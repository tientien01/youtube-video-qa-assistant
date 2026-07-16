from __future__ import annotations

import html
import json
import re
import unicodedata
from dataclasses import replace
from hashlib import sha256

from app.application.ingest.ports import (
    CanonicalTranscriptPublication,
    CanonicalTranscriptSegment,
    TranscriptQualityDiagnostics,
)
from app.application.ingest.transcript import TranscriptDocument


NORMALIZER_VERSION = "canonical-v1"
PARSER_VERSION = "v1"
_WHITESPACE = re.compile(r"\s+")
_ZERO_WIDTH = str.maketrans("", "", "\u200b\u200c\u200d\ufeff")
_ROLLING_MAX_GAP_MS = 250
_MIN_PARTIAL_OVERLAP_TOKENS = 2


class TranscriptNormalizationError(ValueError):
    """A stable validation failure raised before canonical publication."""


def normalize_transcript(document: TranscriptDocument) -> CanonicalTranscriptPublication:
    """Create deterministic canonical cues while preserving source text and timing."""

    canonical: list[CanonicalTranscriptSegment] = []
    removed_duplicates = 0
    previous_source_start = -1

    for source in document.segments:
        if source.start_ms < previous_source_start:
            raise TranscriptNormalizationError("Transcript cues are not ordered by start time.")
        previous_source_start = source.start_ms
        normalized = normalize_text(source.text)
        if not normalized:
            raise TranscriptNormalizationError("Transcript normalization produced an empty cue.")

        candidate = CanonicalTranscriptSegment(
            sequence_number=len(canonical),
            original_text=source.text,
            normalized_text=normalized,
            start_ms=source.start_ms,
            end_ms=source.end_ms,
        )
        if canonical:
            previous = canonical[-1]
            is_rolling_window = candidate.start_ms <= previous.end_ms + _ROLLING_MAX_GAP_MS
            if is_rolling_window and _same_text(previous.normalized_text, candidate.normalized_text):
                canonical[-1] = replace(previous, end_ms=max(previous.end_ms, candidate.end_ms))
                removed_duplicates += 1
                continue
            if is_rolling_window:
                trimmed = _trim_rolling_prefix(previous.normalized_text, candidate.normalized_text)
                if trimmed != candidate.normalized_text:
                    removed_duplicates += 1
                    if not trimmed:
                        canonical[-1] = replace(previous, end_ms=max(previous.end_ms, candidate.end_ms))
                        continue
                    candidate = replace(candidate, normalized_text=trimmed)

        canonical.append(replace(candidate, sequence_number=len(canonical)))

    if not canonical:
        raise TranscriptNormalizationError("Transcript contains no canonical cues.")
    _validate_canonical(canonical)
    diagnostics = _quality_diagnostics(document, canonical, removed_duplicates)
    content_hash = _content_hash(document, canonical)
    return CanonicalTranscriptPublication(
        provider=document.provider,
        provider_version=document.provider_version,
        language_code=document.language_code,
        transcript_type=document.transcript_type,
        content_hash=content_hash,
        parser_version=f"{document.source_format.value}-{PARSER_VERSION}",
        normalizer_version=NORMALIZER_VERSION,
        segments=tuple(canonical),
        diagnostics=diagnostics,
    )


def normalize_text(value: str) -> str:
    decoded = html.unescape(value).translate(_ZERO_WIDTH).replace("\u00a0", " ")
    return _WHITESPACE.sub(" ", unicodedata.normalize("NFKC", decoded)).strip()


def _same_text(left: str, right: str) -> bool:
    return left.casefold() == right.casefold()


def _trim_rolling_prefix(previous: str, current: str) -> str:
    previous_tokens = previous.split()
    current_tokens = current.split()
    maximum = min(len(previous_tokens), len(current_tokens))
    for size in range(maximum, _MIN_PARTIAL_OVERLAP_TOKENS - 1, -1):
        left = [token.casefold() for token in previous_tokens[-size:]]
        right = [token.casefold() for token in current_tokens[:size]]
        if left == right:
            return " ".join(current_tokens[size:])
    return current


def _validate_canonical(segments: list[CanonicalTranscriptSegment]) -> None:
    previous_start = -1
    for expected_sequence, segment in enumerate(segments):
        if segment.sequence_number != expected_sequence:
            raise TranscriptNormalizationError("Canonical cue sequence is not contiguous.")
        if segment.start_ms < previous_start:
            raise TranscriptNormalizationError("Canonical cues are not monotonic.")
        if segment.start_ms < 0 or segment.end_ms <= segment.start_ms:
            raise TranscriptNormalizationError("Canonical cue timestamp range is invalid.")
        if not segment.normalized_text:
            raise TranscriptNormalizationError("Canonical cue text is empty.")
        previous_start = segment.start_ms


def _quality_diagnostics(
    document: TranscriptDocument,
    segments: list[CanonicalTranscriptSegment],
    removed_duplicates: int,
) -> TranscriptQualityDiagnostics:
    intervals = sorted((segment.start_ms, segment.end_ms) for segment in segments)
    covered_ms = 0
    largest_gap_ms = 0
    merged_start, merged_end = intervals[0]
    for start_ms, end_ms in intervals[1:]:
        if start_ms <= merged_end:
            merged_end = max(merged_end, end_ms)
        else:
            covered_ms += merged_end - merged_start
            largest_gap_ms = max(largest_gap_ms, start_ms - merged_end)
            merged_start, merged_end = start_ms, end_ms
    covered_ms += merged_end - merged_start
    return TranscriptQualityDiagnostics(
        source_segment_count=len(document.segments),
        canonical_segment_count=len(segments),
        removed_duplicate_count=removed_duplicates,
        caption_span_ms=max(end_ms for _, end_ms in intervals) - intervals[0][0],
        covered_ms=covered_ms,
        largest_gap_ms=largest_gap_ms,
    )


def _content_hash(
    document: TranscriptDocument,
    segments: list[CanonicalTranscriptSegment],
) -> str:
    material = {
        "language_code": document.language_code.casefold(),
        "transcript_type": document.transcript_type.value,
        "segments": [[segment.start_ms, segment.end_ms, segment.normalized_text] for segment in segments],
    }
    encoded = json.dumps(material, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return sha256(encoded).hexdigest()
