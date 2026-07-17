from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace
from hashlib import sha256
from uuid import NAMESPACE_URL, uuid5

from app.application.chunking.models import CHUNKER_VERSION, ChunkerConfig, ChunkingResult, LimitException
from app.application.chunking.ports import SentenceSegmenter, SentenceSpan, TokenCounter
from app.domain.entities import Chunk, ChunkSegmentLink, ChunkType, TranscriptSegment


_SOFT_SPLIT = re.compile(r"(?<=[,;:!?।。！？])\s+")
_WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class _SourceSpan:
    segment: TranscriptSegment
    start_char: int
    end_char: int


@dataclass(frozen=True, slots=True)
class _Unit:
    text: str
    sources: tuple[TranscriptSegment, ...]
    token_count: int

    @property
    def start_ms(self) -> int:
        return self.sources[0].start_ms

    @property
    def end_ms(self) -> int:
        return self.sources[-1].end_ms


@dataclass(frozen=True, slots=True)
class _Packed:
    units: tuple[_Unit, ...]
    token_count: int
    exception_reason: str | None = None

    @property
    def text(self) -> str:
        return " ".join(unit.text for unit in self.units).strip()

    @property
    def sources(self) -> tuple[TranscriptSegment, ...]:
        ordered: dict[str, TranscriptSegment] = {}
        for unit in self.units:
            for source in unit.sources:
                ordered.setdefault(source.id, source)
        return tuple(ordered.values())


class HierarchicalChunker:
    """Owns deterministic timestamp mapping, hierarchy, limits, and overlap."""

    def __init__(
        self,
        sentence_segmenter: SentenceSegmenter,
        token_counter: TokenCounter,
        config: ChunkerConfig | None = None,
    ) -> None:
        self._segmenter = sentence_segmenter
        self._tokens = token_counter
        self.config = config or ChunkerConfig()

    def fingerprint(self, transcript_content_hash: str) -> str:
        material = {
            "chunker_config": self.config.to_dict(),
            "chunker_version": CHUNKER_VERSION,
            "tokenizer_model": self._tokens.model_id,
            "transcript_content_hash": transcript_content_hash,
        }
        encoded = json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
        return sha256(encoded).hexdigest()

    def chunk(
        self,
        *,
        video_id: str,
        transcript_id: str,
        index_version_id: str,
        index_fingerprint: str,
        language_code: str,
        segments: list[TranscriptSegment],
    ) -> ChunkingResult:
        _validate_segments(transcript_id, segments)
        units = self._sentence_units(segments, language_code)
        child_packed = _pack(
            units,
            target_tokens=self.config.child_target_tokens,
            max_tokens=self.config.child_max_tokens,
            max_duration_ms=self.config.child_max_duration_seconds * 1000,
            gap_boundary_ms=round(self.config.timing_gap_boundary_seconds * 1000),
            overlap_tokens=self.config.child_overlap_tokens,
            token_counter=self._tokens,
        )
        parent_packed = _pack(
            units,
            target_tokens=self.config.parent_target_tokens,
            max_tokens=self.config.parent_max_tokens,
            max_duration_ms=self.config.parent_max_duration_seconds * 1000,
            gap_boundary_ms=round(self.config.timing_gap_boundary_seconds * 1000),
            overlap_tokens=0,
            token_counter=self._tokens,
        )
        parents = [
            _to_chunk(
                packed,
                video_id=video_id,
                transcript_id=transcript_id,
                index_version_id=index_version_id,
                fingerprint=index_fingerprint,
                chunk_type=ChunkType.PARENT,
                sequence_number=sequence,
            )
            for sequence, packed in enumerate(parent_packed)
        ]
        children: list[Chunk] = []
        for sequence, packed in enumerate(child_packed):
            parent = _best_parent(packed, parent_packed, parents)
            child = _to_chunk(
                packed,
                video_id=video_id,
                transcript_id=transcript_id,
                index_version_id=index_version_id,
                fingerprint=index_fingerprint,
                chunk_type=ChunkType.CHILD,
                sequence_number=sequence,
            )
            children.append(replace(child, parent_chunk_id=parent.id))

        packed_by_id = [(chunk, packed) for chunk, packed in zip(parents, parent_packed, strict=True)]
        packed_by_id.extend(zip(children, child_packed, strict=True))
        links = tuple(
            ChunkSegmentLink(chunk.id, source.id, position)
            for chunk, packed in packed_by_id
            for position, source in enumerate(packed.sources)
        )
        exceptions = tuple(
            LimitException(chunk.id, packed.exception_reason, tuple(source.id for source in packed.sources))
            for chunk, packed in packed_by_id
            if packed.exception_reason is not None
        )
        return ChunkingResult(chunks=tuple([*parents, *children]), links=links, limit_exceptions=exceptions)

    def _sentence_units(self, segments: list[TranscriptSegment], language_code: str) -> tuple[_Unit, ...]:
        document, source_spans = _build_document(segments)
        sentences = self._segmenter.segment(document, language_code)
        if not sentences:
            sentences = tuple(
                SentenceSpan(document[span.start_char : span.end_char], span.start_char, span.end_char)
                for span in source_spans
            )
        elif len(sentences) == 1 and len(source_spans) > 1 and not re.search(r"[.!?。！？]", document):
            # Punctuation-poor automatic captions are safer at source-cue boundaries.
            sentences = tuple(
                SentenceSpan(document[span.start_char : span.end_char], span.start_char, span.end_char)
                for span in source_spans
            )
        _validate_sentence_spans(document, sentences)
        units: list[_Unit] = []
        for sentence in sentences:
            sources = tuple(
                span.segment
                for span in source_spans
                if sentence.start_char < span.end_char and sentence.end_char > span.start_char
            )
            text = _WHITESPACE.sub(" ", document[sentence.start_char : sentence.end_char]).strip()
            if not text or not sources:
                continue
            if sources[-1].end_ms - sources[0].start_ms > self.config.child_max_duration_seconds * 1000:
                for source in sources:
                    source_text = source.normalized_text.strip()
                    units.extend(self._split_oversized(source_text, (source,)))
                continue
            units.extend(self._split_oversized(text, sources))
        if not units:
            raise ValueError("Sentence segmentation produced no mappable transcript units.")
        return tuple(units)

    def _split_oversized(self, text: str, sources: tuple[TranscriptSegment, ...]) -> list[_Unit]:
        token_count = self._tokens.count(text)
        if token_count <= self.config.child_max_tokens:
            return [_Unit(text, sources, token_count)]
        parts = [part.strip() for part in _SOFT_SPLIT.split(text) if part.strip()]
        if len(parts) == 1:
            parts = text.split()
        packed: list[_Unit] = []
        current: list[str] = []
        for part in parts:
            candidate = " ".join([*current, part])
            if current and self._tokens.count(candidate) > self.config.child_max_tokens:
                current_text = " ".join(current)
                packed.append(_Unit(current_text, sources, self._tokens.count(current_text)))
                current = [part]
            else:
                current.append(part)
        if current:
            current_text = " ".join(current)
            packed.append(_Unit(current_text, sources, self._tokens.count(current_text)))
        return packed


def _build_document(segments: list[TranscriptSegment]) -> tuple[str, tuple[_SourceSpan, ...]]:
    parts: list[str] = []
    spans: list[_SourceSpan] = []
    cursor = 0
    for segment in segments:
        if parts:
            parts.append(" ")
            cursor += 1
        text = segment.normalized_text.strip()
        start = cursor
        parts.append(text)
        cursor += len(text)
        spans.append(_SourceSpan(segment, start, cursor))
    return "".join(parts), tuple(spans)


def _validate_sentence_spans(document: str, spans: tuple[SentenceSpan, ...]) -> None:
    previous_end = 0
    for span in spans:
        if span.start_char < previous_end or span.end_char > len(document):
            raise ValueError("Sentence segmenter returned unordered or out-of-range spans.")
        previous_end = span.end_char


def _validate_segments(transcript_id: str, segments: list[TranscriptSegment]) -> None:
    if not segments:
        raise ValueError("Cannot chunk an empty transcript.")
    for expected, segment in enumerate(segments):
        if segment.transcript_id != transcript_id:
            raise ValueError("All segments must belong to the requested transcript.")
        if segment.sequence_number != expected:
            raise ValueError("Transcript segments must have contiguous sequence numbers.")


def _pack(
    units: tuple[_Unit, ...],
    *,
    target_tokens: int,
    max_tokens: int,
    max_duration_ms: int,
    gap_boundary_ms: int,
    overlap_tokens: int,
    token_counter: TokenCounter,
) -> tuple[_Packed, ...]:
    chunks: list[_Packed] = []
    current: list[_Unit] = []
    added_since_flush = False
    for unit in units:
        gap = unit.start_ms - current[-1].end_ms if current else 0
        candidate_tokens = token_counter.count(" ".join(item.text for item in [*current, unit]))
        candidate_duration = unit.end_ms - current[0].start_ms if current else unit.end_ms - unit.start_ms
        boundary = bool(current) and (
            gap > gap_boundary_ms
            or candidate_tokens > max_tokens
            or candidate_duration > max_duration_ms
            or (token_counter.count(" ".join(item.text for item in current)) >= target_tokens and added_since_flush)
        )
        if boundary:
            if added_since_flush:
                chunks.append(_packed(current, max_tokens, max_duration_ms, token_counter))
                current = [] if gap > gap_boundary_ms else _overlap(current, overlap_tokens)
            else:
                # Overlap is best-effort and must never create an overlap-only chunk.
                current = []
            added_since_flush = False
        current.append(unit)
        added_since_flush = True
    if current and (added_since_flush or not chunks):
        chunks.append(_packed(current, max_tokens, max_duration_ms, token_counter))
    return tuple(chunks)


def _overlap(units: list[_Unit], overlap_tokens: int) -> list[_Unit]:
    selected: list[_Unit] = []
    count = 0
    for unit in reversed(units):
        if selected and count + unit.token_count > overlap_tokens:
            break
        if not selected and unit.token_count > overlap_tokens:
            break
        selected.append(unit)
        count += unit.token_count
    return list(reversed(selected))


def _packed(
    units: list[_Unit],
    max_tokens: int,
    max_duration_ms: int,
    token_counter: TokenCounter,
) -> _Packed:
    token_count = token_counter.count(" ".join(unit.text for unit in units))
    duration = units[-1].end_ms - units[0].start_ms
    reason: str | None = None
    if token_count > max_tokens:
        reason = "indivisible_source_exceeds_token_limit"
    if duration > max_duration_ms:
        reason = "indivisible_source_exceeds_duration_limit"
    return _Packed(tuple(units), token_count, reason)


def _to_chunk(
    packed: _Packed,
    *,
    video_id: str,
    transcript_id: str,
    index_version_id: str,
    fingerprint: str,
    chunk_type: ChunkType,
    sequence_number: int,
) -> Chunk:
    sources = packed.sources
    chunk_id = str(uuid5(NAMESPACE_URL, f"{fingerprint}\n{chunk_type.value}\n{sequence_number}"))
    return Chunk(
        id=chunk_id,
        video_id=video_id,
        transcript_id=transcript_id,
        index_version_id=index_version_id,
        sequence_number=sequence_number,
        chunk_type=chunk_type,
        text=packed.text,
        start_ms=sources[0].start_ms,
        end_ms=sources[-1].end_ms,
        token_count=packed.token_count,
    )


def _best_parent(child: _Packed, packed_parents: tuple[_Packed, ...], parents: list[Chunk]) -> Chunk:
    child_ids = {source.id for source in child.sources}
    scores = [len(child_ids.intersection(source.id for source in packed.sources)) for packed in packed_parents]
    return parents[max(range(len(parents)), key=lambda index: (scores[index], -index))]
