from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum as PythonEnum

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from app.domain.entities import (
    AttemptOutcome,
    ChunkType,
    IndexVersionStatus,
    IngestJobStatus,
    IngestStage,
    TranscriptType,
    VideoStatus,
)


NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UTCDateTime(TypeDecorator[datetime]):
    """Persist UTC datetimes and always restore timezone-aware domain values."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("UTCDateTime requires a timezone-aware datetime.")
        normalized = value.astimezone(UTC)
        return normalized.replace(tzinfo=None) if dialect.name == "sqlite" else normalized

    def process_result_value(self, value: datetime | None, _dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _enum_type(enum_class: type[PythonEnum], name: str) -> Enum:
    return Enum(
        enum_class,
        name=name,
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
        values_callable=lambda values: [item.value for item in values],
    )


class VideoModel(Base):
    __tablename__ = "videos"
    __table_args__ = (CheckConstraint("duration_ms IS NULL OR duration_ms >= 0", name="duration_non_negative"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    youtube_video_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    canonical_url: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    channel_title: Mapped[str | None] = mapped_column(Text)
    thumbnail_url: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[VideoStatus] = mapped_column(_enum_type(VideoStatus, "video_status"), index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    ingest_jobs: Mapped[list[IngestJobModel]] = relationship(back_populates="video", cascade="all, delete-orphan")
    transcripts: Mapped[list[TranscriptModel]] = relationship(back_populates="video", cascade="all, delete-orphan")
    index_versions: Mapped[list[IndexVersionModel]] = relationship(back_populates="video", cascade="all, delete-orphan")


class IngestJobModel(Base):
    __tablename__ = "ingest_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    video_id: Mapped[str] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), index=True)
    status: Mapped[IngestJobStatus] = mapped_column(_enum_type(IngestJobStatus, "ingest_job_status"), index=True)
    current_stage: Mapped[IngestStage] = mapped_column(_enum_type(IngestStage, "ingest_stage"))
    idempotency_key: Mapped[str | None] = mapped_column(String(64))
    target_fingerprint: Mapped[str | None] = mapped_column(String(128))
    retryable: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.current_timestamp())
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime())

    video: Mapped[VideoModel] = relationship(back_populates="ingest_jobs")
    attempts: Mapped[list[IngestAttemptModel]] = relationship(
        back_populates="ingest_job",
        cascade="all, delete-orphan",
    )


class IngestAttemptModel(Base):
    __tablename__ = "ingest_attempts"
    __table_args__ = (
        CheckConstraint("attempt_number > 0", name="attempt_number_positive"),
        CheckConstraint("elapsed_ms IS NULL OR elapsed_ms >= 0", name="elapsed_non_negative"),
        UniqueConstraint("ingest_job_id", "attempt_number", name="uq_ingest_attempts_job_number"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    ingest_job_id: Mapped[str] = mapped_column(ForeignKey("ingest_jobs.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(64))
    stage: Mapped[IngestStage] = mapped_column(_enum_type(IngestStage, "ingest_attempt_stage"))
    attempt_number: Mapped[int] = mapped_column(Integer)
    outcome: Mapped[AttemptOutcome] = mapped_column(_enum_type(AttemptOutcome, "ingest_attempt_outcome"))
    elapsed_ms: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.current_timestamp())

    ingest_job: Mapped[IngestJobModel] = relationship(back_populates="attempts")


class TranscriptModel(Base):
    __tablename__ = "transcripts"
    __table_args__ = (
        UniqueConstraint("video_id", "provider", "content_hash", name="uq_transcripts_video_provider_hash"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    video_id: Mapped[str] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(64))
    provider_version: Mapped[str | None] = mapped_column(String(64))
    language_code: Mapped[str] = mapped_column(String(35), index=True)
    transcript_type: Mapped[TranscriptType] = mapped_column(_enum_type(TranscriptType, "transcript_type"))
    content_hash: Mapped[str] = mapped_column(String(128))
    parser_version: Mapped[str] = mapped_column(String(64))
    normalizer_version: Mapped[str] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", index=True)
    fetched_at: Mapped[datetime] = mapped_column(UTCDateTime())
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.current_timestamp())

    video: Mapped[VideoModel] = relationship(back_populates="transcripts")
    segments: Mapped[list[TranscriptSegmentModel]] = relationship(
        back_populates="transcript",
        cascade="all, delete-orphan",
        order_by="TranscriptSegmentModel.sequence_number",
    )
    index_versions: Mapped[list[IndexVersionModel]] = relationship(back_populates="transcript")


class TranscriptSegmentModel(Base):
    __tablename__ = "transcript_segments"
    __table_args__ = (
        CheckConstraint("sequence_number >= 0", name="sequence_non_negative"),
        CheckConstraint("start_ms >= 0 AND end_ms > start_ms", name="timestamp_range_valid"),
        UniqueConstraint("transcript_id", "sequence_number", name="uq_transcript_segments_transcript_sequence"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    transcript_id: Mapped[str] = mapped_column(ForeignKey("transcripts.id", ondelete="CASCADE"), index=True)
    sequence_number: Mapped[int] = mapped_column(Integer)
    original_text: Mapped[str] = mapped_column(Text)
    normalized_text: Mapped[str] = mapped_column(Text)
    start_ms: Mapped[int] = mapped_column(Integer)
    end_ms: Mapped[int] = mapped_column(Integer)

    transcript: Mapped[TranscriptModel] = relationship(back_populates="segments")
    chunk_links: Mapped[list[ChunkSegmentModel]] = relationship(
        back_populates="transcript_segment",
        cascade="all, delete-orphan",
    )


class IndexVersionModel(Base):
    __tablename__ = "index_versions"
    __table_args__ = (
        CheckConstraint("embedding_dimension > 0", name="embedding_dimension_positive"),
        UniqueConstraint("video_id", "fingerprint", name="uq_index_versions_video_fingerprint"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    video_id: Mapped[str] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), index=True)
    transcript_id: Mapped[str] = mapped_column(ForeignKey("transcripts.id", ondelete="CASCADE"), index=True)
    fingerprint: Mapped[str] = mapped_column(String(128))
    chunker_version: Mapped[str] = mapped_column(String(64))
    chunker_config: Mapped[dict[str, object]] = mapped_column(JSON)
    embedding_provider: Mapped[str] = mapped_column(String(64))
    embedding_model: Mapped[str] = mapped_column(String(255))
    embedding_revision: Mapped[str | None] = mapped_column(String(128))
    embedding_dimension: Mapped[int] = mapped_column(Integer)
    status: Mapped[IndexVersionStatus] = mapped_column(
        _enum_type(IndexVersionStatus, "index_version_status"),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.current_timestamp())
    activated_at: Mapped[datetime | None] = mapped_column(UTCDateTime())

    video: Mapped[VideoModel] = relationship(back_populates="index_versions")
    transcript: Mapped[TranscriptModel] = relationship(back_populates="index_versions")
    chunks: Mapped[list[ChunkModel]] = relationship(back_populates="index_version", cascade="all, delete-orphan")


class ChunkModel(Base):
    __tablename__ = "chunks"
    __table_args__ = (
        CheckConstraint("sequence_number >= 0", name="sequence_non_negative"),
        CheckConstraint("start_ms >= 0 AND end_ms > start_ms", name="timestamp_range_valid"),
        CheckConstraint("token_count > 0", name="token_count_positive"),
        UniqueConstraint("index_version_id", "chunk_type", "sequence_number", name="uq_chunks_version_type_sequence"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    video_id: Mapped[str] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), index=True)
    transcript_id: Mapped[str] = mapped_column(ForeignKey("transcripts.id", ondelete="CASCADE"), index=True)
    index_version_id: Mapped[str] = mapped_column(ForeignKey("index_versions.id", ondelete="CASCADE"), index=True)
    parent_chunk_id: Mapped[str | None] = mapped_column(ForeignKey("chunks.id", ondelete="SET NULL"), index=True)
    sequence_number: Mapped[int] = mapped_column(Integer)
    chunk_type: Mapped[ChunkType] = mapped_column(_enum_type(ChunkType, "chunk_type"))
    text: Mapped[str] = mapped_column(Text)
    start_ms: Mapped[int] = mapped_column(Integer)
    end_ms: Mapped[int] = mapped_column(Integer)
    token_count: Mapped[int] = mapped_column(Integer)

    index_version: Mapped[IndexVersionModel] = relationship(back_populates="chunks")
    parent: Mapped[ChunkModel | None] = relationship(remote_side=[id], back_populates="children")
    children: Mapped[list[ChunkModel]] = relationship(back_populates="parent")
    segment_links: Mapped[list[ChunkSegmentModel]] = relationship(
        back_populates="chunk",
        cascade="all, delete-orphan",
        order_by="ChunkSegmentModel.position",
    )


class ChunkSegmentModel(Base):
    __tablename__ = "chunk_segments"
    __table_args__ = (
        CheckConstraint("position >= 0", name="position_non_negative"),
        UniqueConstraint("chunk_id", "position", name="uq_chunk_segments_chunk_position"),
    )

    chunk_id: Mapped[str] = mapped_column(ForeignKey("chunks.id", ondelete="CASCADE"), primary_key=True)
    transcript_segment_id: Mapped[str] = mapped_column(
        ForeignKey("transcript_segments.id", ondelete="CASCADE"),
        primary_key=True,
    )
    position: Mapped[int] = mapped_column(Integer)

    chunk: Mapped[ChunkModel] = relationship(back_populates="segment_links")
    transcript_segment: Mapped[TranscriptSegmentModel] = relationship(back_populates="chunk_links")


Index("ix_transcripts_video_active", TranscriptModel.video_id, TranscriptModel.is_active)
Index("ix_index_versions_video_status", IndexVersionModel.video_id, IndexVersionModel.status)
Index("uq_ingest_jobs_idempotency_key", IngestJobModel.idempotency_key, unique=True)
Index(
    "uq_ingest_jobs_active_target",
    IngestJobModel.video_id,
    IngestJobModel.target_fingerprint,
    unique=True,
    sqlite_where=text("status IN ('pending', 'running', 'retry_wait')"),
    postgresql_where=text("status IN ('pending', 'running', 'retry_wait')"),
)
