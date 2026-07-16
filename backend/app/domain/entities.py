from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4


def new_id() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(UTC)


class VideoStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class IngestJobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    RETRY_WAIT = "retry_wait"
    READY = "ready"
    FAILED = "failed"
    CANCELLED = "cancelled"


class IngestStage(StrEnum):
    PENDING = "pending"
    FETCHING_METADATA = "fetching_metadata"
    FETCHING_TRANSCRIPT = "fetching_transcript"
    NORMALIZING = "normalizing"
    VALIDATING = "validating"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    COMMITTING = "committing"
    COMPLETE = "complete"


class AttemptOutcome(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class TranscriptType(StrEnum):
    MANUAL = "manual"
    GENERATED = "generated"
    ASR = "asr"


class IndexVersionStatus(StrEnum):
    BUILDING = "building"
    READY = "ready"
    FAILED = "failed"
    INACTIVE = "inactive"


class ChunkType(StrEnum):
    CHILD = "child"
    PARENT = "parent"


@dataclass(frozen=True, slots=True)
class Video:
    youtube_video_id: str
    canonical_url: str
    title: str
    id: str = field(default_factory=new_id)
    channel_title: str | None = None
    thumbnail_url: str | None = None
    duration_ms: int | None = None
    status: VideoStatus = VideoStatus.PENDING
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not self.youtube_video_id.strip():
            raise ValueError("youtube_video_id cannot be empty.")
        if self.duration_ms is not None and self.duration_ms < 0:
            raise ValueError("duration_ms cannot be negative.")


@dataclass(frozen=True, slots=True)
class IngestJob:
    video_id: str
    id: str = field(default_factory=new_id)
    status: IngestJobStatus = IngestJobStatus.PENDING
    current_stage: IngestStage = IngestStage.PENDING
    idempotency_key: str | None = None
    target_fingerprint: str | None = None
    retryable: bool = False
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    started_at: datetime | None = None
    finished_at: datetime | None = None

    def start(self, *, now: datetime | None = None) -> IngestJob:
        if self.status is not IngestJobStatus.PENDING:
            raise ValueError(f"Cannot start ingest job from status {self.status.value}.")
        return replace(
            self,
            status=IngestJobStatus.RUNNING,
            current_stage=IngestStage.FETCHING_METADATA,
            started_at=now or utc_now(),
            finished_at=None,
            retryable=False,
            error_code=None,
            error_message=None,
        )

    def advance(self, stage: IngestStage) -> IngestJob:
        if self.status is not IngestJobStatus.RUNNING:
            raise ValueError(f"Cannot advance ingest job from status {self.status.value}.")
        if stage in {IngestStage.PENDING, IngestStage.COMPLETE}:
            raise ValueError(f"Cannot advance directly to stage {stage.value}.")
        if _stage_position(stage) <= _stage_position(self.current_stage):
            raise ValueError(f"Invalid ingest stage transition: {self.current_stage.value} -> {stage.value}.")
        return replace(self, current_stage=stage)

    def succeed(self, *, now: datetime | None = None) -> IngestJob:
        if self.status is not IngestJobStatus.RUNNING or self.current_stage is not IngestStage.COMMITTING:
            raise ValueError("An ingest job can become ready only after committing.")
        return replace(
            self,
            status=IngestJobStatus.READY,
            current_stage=IngestStage.COMPLETE,
            retryable=False,
            error_code=None,
            error_message=None,
            finished_at=now or utc_now(),
        )

    def fail(
        self,
        *,
        error_code: str,
        error_message: str,
        retryable: bool,
        now: datetime | None = None,
    ) -> IngestJob:
        if self.status not in {IngestJobStatus.PENDING, IngestJobStatus.RUNNING, IngestJobStatus.RETRY_WAIT}:
            raise ValueError(f"Cannot fail ingest job from status {self.status.value}.")
        return replace(
            self,
            status=IngestJobStatus.FAILED,
            retryable=retryable,
            error_code=error_code,
            error_message=error_message,
            finished_at=now or utc_now(),
        )

    def cancel(self, *, now: datetime | None = None) -> IngestJob:
        if self.status not in {IngestJobStatus.PENDING, IngestJobStatus.RUNNING, IngestJobStatus.RETRY_WAIT}:
            raise ValueError(f"Cannot cancel ingest job from status {self.status.value}.")
        return replace(
            self,
            status=IngestJobStatus.CANCELLED,
            retryable=False,
            error_code="INGEST_CANCELLED",
            error_message="Ingest was cancelled.",
            finished_at=now or utc_now(),
        )

    def retry(self) -> IngestJob:
        if self.status is not IngestJobStatus.FAILED or not self.retryable:
            raise ValueError("Only a retryable failed ingest job can be retried.")
        return replace(
            self,
            status=IngestJobStatus.PENDING,
            current_stage=IngestStage.PENDING,
            retryable=False,
            error_code=None,
            error_message=None,
            started_at=None,
            finished_at=None,
        )


_INGEST_STAGE_ORDER = tuple(IngestStage)


def _stage_position(stage: IngestStage) -> int:
    return _INGEST_STAGE_ORDER.index(stage)


@dataclass(frozen=True, slots=True)
class IngestAttempt:
    ingest_job_id: str
    provider: str
    stage: IngestStage
    attempt_number: int
    outcome: AttemptOutcome
    id: str = field(default_factory=new_id)
    elapsed_ms: int | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, slots=True)
class Transcript:
    video_id: str
    provider: str
    language_code: str
    transcript_type: TranscriptType
    content_hash: str
    parser_version: str
    normalizer_version: str
    id: str = field(default_factory=new_id)
    provider_version: str | None = None
    is_active: bool = False
    quality_diagnostics: dict[str, int] = field(default_factory=dict)
    fetched_at: datetime = field(default_factory=utc_now)
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, slots=True)
class TranscriptSegment:
    transcript_id: str
    sequence_number: int
    original_text: str
    normalized_text: str
    start_ms: int
    end_ms: int
    id: str = field(default_factory=new_id)

    def __post_init__(self) -> None:
        if self.sequence_number < 0:
            raise ValueError("sequence_number cannot be negative.")
        if self.start_ms < 0 or self.end_ms <= self.start_ms:
            raise ValueError("Transcript segment timestamps are invalid.")
        if not self.normalized_text.strip():
            raise ValueError("normalized_text cannot be empty.")


@dataclass(frozen=True, slots=True)
class IndexVersion:
    video_id: str
    transcript_id: str
    fingerprint: str
    chunker_version: str
    chunker_config: dict[str, object]
    embedding_provider: str
    embedding_model: str
    embedding_dimension: int
    id: str = field(default_factory=new_id)
    embedding_revision: str | None = None
    status: IndexVersionStatus = IndexVersionStatus.BUILDING
    created_at: datetime = field(default_factory=utc_now)
    activated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class Chunk:
    video_id: str
    transcript_id: str
    index_version_id: str
    sequence_number: int
    chunk_type: ChunkType
    text: str
    start_ms: int
    end_ms: int
    token_count: int
    id: str = field(default_factory=new_id)
    parent_chunk_id: str | None = None

    def __post_init__(self) -> None:
        if self.sequence_number < 0 or self.token_count <= 0:
            raise ValueError("Chunk sequence and token count are invalid.")
        if self.start_ms < 0 or self.end_ms <= self.start_ms:
            raise ValueError("Chunk timestamps are invalid.")
        if not self.text.strip():
            raise ValueError("Chunk text cannot be empty.")


@dataclass(frozen=True, slots=True)
class ChunkSegmentLink:
    chunk_id: str
    transcript_segment_id: str
    position: int

    def __post_init__(self) -> None:
        if self.position < 0:
            raise ValueError("position cannot be negative.")
