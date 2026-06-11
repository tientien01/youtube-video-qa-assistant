from dataclasses import dataclass
from hashlib import sha1

from app.schemas.generation import GenerationMetadata
from app.schemas.notes import StudyNotesMode, StudyNotesResponse, StudyNotesSource
from app.services.llm.base import LlmClient
from app.services.llm.generation import generate_optional_llm_result
from app.services.llm.prompt_builder import build_study_notes_prompt
from app.services.learning.generated_output_store import generated_output_store
from app.services.rag.local_store import VideoNotIndexedError, rag_store
from app.services.rag.models import RetrievedChunk, TranscriptChunk
from app.services.rag.text_processing import tokenize


NOTES_OUTPUT_TYPE = "study_notes"
DEFAULT_NOTES_MODE: StudyNotesMode = "concise"
LONG_VIDEO_CHUNK_THRESHOLD = 18


@dataclass(frozen=True)
class GeneratedNotes:
    text: str
    generation: GenerationMetadata


def generate_study_notes(
    video_id: str,
    mode: StudyNotesMode = DEFAULT_NOTES_MODE,
    learning_goal: str | None = None,
    force: bool = False,
    llm_client: LlmClient | None = None,
) -> StudyNotesResponse:
    chunks = rag_store.get_video_chunks(video_id)
    if not chunks:
        raise VideoNotIndexedError("Video has not been indexed yet.")

    normalized_goal = _normalize_goal(learning_goal)
    cache_mode = _build_cache_mode(mode=mode, learning_goal=normalized_goal)
    cached_output = generated_output_store.get_output(
        video_id=video_id,
        output_type=NOTES_OUTPUT_TYPE,
        mode=cache_mode,
    )
    chunk_by_id = {chunk.chunk_id: chunk for chunk in chunks}
    if cached_output is not None and not force and _is_usable_notes(cached_output.content):
        return StudyNotesResponse(
            video_id=video_id,
            mode=mode,
            learning_goal=normalized_goal,
            notes=cached_output.content,
            sources=_sources_from_chunk_ids(cached_output.source_chunk_ids, chunk_by_id),
            cached=True,
            generation=GenerationMetadata(
                generation_mode="cached",
                provider=cached_output.provider,
                fallback_reason=_cached_generation_note(cached_output.generation_mode, cached_output.fallback_reason),
            ),
        )

    source_chunks = _select_source_chunks(
        video_id=video_id,
        chunks=chunks,
        mode=mode,
        learning_goal=normalized_goal,
    )
    generated_notes = _generate_notes_text(
        mode=mode,
        learning_goal=normalized_goal,
        chunks=source_chunks,
        llm_client=llm_client,
    )
    generated_output_store.upsert_output(
        video_id=video_id,
        output_type=NOTES_OUTPUT_TYPE,
        mode=cache_mode,
        content=generated_notes.text,
        source_chunk_ids=[chunk.chunk_id for chunk in source_chunks],
        generation_mode=generated_notes.generation.generation_mode,
        provider=generated_notes.generation.provider,
        fallback_reason=generated_notes.generation.fallback_reason,
    )

    return StudyNotesResponse(
        video_id=video_id,
        mode=mode,
        learning_goal=normalized_goal,
        notes=generated_notes.text,
        sources=[_chunk_to_source(chunk) for chunk in source_chunks],
        cached=False,
        generation=generated_notes.generation,
    )


def _generate_notes_text(
    *,
    mode: StudyNotesMode,
    learning_goal: str | None,
    chunks: list[TranscriptChunk],
    llm_client: LlmClient | None,
) -> GeneratedNotes:
    prompt = build_study_notes_prompt(chunks, mode=mode, learning_goal=learning_goal)
    llm_result = generate_optional_llm_result(
        prompt,
        llm_client=llm_client,
        fallback_log_message="LLM study notes generation failed, using fallback notes",
    )
    if llm_result.text is not None:
        if llm_result.provider != "injected" and not _is_usable_notes(llm_result.text):
            fallback_reason = "LLM study notes were incomplete or missing required sections."
            return GeneratedNotes(
                text=_build_fallback_notes(chunks, mode=mode, learning_goal=learning_goal),
                generation=GenerationMetadata(
                    generation_mode="fallback",
                    provider=llm_result.provider,
                    fallback_reason=fallback_reason,
                ),
            )

        return GeneratedNotes(
            text=llm_result.text,
            generation=GenerationMetadata(
                generation_mode="llm",
                provider=llm_result.provider,
                fallback_reason=None,
            ),
        )

    return GeneratedNotes(
        text=_build_fallback_notes(chunks, mode=mode, learning_goal=learning_goal),
        generation=GenerationMetadata(
            generation_mode="fallback",
            provider=llm_result.provider,
            fallback_reason=llm_result.fallback_reason,
        ),
    )


def _select_source_chunks(
    *,
    video_id: str,
    chunks: list[TranscriptChunk],
    mode: StudyNotesMode,
    learning_goal: str | None,
) -> list[TranscriptChunk]:
    target_count = 14 if mode in {"detailed", "timeline", "exam_review"} else 10
    timeline_chunks = _select_timeline_chunks(chunks, max_count=target_count)
    semantic_chunks = _select_semantic_chunks(
        video_id=video_id,
        mode=mode,
        learning_goal=learning_goal,
        max_count=6,
    )
    selected_chunks = _dedupe_chunks([*timeline_chunks, *semantic_chunks])
    selected_chunks.sort(key=lambda chunk: (chunk.start_seconds, chunk.chunk_id))
    return selected_chunks[: target_count + 4]


def _select_timeline_chunks(chunks: list[TranscriptChunk], max_count: int) -> list[TranscriptChunk]:
    if len(chunks) <= max_count:
        return chunks

    if len(chunks) >= LONG_VIDEO_CHUNK_THRESHOLD:
        return _select_section_representatives(chunks, max_count=max_count)

    step = (len(chunks) - 1) / max(max_count - 1, 1)
    indexes = sorted({round(index * step) for index in range(max_count)})
    return [chunks[index] for index in indexes]


def _select_section_representatives(chunks: list[TranscriptChunk], max_count: int) -> list[TranscriptChunk]:
    section_count = min(6, max(3, max_count // 2))
    selected_indexes: set[int] = set()
    for section_index in range(section_count):
        start = round(section_index * len(chunks) / section_count)
        end = round((section_index + 1) * len(chunks) / section_count)
        section_indexes = list(range(start, min(end, len(chunks))))
        if not section_indexes:
            continue

        selected_indexes.add(section_indexes[0])
        selected_indexes.add(section_indexes[len(section_indexes) // 2])

    return [chunks[index] for index in sorted(selected_indexes)[:max_count]]


def _select_semantic_chunks(
    *,
    video_id: str,
    mode: StudyNotesMode,
    learning_goal: str | None,
    max_count: int,
) -> list[TranscriptChunk]:
    queries = _semantic_queries(mode=mode, learning_goal=learning_goal)
    candidates: list[RetrievedChunk] = []
    for query in queries:
        try:
            from app.services.rag.retrieval_service import retrieve_chunks

            candidates.extend(
                retrieve_chunks(
                    video_id=video_id,
                    question=query,
                    mode="hybrid",
                    top_k=3,
                )
            )
        except (ValueError, VideoNotIndexedError, RuntimeError):
            continue

    candidates.sort(key=lambda item: item.score, reverse=True)
    return _dedupe_chunks([candidate.chunk for candidate in candidates])[:max_count]


def _semantic_queries(*, mode: StudyNotesMode, learning_goal: str | None) -> list[str]:
    queries = [
        "main concepts important definitions key takeaways",
        "examples details timestamps review",
    ]
    if mode == "exam_review":
        queries.append("exam review important questions definitions")
    elif mode == "beginner":
        queries.append("simple explanation basic concepts")
    elif mode == "timeline":
        queries.append("timeline sequence steps process")
    elif mode == "detailed":
        queries.append("detailed explanation important details")

    if learning_goal:
        queries.append(learning_goal)

    return queries


def _dedupe_chunks(chunks: list[TranscriptChunk]) -> list[TranscriptChunk]:
    unique_chunks: dict[str, TranscriptChunk] = {}
    for chunk in chunks:
        unique_chunks.setdefault(chunk.chunk_id, chunk)

    return list(unique_chunks.values())


def _build_fallback_notes(
    chunks: list[TranscriptChunk],
    *,
    mode: StudyNotesMode,
    learning_goal: str | None,
) -> str:
    key_points = "\n".join(
        f"- {_shorten_text(chunk.text, 180)}"
        for chunk in _rank_chunks_by_terms(chunks, _mode_terms(mode, learning_goal))[:6]
    )
    review_timestamps = "\n".join(
        f"- {_format_timestamp(chunk.start_seconds)}-{_format_timestamp(chunk.end_seconds)}: {_shorten_text(chunk.text, 140)}"
        for chunk in chunks[:5]
    )
    sections = _format_section_notes(chunks) if len(chunks) >= 12 else ""
    goal_line = f"- Mục tiêu riêng: {learning_goal}\n" if learning_goal else ""

    return (
        "Mục tiêu bài học:\n"
        "- Nắm các ý chính xuất hiện trong transcript và biết đoạn nào cần xem lại.\n\n"
        f"{goal_line}"
        "Khái niệm chính:\n"
        f"{key_points}\n\n"
        "Giải thích ngắn:\n"
        "Các ghi chú này được tạo từ các đoạn transcript đại diện của video. "
        "Khi LLM không khả dụng, hệ thống chọn các đoạn đại diện theo timeline và keyword để giữ notes có thể dùng được.\n\n"
        f"{sections}"
        "Timestamp nên xem lại:\n"
        f"{review_timestamps}"
    )


def _is_usable_notes(text: str) -> bool:
    stripped_text = text.strip()
    if len(stripped_text.split()) < 45:
        return False

    required_sections = [
        "Mục tiêu bài học",
        "Khái niệm chính",
        "Giải thích",
        "Timestamp nên xem lại",
    ]
    if not all(section in stripped_text for section in required_sections):
        return False

    last_line = next(
        (line.strip() for line in reversed(stripped_text.splitlines()) if line.strip()),
        "",
    )
    return bool(last_line) and last_line[-1] in {".", "!", "?", ")", "]"}


def _rank_chunks_by_terms(chunks: list[TranscriptChunk], query_terms: set[str]) -> list[TranscriptChunk]:
    if not query_terms:
        return chunks

    return sorted(
        chunks,
        key=lambda chunk: len(query_terms & set(tokenize(chunk.text))),
        reverse=True,
    )


def _mode_terms(mode: StudyNotesMode, learning_goal: str | None) -> set[str]:
    text = {
        "concise": "main concepts key ideas",
        "detailed": "details explanation examples",
        "timeline": "timeline process steps",
        "exam_review": "definition exam review important question",
        "beginner": "basic simple concept explanation",
    }[mode]
    if learning_goal:
        text = f"{text} {learning_goal}"

    return set(tokenize(text))


def _format_section_notes(chunks: list[TranscriptChunk]) -> str:
    sections = []
    for index, chunk in enumerate(chunks[:6], start=1):
        sections.append(
            f"- Phần {index} ({_format_timestamp(chunk.start_seconds)}-{_format_timestamp(chunk.end_seconds)}): "
            f"{_shorten_text(chunk.text, 150)}"
        )

    return "Ghi chú theo phần:\n" + "\n".join(sections) + "\n\n"


def _build_cache_mode(*, mode: StudyNotesMode, learning_goal: str | None) -> str:
    if not learning_goal:
        return mode

    digest = sha1(learning_goal.encode("utf-8")).hexdigest()[:10]
    return f"{mode}:goal:{digest}"


def _normalize_goal(learning_goal: str | None) -> str | None:
    if learning_goal is None:
        return None

    normalized_goal = " ".join(learning_goal.split())
    return normalized_goal[:240] or None


def _cached_generation_note(generation_mode: str, fallback_reason: str | None) -> str:
    if fallback_reason:
        return f"Cached output originally used {generation_mode}. {fallback_reason}"

    return f"Cached output originally used {generation_mode}."


def _shorten_text(text: str, max_length: int) -> str:
    normalized_text = " ".join(text.split())
    if len(normalized_text) <= max_length:
        return normalized_text

    return f"{normalized_text[: max_length - 3].rstrip()}..."


def _sources_from_chunk_ids(
    chunk_ids: list[str],
    chunk_by_id: dict[str, TranscriptChunk],
) -> list[StudyNotesSource]:
    return [
        _chunk_to_source(chunk_by_id[chunk_id])
        for chunk_id in chunk_ids
        if chunk_id in chunk_by_id
    ]


def _chunk_to_source(chunk: TranscriptChunk) -> StudyNotesSource:
    return StudyNotesSource(
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
