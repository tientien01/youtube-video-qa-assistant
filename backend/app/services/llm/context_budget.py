from dataclasses import replace

from app.services.rag.models import RetrievedChunk, TranscriptChunk


LONG_VIDEO_SECONDS = 20 * 60
DEFAULT_DIRECT_CONTEXT_CHARS = 9000
COMPACT_DIRECT_CONTEXT_CHARS = 5500


def should_use_sectioned_generation(chunks: list[TranscriptChunk]) -> bool:
    if not chunks:
        return False

    duration_seconds = max(chunk.end_seconds for chunk in chunks) - min(
        chunk.start_seconds for chunk in chunks
    )
    return duration_seconds >= LONG_VIDEO_SECONDS or total_text_chars(chunks) > DEFAULT_DIRECT_CONTEXT_CHARS


def compact_transcript_chunks(
    chunks: list[TranscriptChunk],
    *,
    max_total_chars: int = DEFAULT_DIRECT_CONTEXT_CHARS,
    max_chunk_chars: int = 900,
) -> list[TranscriptChunk]:
    compacted: list[TranscriptChunk] = []
    remaining_chars = max_total_chars
    for chunk in chunks:
        if remaining_chars <= 0:
            break

        text = _shorten_text(chunk.text, min(max_chunk_chars, remaining_chars))
        compacted.append(replace(chunk, text=text))
        remaining_chars -= len(text)

    return compacted


def compact_retrieved_chunks(
    retrieved_chunks: list[RetrievedChunk],
    *,
    max_total_chars: int = DEFAULT_DIRECT_CONTEXT_CHARS,
    max_chunk_chars: int = 900,
) -> list[RetrievedChunk]:
    compacted_chunks = compact_transcript_chunks(
        [item.chunk for item in retrieved_chunks],
        max_total_chars=max_total_chars,
        max_chunk_chars=max_chunk_chars,
    )
    compacted_by_id = {chunk.chunk_id: chunk for chunk in compacted_chunks}
    return [
        replace(item, chunk=compacted_by_id[item.chunk.chunk_id])
        for item in retrieved_chunks
        if item.chunk.chunk_id in compacted_by_id
    ]


def split_chunks_into_sections(
    chunks: list[TranscriptChunk],
    *,
    target_section_seconds: int = 5 * 60,
    max_sections: int = 10,
) -> list[list[TranscriptChunk]]:
    if not chunks:
        return []

    sections: list[list[TranscriptChunk]] = []
    current_section: list[TranscriptChunk] = []
    section_start = chunks[0].start_seconds
    for chunk in chunks:
        section_duration = chunk.end_seconds - section_start
        if current_section and section_duration >= target_section_seconds:
            sections.append(current_section)
            current_section = []
            section_start = chunk.start_seconds

        current_section.append(chunk)

    if current_section:
        sections.append(current_section)

    if len(sections) <= max_sections:
        return sections

    return _merge_sections(sections, max_sections=max_sections)


def total_text_chars(chunks: list[TranscriptChunk]) -> int:
    return sum(len(chunk.text) for chunk in chunks)


def is_token_limit_failure(reason: str | None) -> bool:
    return bool(reason and "token limit" in reason.lower())


def _merge_sections(
    sections: list[list[TranscriptChunk]],
    *,
    max_sections: int,
) -> list[list[TranscriptChunk]]:
    merged_sections: list[list[TranscriptChunk]] = []
    step = len(sections) / max_sections
    for index in range(max_sections):
        start = round(index * step)
        end = round((index + 1) * step)
        merged: list[TranscriptChunk] = []
        for section in sections[start:end]:
            merged.extend(section)
        if merged:
            merged_sections.append(merged)

    return merged_sections


def _shorten_text(text: str, max_length: int) -> str:
    normalized_text = " ".join(text.split())
    if len(normalized_text) <= max_length:
        return normalized_text

    if max_length <= 3:
        return normalized_text[:max_length]

    return f"{normalized_text[: max_length - 3].rstrip()}..."
