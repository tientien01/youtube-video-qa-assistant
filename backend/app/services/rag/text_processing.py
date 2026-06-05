import re
from dataclasses import dataclass

from app.schemas.transcript import TranscriptSegment
from app.services.rag.models import TranscriptChunk


WHITESPACE_PATTERN = re.compile(r"\s+")
TOKEN_PATTERN = re.compile(r"[^\W_]+", re.UNICODE)


@dataclass(frozen=True)
class _ChunkPart:
    text: str
    start_seconds: float
    end_seconds: float
    word_count: int


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
    current_parts: list[_ChunkPart] = []
    current_word_count = 0

    for segment in segments:
        cleaned_text = clean_text(segment.text)
        if not cleaned_text:
            continue

        word_count = len(tokenize(cleaned_text))
        if word_count == 0:
            continue

        current_parts.append(
            _ChunkPart(
                text=cleaned_text,
                start_seconds=segment.start_seconds,
                end_seconds=segment.end_seconds,
                word_count=word_count,
            )
        )
        current_word_count += word_count

        if current_word_count >= target_words:
            _append_chunk(chunks, video_id, current_parts)
            current_parts, current_word_count = _build_overlap(
                current_parts,
                overlap_words,
            )

    if current_parts:
        _append_chunk(chunks, video_id, current_parts)

    return chunks


def _append_chunk(
    chunks: list[TranscriptChunk],
    video_id: str,
    parts: list[_ChunkPart],
) -> None:
    text = clean_text(" ".join(part.text for part in parts))
    if not text:
        return

    chunks.append(
        TranscriptChunk(
            chunk_id=f"{video_id}-{len(chunks) + 1:04d}",
            video_id=video_id,
            text=text,
            start_seconds=parts[0].start_seconds,
            end_seconds=parts[-1].end_seconds,
        )
    )


def _build_overlap(
    parts: list[_ChunkPart],
    overlap_words: int,
) -> tuple[list[_ChunkPart], int]:
    if overlap_words == 0:
        return [], 0

    overlap_parts: list[_ChunkPart] = []
    remaining_words = overlap_words
    for part in reversed(parts):
        if part.word_count <= remaining_words:
            overlap_parts.append(part)
            remaining_words -= part.word_count
            if remaining_words <= 0:
                break
        else:
            tokens = tokenize(part.text)
            selected_tokens = tokens[-remaining_words:]
            overlap_parts.append(
                _ChunkPart(
                    text=" ".join(selected_tokens),
                    start_seconds=part.start_seconds,
                    end_seconds=part.end_seconds,
                    word_count=len(selected_tokens),
                )
            )
            break

    overlap_parts.reverse()
    return overlap_parts, sum(part.word_count for part in overlap_parts)
