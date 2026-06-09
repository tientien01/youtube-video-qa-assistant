from dataclasses import dataclass

from app.schemas.generation import GenerationMetadata
from app.schemas.notes import StudyNotesResponse, StudyNotesSource
from app.services.llm.base import LlmClient
from app.services.llm.generation import generate_optional_llm_result
from app.services.llm.prompt_builder import build_study_notes_prompt
from app.services.learning.generated_output_store import generated_output_store
from app.services.rag.local_store import VideoNotIndexedError, rag_store
from app.services.rag.models import TranscriptChunk


NOTES_OUTPUT_TYPE = "study_notes"
NOTES_MODE = "default"


@dataclass(frozen=True)
class GeneratedNotes:
    text: str
    generation: GenerationMetadata


def generate_study_notes(
    video_id: str,
    llm_client: LlmClient | None = None,
) -> StudyNotesResponse:
    chunks = rag_store.get_video_chunks(video_id)
    if not chunks:
        raise VideoNotIndexedError("Video has not been indexed yet.")

    cached_output = generated_output_store.get_output(
        video_id=video_id,
        output_type=NOTES_OUTPUT_TYPE,
        mode=NOTES_MODE,
    )
    chunk_by_id = {chunk.chunk_id: chunk for chunk in chunks}
    if cached_output is not None:
        return StudyNotesResponse(
            video_id=video_id,
            notes=cached_output.content,
            sources=_sources_from_chunk_ids(cached_output.source_chunk_ids, chunk_by_id),
            cached=True,
            generation=GenerationMetadata(
                generation_mode="cached",
                provider="cache",
                fallback_reason=None,
            ),
        )

    source_chunks = chunks[:10]
    generated_notes = _generate_notes_text(
        chunks=source_chunks,
        llm_client=llm_client,
    )
    generated_output_store.upsert_output(
        video_id=video_id,
        output_type=NOTES_OUTPUT_TYPE,
        mode=NOTES_MODE,
        content=generated_notes.text,
        source_chunk_ids=[chunk.chunk_id for chunk in source_chunks],
    )

    return StudyNotesResponse(
        video_id=video_id,
        notes=generated_notes.text,
        sources=[_chunk_to_source(chunk) for chunk in source_chunks],
        cached=False,
        generation=generated_notes.generation,
    )


def _generate_notes_text(
    *,
    chunks: list[TranscriptChunk],
    llm_client: LlmClient | None,
) -> GeneratedNotes:
    prompt = build_study_notes_prompt(chunks)
    llm_result = generate_optional_llm_result(
        prompt,
        llm_client=llm_client,
        fallback_log_message="LLM study notes generation failed, using fallback notes",
    )
    if llm_result.text is not None:
        return GeneratedNotes(
            text=llm_result.text,
            generation=GenerationMetadata(
                generation_mode="llm",
                provider=llm_result.provider,
                fallback_reason=None,
            ),
        )

    return GeneratedNotes(
        text=_build_fallback_notes(chunks),
        generation=GenerationMetadata(
            generation_mode="fallback",
            provider=llm_result.provider,
            fallback_reason=llm_result.fallback_reason,
        ),
    )


def _build_fallback_notes(chunks: list[TranscriptChunk]) -> str:
    key_points = "\n".join(
        f"{index}. {chunk.text}"
        for index, chunk in enumerate(chunks[:6], start=1)
    )
    review_timestamps = "\n".join(
        f"- {_format_timestamp(chunk.start_seconds)}-{_format_timestamp(chunk.end_seconds)}: {chunk.text}"
        for chunk in chunks[:5]
    )

    return (
        "Mục tiêu bài học:\n"
        "- Nắm các ý chính xuất hiện trong transcript và biết đoạn nào cần xem lại.\n\n"
        "Khái niệm chính:\n"
        f"{key_points}\n\n"
        "Giải thích ngắn:\n"
        "Các ghi chú này được tạo từ những đoạn transcript đầu tiên của video. "
        "Khi bật LLM sau này, phần này có thể được viết lại tự nhiên và có cấu trúc sâu hơn.\n\n"
        "Timestamp nên xem lại:\n"
        f"{review_timestamps}"
    )


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
