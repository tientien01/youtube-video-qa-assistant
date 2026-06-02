import re

from app.schemas.transcript import TranscriptSegment
from app.services.rag.models import TranscriptChunk


WHITESPACE_PATTERN = re.compile(r"\s+")
TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_]+", re.UNICODE)


def clean_text(text: str) -> str:
    return WHITESPACE_PATTERN.sub(" ", text).strip()


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text)]


def chunk_transcript(
    video_id: str,
    segments: list[TranscriptSegment],
    target_words: int = 140,
    overlap_words: int = 30,
) -> list[TranscriptChunk]:
    if target_words <= 0:
        raise ValueError("target_words must be greater than zero.")
    if overlap_words < 0:
        raise ValueError("overlap_words cannot be negative.")
    if overlap_words >= target_words:
        raise ValueError("overlap_words must be smaller than target_words.")

    chunks: list[TranscriptChunk] = []
    current_parts: list[str] = []
    current_word_count = 0
    current_start: float | None = None
    current_end: float | None = None

    for segment in segments:
        cleaned_text = clean_text(segment.text)
        if not cleaned_text:
            continue

        if current_start is None:
            current_start = segment.start_seconds

        current_parts.append(cleaned_text)
        current_word_count += len(tokenize(cleaned_text))
        current_end = segment.end_seconds

        if current_word_count >= target_words:
            _append_chunk(chunks, video_id, current_parts, current_start, current_end)
            current_parts, current_word_count, current_start = _build_overlap(
                current_parts,
                current_end,
                overlap_words,
            )

    if current_parts and current_start is not None and current_end is not None:
        _append_chunk(chunks, video_id, current_parts, current_start, current_end)

    return chunks


def _append_chunk(
    chunks: list[TranscriptChunk],
    video_id: str,
    parts: list[str],
    start_seconds: float,
    end_seconds: float,
) -> None:
    text = clean_text(" ".join(parts))
    if not text:
        return

    chunks.append(
        TranscriptChunk(
            chunk_id=f"{video_id}-{len(chunks) + 1:04d}",
            video_id=video_id,
            text=text,
            start_seconds=start_seconds,
            end_seconds=end_seconds,
        )
    )


def _build_overlap(
    parts: list[str],
    fallback_start: float,
    overlap_words: int,
) -> tuple[list[str], int, float]:
    if overlap_words == 0:
        return [], 0, fallback_start

    overlap_tokens: list[str] = []
    for part in reversed(parts):
        part_tokens = tokenize(part)
        overlap_tokens = part_tokens + overlap_tokens
        if len(overlap_tokens) >= overlap_words:
            break

    selected_tokens = overlap_tokens[-overlap_words:]
    overlap_text = " ".join(selected_tokens)
    if not overlap_text:
        return [], 0, fallback_start

    return [overlap_text], len(selected_tokens), fallback_start
