import pytest

from app.domain.entities import Chunk, ChunkType, TranscriptSegment, Video


def test_video_rejects_negative_duration() -> None:
    with pytest.raises(ValueError, match="duration_ms"):
        Video(
            youtube_video_id="dQw4w9WgXcQ",
            canonical_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            title="Example",
            duration_ms=-1,
        )


def test_transcript_segment_rejects_invalid_timestamp_range() -> None:
    with pytest.raises(ValueError, match="timestamps"):
        TranscriptSegment(
            transcript_id="transcript-id",
            sequence_number=0,
            original_text="Example",
            normalized_text="Example",
            start_ms=1000,
            end_ms=1000,
        )


def test_chunk_rejects_empty_text() -> None:
    with pytest.raises(ValueError, match="text"):
        Chunk(
            video_id="video-id",
            transcript_id="transcript-id",
            index_version_id="index-id",
            sequence_number=0,
            chunk_type=ChunkType.CHILD,
            text=" ",
            start_ms=0,
            end_ms=1000,
            token_count=1,
        )
