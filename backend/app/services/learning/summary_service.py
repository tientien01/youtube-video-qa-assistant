from dataclasses import dataclass

from app.schemas.generation import GenerationMetadata
from app.schemas.summary import SummaryMode, SummaryResponse, SummarySource
from app.services.llm.base import LlmClient
from app.services.llm.generation import generate_optional_llm_result
from app.services.llm.prompt_builder import build_summary_prompt
from app.services.learning.generated_output_store import generated_output_store
from app.services.rag.local_store import VideoNotIndexedError, rag_store
from app.services.rag.models import TranscriptChunk


SUMMARY_OUTPUT_TYPE = "summary"


@dataclass(frozen=True)
class GeneratedSummary:
    text: str
    generation: GenerationMetadata


def generate_video_summary(
    video_id: str,
    mode: SummaryMode = "short",
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
    if cached_output is not None:
        return SummaryResponse(
            video_id=video_id,
            mode=mode,
            summary=cached_output.content,
            sources=_sources_from_chunk_ids(cached_output.source_chunk_ids, chunk_by_id),
            cached=True,
            generation=GenerationMetadata(
                generation_mode="cached",
                provider="cache",
                fallback_reason=None,
            ),
        )

    source_chunks = _select_source_chunks(chunks=chunks, mode=mode)
    generated_summary = _generate_summary_text(
        mode=mode,
        chunks=source_chunks,
        llm_client=llm_client,
    )
    generated_output_store.upsert_output(
        video_id=video_id,
        output_type=SUMMARY_OUTPUT_TYPE,
        mode=mode,
        content=generated_summary.text,
        source_chunk_ids=[chunk.chunk_id for chunk in source_chunks],
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
    llm_client: LlmClient | None,
) -> GeneratedSummary:
    prompt = build_summary_prompt(mode=mode, chunks=chunks)
    llm_result = generate_optional_llm_result(
        prompt,
        llm_client=llm_client,
        fallback_log_message="LLM summary generation failed, using fallback summary",
    )
    if llm_result.text is not None:
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


def _select_source_chunks(chunks: list[TranscriptChunk], mode: SummaryMode) -> list[TranscriptChunk]:
    if mode == "short":
        return chunks[:5]

    if mode == "detailed":
        return chunks[:8]

    return chunks[:12]


def _build_fallback_summary(mode: SummaryMode, chunks: list[TranscriptChunk]) -> str:
    if mode == "timeline":
        lines = [
            f"- {_format_timestamp(chunk.start_seconds)}-{_format_timestamp(chunk.end_seconds)}: {chunk.text}"
            for chunk in chunks
        ]
        return "Tóm tắt theo timeline:\n" + "\n".join(lines)

    if mode == "detailed":
        lines = [
            f"{index}. {chunk.text}"
            for index, chunk in enumerate(chunks, start=1)
        ]
        return "Các ý chính trong video:\n" + "\n".join(lines)

    lines = [
        f"- {chunk.text}"
        for chunk in chunks
    ]
    return "Tóm tắt ngắn:\n" + "\n".join(lines)


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
