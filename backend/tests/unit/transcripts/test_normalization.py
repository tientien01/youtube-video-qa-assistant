import pytest

from app.application.ingest.normalization import TranscriptNormalizationError, normalize_transcript
from app.application.ingest.transcript import SourceTranscriptSegment, SubtitleFormat, TranscriptDocument
from app.domain.entities import TranscriptType


def _document(*segments: SourceTranscriptSegment) -> TranscriptDocument:
    return TranscriptDocument(
        provider="fixture",
        provider_version="1.0",
        language_code="vi",
        transcript_type=TranscriptType.GENERATED,
        source_format=SubtitleFormat.STRUCTURED,
        segments=segments,
    )


def test_normalization_removes_rolling_prefix_and_adjacent_duplicate() -> None:
    result = normalize_transcript(
        _document(
            SourceTranscriptSegment("Xin   chào thế giới", 0, 1_500),
            SourceTranscriptSegment("thế giới &amp; hôm nay", 1_200, 2_500),
            SourceTranscriptSegment("& hôm nay", 2_500, 3_000),
        )
    )

    assert [segment.normalized_text for segment in result.segments] == [
        "Xin chào thế giới",
        "& hôm nay",
    ]
    assert result.segments[1].original_text == "thế giới &amp; hôm nay"
    assert result.segments[1].end_ms == 3_000
    assert result.diagnostics.removed_duplicate_count == 2


def test_legitimate_repetition_is_retained_when_it_is_not_a_rolling_cue() -> None:
    result = normalize_transcript(
        _document(
            SourceTranscriptSegment("Nhắc lại", 0, 500),
            SourceTranscriptSegment("Nhắc lại", 2_000, 2_500),
            SourceTranscriptSegment("rất rất quan trọng", 3_000, 3_500),
        )
    )

    assert [segment.normalized_text for segment in result.segments] == [
        "Nhắc lại",
        "Nhắc lại",
        "rất rất quan trọng",
    ]


def test_equivalent_unicode_html_and_whitespace_have_the_same_hash() -> None:
    first = normalize_transcript(_document(SourceTranscriptSegment("ＲＡＧ\u00a0&amp;  AI", 0, 1_000)))
    second = normalize_transcript(_document(SourceTranscriptSegment("RAG & AI", 0, 1_000)))

    assert first.content_hash == second.content_hash
    assert first.segments[0].normalized_text == "RAG & AI"


def test_invalid_source_order_fails_before_chunking() -> None:
    with pytest.raises(TranscriptNormalizationError, match="ordered"):
        normalize_transcript(
            _document(
                SourceTranscriptSegment("Later", 2_000, 3_000),
                SourceTranscriptSegment("Earlier", 1_000, 1_500),
            )
        )


def test_quality_diagnostics_use_interval_union() -> None:
    result = normalize_transcript(
        _document(
            SourceTranscriptSegment("One", 0, 1_000),
            SourceTranscriptSegment("Two", 500, 1_500),
            SourceTranscriptSegment("Three", 2_000, 2_500),
        )
    )

    assert result.diagnostics.covered_ms == 2_000
    assert result.diagnostics.caption_span_ms == 2_500
    assert result.diagnostics.largest_gap_ms == 500
