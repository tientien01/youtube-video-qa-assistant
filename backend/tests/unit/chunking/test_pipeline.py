from dataclasses import asdict

from app.application.chunking import ChunkerConfig, HierarchicalChunker
from app.domain.entities import TranscriptSegment

from tests.unit.chunking.helpers import PunctuationSegmenter, WhitespaceTokenCounter


def _segment(sequence: int, text: str, start_ms: int, end_ms: int) -> TranscriptSegment:
    return TranscriptSegment(
        id=f"segment-{sequence}",
        transcript_id="transcript-1",
        sequence_number=sequence,
        original_text=text,
        normalized_text=text,
        start_ms=start_ms,
        end_ms=end_ms,
    )


def _chunk(segments: list[TranscriptSegment], config: ChunkerConfig):
    return HierarchicalChunker(PunctuationSegmenter(), WhitespaceTokenCounter(), config).chunk(
        video_id="video-1",
        transcript_id="transcript-1",
        index_version_id="index-1",
        index_fingerprint="fingerprint-1",
        language_code="vi",
        segments=segments,
    )


def test_preserves_english_and_vietnamese_sentence_boundaries() -> None:
    segments = [
        _segment(0, "Hello world. Đây là câu tiếng Việt.", 0, 2_000),
        _segment(1, "A final sentence!", 2_000, 3_000),
    ]
    result = _chunk(
        segments,
        ChunkerConfig(child_target_tokens=4, child_max_tokens=8, child_overlap_tokens=0),
    )

    assert [chunk.text for chunk in result.child_chunks] == [
        "Hello world. Đây là câu tiếng Việt.",
        "A final sentence!",
    ]
    assert result.child_chunks[0].start_ms == 0
    assert result.child_chunks[0].end_ms == 2_000


def test_gap_boundary_prevents_overlap_across_caption_gap() -> None:
    segments = [
        _segment(0, "First complete sentence.", 0, 1_000),
        _segment(1, "Second complete sentence.", 5_000, 6_000),
    ]
    result = _chunk(
        segments,
        ChunkerConfig(child_target_tokens=3, child_max_tokens=8, child_overlap_tokens=3),
    )

    assert [chunk.text for chunk in result.child_chunks] == [
        "First complete sentence.",
        "Second complete sentence.",
    ]


def test_poor_punctuation_falls_back_to_segments_and_hard_token_splits() -> None:
    segments = [
        _segment(0, "one two three four five six seven", 0, 1_000),
        _segment(1, "eight nine ten", 1_000, 2_000),
    ]
    result = _chunk(
        segments,
        ChunkerConfig(
            child_target_tokens=3,
            child_max_tokens=4,
            child_overlap_tokens=0,
            parent_target_tokens=5,
            parent_max_tokens=8,
        ),
    )

    assert all(chunk.token_count <= 4 for chunk in result.child_chunks)
    assert [chunk.text for chunk in result.child_chunks] == ["one two three four", "five six seven", "eight nine ten"]
    assert [chunk.start_ms for chunk in result.child_chunks] == [0, 0, 1_000]


def test_indivisible_duration_exception_is_recorded() -> None:
    result = _chunk(
        [_segment(0, "A long source cue.", 0, 90_000)],
        ChunkerConfig(child_max_duration_seconds=75, parent_max_duration_seconds=80),
    )

    assert len(result.limit_exceptions) == 2
    assert {item.reason for item in result.limit_exceptions} == {"indivisible_source_exceeds_duration_limit"}
    assert all(item.source_segment_ids == ("segment-0",) for item in result.limit_exceptions)


def test_same_input_and_config_produces_identical_records_and_ids() -> None:
    segments = [_segment(0, "Stable sentence one. Stable sentence two.", 0, 2_000)]
    config = ChunkerConfig(child_target_tokens=3, child_max_tokens=6, child_overlap_tokens=2)

    first = _chunk(segments, config)
    second = _chunk(segments, config)

    assert [asdict(chunk) for chunk in first.chunks] == [asdict(chunk) for chunk in second.chunks]
    assert [asdict(link) for link in first.links] == [asdict(link) for link in second.links]


def test_fingerprint_versions_config_and_tokenizer() -> None:
    chunker = HierarchicalChunker(PunctuationSegmenter(), WhitespaceTokenCounter())

    assert chunker.fingerprint("content-hash") == chunker.fingerprint("content-hash")
    assert chunker.fingerprint("content-hash") != chunker.fingerprint("other-hash")
