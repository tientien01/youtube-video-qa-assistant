from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, Self

from app.application.ports.repositories import IngestJobRepository, TranscriptRepository, VideoRepository
from app.domain.entities import AttemptOutcome, IngestStage, TranscriptType


@dataclass(frozen=True, slots=True)
class IngestAttemptReport:
    provider: str
    stage: IngestStage
    outcome: AttemptOutcome
    elapsed_ms: int | None = None
    error_code: str | None = None
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class ProcessVideoRequest:
    video_id: str
    canonical_url: str


@dataclass(frozen=True, slots=True)
class CanonicalTranscriptSegment:
    sequence_number: int
    original_text: str
    normalized_text: str
    start_ms: int
    end_ms: int


@dataclass(frozen=True, slots=True)
class TranscriptQualityDiagnostics:
    source_segment_count: int
    canonical_segment_count: int
    removed_duplicate_count: int
    caption_span_ms: int
    covered_ms: int
    largest_gap_ms: int


@dataclass(frozen=True, slots=True)
class CanonicalTranscriptPublication:
    provider: str
    provider_version: str | None
    language_code: str
    transcript_type: TranscriptType
    content_hash: str
    parser_version: str
    normalizer_version: str
    segments: tuple[CanonicalTranscriptSegment, ...]
    diagnostics: TranscriptQualityDiagnostics


@dataclass(frozen=True, slots=True)
class ProcessedVideo:
    title: str
    channel_title: str | None = None
    thumbnail_url: str | None = None
    duration_ms: int | None = None
    transcript: CanonicalTranscriptPublication | None = None
    attempts: tuple[IngestAttemptReport, ...] = ()


class IngestFailure(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        retryable: bool,
        attempts: tuple[IngestAttemptReport, ...] = (),
    ) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable
        self.attempts = attempts


class IngestProcessor(Protocol):
    name: str

    def process(
        self,
        request: ProcessVideoRequest,
        *,
        report_stage: Callable[[IngestStage], None],
        is_cancelled: Callable[[], bool],
    ) -> ProcessedVideo: ...


class IngestUnitOfWork(Protocol):
    videos: VideoRepository
    jobs: IngestJobRepository
    transcripts: TranscriptRepository

    def __enter__(self) -> Self: ...

    def __exit__(self, exc_type, exc_value, traceback) -> None: ...

    def commit(self) -> None: ...


type IngestUnitOfWorkFactory = Callable[[], IngestUnitOfWork]


class IngestJobRunner(Protocol):
    def submit(self, job_id: str, video_id: str) -> None: ...
