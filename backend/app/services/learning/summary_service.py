from dataclasses import dataclass
from datetime import UTC, datetime

from app.schemas.generation import GenerationMetadata
from app.schemas.summary import SummaryMode, SummaryResponse, SummarySource
from app.services.llm.base import LlmClient
from app.services.llm.context_budget import (
    COMPACT_DIRECT_CONTEXT_CHARS,
    compact_transcript_chunks,
    is_token_limit_failure,
    should_use_sectioned_generation,
    split_chunks_into_sections,
)
from app.services.llm.generation import generate_optional_llm_result
from app.services.llm.prompt_builder import (
    build_summary_merge_prompt,
    build_summary_prompt,
    build_summary_section_prompt,
)
from app.services.learning.generated_output_store import GeneratedOutput, generated_output_store
from app.services.rag.local_store import VideoNotIndexedError, rag_store
from app.services.rag.models import RetrievedChunk, TranscriptChunk


SUMMARY_OUTPUT_TYPE = "summary"
SUMMARY_SECTION_OUTPUT_TYPE = "summary_section"


@dataclass(frozen=True)
class GeneratedSummary:
    text: str
    generation: GenerationMetadata


def generate_video_summary(
    video_id: str,
    mode: SummaryMode = "short",
    force: bool = False,
    llm_client: LlmClient | None = None,
) -> SummaryResponse:
    chunks = rag_store.get_video_chunks(video_id)
    if not chunks:
        raise VideoNotIndexedError("Video has not been indexed yet.")

    cached_output = generated_output_store.get_output(
        video_id=video_id,
        output_type=SUMMARY_OUTPUT_TYPE,
        mode=mode,
    )
    chunk_by_id = {chunk.chunk_id: chunk for chunk in chunks}
    if cached_output is not None and not force and not _looks_incomplete(cached_output.content):
        return SummaryResponse(
            video_id=video_id,
            mode=mode,
            summary=cached_output.content,
            sources=_sources_from_chunk_ids(cached_output.source_chunk_ids, chunk_by_id),
            cached=True,
            generation=GenerationMetadata(
                generation_mode="cached",
                provider=cached_output.provider,
                fallback_reason=_cached_generation_note(cached_output.generation_mode, cached_output.fallback_reason),
            ),
        )

    source_chunks = _select_source_chunks(video_id=video_id, chunks=chunks, mode=mode)
    generated_summary = _generate_summary_text(
        mode=mode,
        chunks=source_chunks,
        all_chunks=chunks,
        video_id=video_id,
        force=force,
        llm_client=llm_client,
    )
    generated_output_store.upsert_output(
        video_id=video_id,
        output_type=SUMMARY_OUTPUT_TYPE,
        mode=mode,
        content=generated_summary.text,
        source_chunk_ids=[chunk.chunk_id for chunk in source_chunks],
        generation_mode=generated_summary.generation.generation_mode,
        provider=generated_summary.generation.provider,
        fallback_reason=generated_summary.generation.fallback_reason,
    )

    return SummaryResponse(
        video_id=video_id,
        mode=mode,
        summary=generated_summary.text,
        sources=[_chunk_to_source(chunk) for chunk in source_chunks],
        cached=False,
        generation=generated_summary.generation,
    )


def _generate_summary_text(
    *,
    mode: SummaryMode,
    chunks: list[TranscriptChunk],
    all_chunks: list[TranscriptChunk],
    video_id: str,
    force: bool,
    llm_client: LlmClient | None,
) -> GeneratedSummary:
    if mode in {"detailed", "timeline"} and should_use_sectioned_generation(all_chunks):
        sectioned_summary = _generate_sectioned_summary(
            video_id=video_id,
            mode=mode,
            chunks=all_chunks,
            fallback_chunks=chunks,
            force=force,
            llm_client=llm_client,
        )
        if sectioned_summary.generation.generation_mode == "llm":
            return sectioned_summary

    compacted_chunks = compact_transcript_chunks(chunks)
    prompt = build_summary_prompt(mode=mode, chunks=compacted_chunks)
    llm_result = generate_optional_llm_result(
        prompt,
        llm_client=llm_client,
        fallback_log_message="LLM summary generation failed, using fallback summary",
    )
    if llm_result.text is None and is_token_limit_failure(llm_result.fallback_reason):
        compacted_chunks = compact_transcript_chunks(
            chunks,
            max_total_chars=COMPACT_DIRECT_CONTEXT_CHARS,
            max_chunk_chars=450,
        )
        retry_prompt = build_summary_prompt(mode=mode, chunks=compacted_chunks)
        llm_result = generate_optional_llm_result(
            retry_prompt,
            llm_client=llm_client,
            fallback_log_message="LLM summary retry failed, using fallback summary",
        )

    if llm_result.text is not None:
        if llm_result.provider != "injected" and not _is_usable_llm_summary(mode, llm_result.text):
            fallback_reason = "LLM summary was too short or looked incomplete."
            return GeneratedSummary(
                text=_build_fallback_summary(mode=mode, chunks=chunks),
                generation=GenerationMetadata(
                    generation_mode="fallback",
                    provider=llm_result.provider,
                    fallback_reason=fallback_reason,
                ),
            )

        return GeneratedSummary(
            text=llm_result.text,
            generation=GenerationMetadata(
                generation_mode="llm",
                provider=llm_result.provider,
                fallback_reason=None,
            ),
        )

    return GeneratedSummary(
        text=_build_fallback_summary(mode=mode, chunks=chunks),
        generation=GenerationMetadata(
            generation_mode="fallback",
            provider=llm_result.provider,
            fallback_reason=llm_result.fallback_reason,
        ),
    )


def _generate_sectioned_summary(
    *,
    video_id: str,
    mode: SummaryMode,
    chunks: list[TranscriptChunk],
    fallback_chunks: list[TranscriptChunk],
    force: bool,
    llm_client: LlmClient | None,
) -> GeneratedSummary:
    sections = split_chunks_into_sections(chunks, target_section_seconds=5 * 60, max_sections=8)
    if len(sections) <= 1:
        return GeneratedSummary(
            text=_build_fallback_summary(mode=mode, chunks=fallback_chunks),
            generation=GenerationMetadata(
                generation_mode="fallback",
                provider="fallback",
                fallback_reason="Video was not split into multiple sections.",
            ),
        )

    section_summaries: list[str] = []
    pending_section_outputs: list[GeneratedOutput] = []
    provider = "fallback"
    fallback_reasons: list[str] = []
    for index, section_chunks in enumerate(sections, start=1):
        cache_mode = _section_cache_mode(mode=mode, section_index=index, section_chunks=section_chunks)
        cached_section = generated_output_store.get_output(
            video_id=video_id,
            output_type=SUMMARY_SECTION_OUTPUT_TYPE,
            mode=cache_mode,
        )
        if cached_section is not None and not force and not _looks_incomplete(cached_section.content):
            section_summaries.append(cached_section.content)
            provider = cached_section.provider
            continue

        compacted_section = compact_transcript_chunks(
            section_chunks,
            max_total_chars=4500,
            max_chunk_chars=700,
        )
        section_prompt = build_summary_section_prompt(
            mode=mode,
            chunks=compacted_section,
            section_index=index,
            section_count=len(sections),
        )
        section_result = generate_optional_llm_result(
            section_prompt,
            llm_client=llm_client,
            fallback_log_message="LLM summary section generation failed, using section fallback",
        )
        if section_result.text is None and is_token_limit_failure(section_result.fallback_reason):
            compacted_section = compact_transcript_chunks(
                section_chunks,
                max_total_chars=2600,
                max_chunk_chars=350,
            )
            section_result = generate_optional_llm_result(
                build_summary_section_prompt(
                    mode=mode,
                    chunks=compacted_section,
                    section_index=index,
                    section_count=len(sections),
                ),
                llm_client=llm_client,
                fallback_log_message="LLM summary section retry failed, using section fallback",
            )

        if section_result.text is None:
            section_text = _build_fallback_summary(mode=mode, chunks=section_chunks[:3])
            fallback_reasons.append(section_result.fallback_reason or f"Section {index} used fallback.")
        else:
            section_text = section_result.text
            provider = section_result.provider

        section_summaries.append(section_text)
        pending_section_outputs.append(
            _pending_generated_output(
                video_id=video_id,
                output_type=SUMMARY_SECTION_OUTPUT_TYPE,
                mode=cache_mode,
                content=section_text,
                source_chunk_ids=[chunk.chunk_id for chunk in section_chunks[:6]],
                generation_mode="llm" if section_result.text is not None else "fallback",
                provider=section_result.provider,
                fallback_reason=section_result.fallback_reason,
            )
        )

    generated_output_store.upsert_outputs(pending_section_outputs)

    merge_result = generate_optional_llm_result(
        build_summary_merge_prompt(mode=mode, section_summaries=section_summaries),
        llm_client=llm_client,
        fallback_log_message="LLM summary merge failed, using section summaries",
    )
    if merge_result.text is None and is_token_limit_failure(merge_result.fallback_reason):
        compacted_summaries = [_shorten_text(summary, 650) for summary in section_summaries]
        merge_result = generate_optional_llm_result(
            build_summary_merge_prompt(mode=mode, section_summaries=compacted_summaries),
            llm_client=llm_client,
            fallback_log_message="LLM summary merge retry failed, using section summaries",
        )

    if merge_result.text is not None and _is_usable_llm_summary(mode, merge_result.text):
        fallback_reason = "; ".join(reason for reason in fallback_reasons if reason) or None
        return GeneratedSummary(
            text=merge_result.text,
            generation=GenerationMetadata(
                generation_mode="llm",
                provider=merge_result.provider or provider,
                fallback_reason=fallback_reason,
            ),
        )

    fallback_reason = merge_result.fallback_reason or "LLM section merge was incomplete."
    return GeneratedSummary(
        text=_merge_section_fallback(mode=mode, section_summaries=section_summaries),
        generation=GenerationMetadata(
            generation_mode="fallback",
            provider=merge_result.provider,
            fallback_reason=fallback_reason,
        ),
    )


def _section_cache_mode(
    *,
    mode: SummaryMode,
    section_index: int,
    section_chunks: list[TranscriptChunk],
) -> str:
    first_chunk = section_chunks[0]
    last_chunk = section_chunks[-1]
    return (
        f"{mode}:section:{section_index}:"
        f"{int(first_chunk.start_seconds)}-{int(last_chunk.end_seconds)}:"
        f"{first_chunk.chunk_id}-{last_chunk.chunk_id}"
    )


def _pending_generated_output(
    *,
    video_id: str,
    output_type: str,
    mode: str,
    content: str,
    source_chunk_ids: list[str],
    generation_mode: str,
    provider: str,
    fallback_reason: str | None,
) -> GeneratedOutput:
    now = datetime.now(UTC).isoformat()
    return GeneratedOutput(
        video_id=video_id,
        output_type=output_type,
        mode=mode,
        content=content,
        source_chunk_ids=source_chunk_ids,
        created_at=now,
        updated_at=now,
        generation_mode=generation_mode,
        provider=provider,
        fallback_reason=fallback_reason,
    )


def _merge_section_fallback(*, mode: SummaryMode, section_summaries: list[str]) -> str:
    if mode == "timeline":
        heading = "Tom tat theo timeline:"
    elif mode == "detailed":
        heading = "Tom tat theo phan:"
    else:
        heading = "Tom tat ngan:"

    lines = [
        f"- Phan {index}: {_shorten_text(summary, 350)}"
        for index, summary in enumerate(section_summaries, start=1)
    ]
    return heading + "\n" + "\n".join(lines)


def _is_usable_llm_summary(mode: SummaryMode, text: str) -> bool:
    stripped_text = text.strip()
    if len(stripped_text.split()) < 35:
        return False

    if _looks_incomplete(stripped_text):
        return False

    if mode == "short":
        bullet_count = sum(
            1
            for line in stripped_text.splitlines()
            if line.lstrip().startswith(("-", "*"))
        )
        return bullet_count >= 3

    return True


def _looks_incomplete(text: str) -> bool:
    last_line = next(
        (line.strip() for line in reversed(text.splitlines()) if line.strip()),
        "",
    )
    if not last_line:
        return True

    return last_line[-1] not in {".", "!", "?", ")", "]"}


def _cached_generation_note(generation_mode: str, fallback_reason: str | None) -> str:
    if fallback_reason:
        return f"Cached output originally used {generation_mode}. {fallback_reason}"

    return f"Cached output originally used {generation_mode}."


def _select_source_chunks(
    *,
    video_id: str,
    chunks: list[TranscriptChunk],
    mode: SummaryMode,
) -> list[TranscriptChunk]:
    target_count = {
        "short": 8,
        "detailed": 14,
        "timeline": 16,
    }[mode]
    timeline_chunks = _select_timeline_chunks(chunks, max_count=target_count)
    semantic_chunks = _select_semantic_chunks(video_id=video_id, mode=mode, max_count=6)
    selected_chunks = _dedupe_chunks([*timeline_chunks, *semantic_chunks])
    selected_chunks.sort(key=lambda chunk: (chunk.start_seconds, chunk.chunk_id))
    return selected_chunks[: target_count + 4]


def _select_timeline_chunks(chunks: list[TranscriptChunk], max_count: int) -> list[TranscriptChunk]:
    if len(chunks) <= max_count:
        return chunks

    step = (len(chunks) - 1) / max(max_count - 1, 1)
    indexes = sorted({round(index * step) for index in range(max_count)})
    return [chunks[index] for index in indexes]


def _select_semantic_chunks(*, video_id: str, mode: SummaryMode, max_count: int) -> list[TranscriptChunk]:
    queries = {
        "short": ["main ideas key takeaway conclusion"],
        "detailed": ["main concepts important details examples explanation"],
        "timeline": ["sequence process steps timeline important transition"],
    }[mode]
    candidates: list[RetrievedChunk] = []
    for query in queries:
        try:
            from app.services.rag.retrieval_service import retrieve_chunks

            candidates.extend(
                retrieve_chunks(
                    video_id=video_id,
                    question=query,
                    mode="hybrid",
                    top_k=4,
                )
            )
        except (ValueError, VideoNotIndexedError, RuntimeError):
            continue

    candidates.sort(key=lambda item: item.score, reverse=True)
    return _dedupe_chunks([candidate.chunk for candidate in candidates])[:max_count]


def _dedupe_chunks(chunks: list[TranscriptChunk]) -> list[TranscriptChunk]:
    unique_chunks: dict[str, TranscriptChunk] = {}
    for chunk in chunks:
        unique_chunks.setdefault(chunk.chunk_id, chunk)

    return list(unique_chunks.values())


def _build_fallback_summary(mode: SummaryMode, chunks: list[TranscriptChunk]) -> str:
    if mode == "timeline":
        lines = [
            f"- {_format_timestamp(chunk.start_seconds)}-{_format_timestamp(chunk.end_seconds)}: {_shorten_text(chunk.text, 160)}"
            for chunk in chunks
        ]
        return "Tóm tắt theo timeline:\n" + "\n".join(lines)

    if mode == "detailed":
        if len(chunks) >= 12:
            return "Tóm tắt theo phần:\n" + "\n".join(
                f"- Phần {index} [{_format_timestamp(chunk.start_seconds)}]: {_shorten_text(chunk.text, 170)}"
                for index, chunk in enumerate(chunks[:10], start=1)
            )

        lines = [
            f"{index}. {_shorten_text(chunk.text, 180)}"
            for index, chunk in enumerate(chunks, start=1)
        ]
        return "Các ý chính trong video:\n" + "\n".join(lines)

    lines = [
        f"- [{_format_timestamp(chunk.start_seconds)}] {_shorten_text(chunk.text, 150)}"
        for chunk in chunks[:7]
    ]
    return "Tóm tắt ngắn:\n" + "\n".join(lines)


def _shorten_text(text: str, max_length: int) -> str:
    normalized_text = " ".join(text.split())
    if len(normalized_text) <= max_length:
        return normalized_text

    return f"{normalized_text[: max_length - 3].rstrip()}..."


def _sources_from_chunk_ids(
    chunk_ids: list[str],
    chunk_by_id: dict[str, TranscriptChunk],
) -> list[SummarySource]:
    return [
        _chunk_to_source(chunk_by_id[chunk_id])
        for chunk_id in chunk_ids
        if chunk_id in chunk_by_id
    ]


def _chunk_to_source(chunk: TranscriptChunk) -> SummarySource:
    return SummarySource(
        chunk_id=chunk.chunk_id,
        text=chunk.text,
        start_seconds=chunk.start_seconds,
        end_seconds=chunk.end_seconds,
    )


def _format_timestamp(seconds: float) -> str:
    total_seconds = max(int(seconds), 0)
    minutes = total_seconds // 60
    remaining_seconds = total_seconds % 60
    return f"{minutes:02d}:{remaining_seconds:02d}"
