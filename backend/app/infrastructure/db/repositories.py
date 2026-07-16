from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import (
    Chunk,
    ChunkSegmentLink,
    IndexVersion,
    IngestAttempt,
    IngestJob,
    IngestJobStatus,
    Transcript,
    TranscriptSegment,
    Video,
)
from app.infrastructure.db.models import (
    ChunkModel,
    ChunkSegmentModel,
    IndexVersionModel,
    IngestAttemptModel,
    IngestJobModel,
    TranscriptModel,
    TranscriptSegmentModel,
    VideoModel,
)


class SqlAlchemyVideoRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, video: Video) -> Video:
        self._session.add(
            VideoModel(
                id=video.id,
                youtube_video_id=video.youtube_video_id,
                canonical_url=video.canonical_url,
                title=video.title,
                channel_title=video.channel_title,
                thumbnail_url=video.thumbnail_url,
                duration_ms=video.duration_ms,
                status=video.status,
                created_at=video.created_at,
                updated_at=video.updated_at,
            )
        )
        self._session.flush()
        return video

    def get(self, video_id: str) -> Video | None:
        model = self._session.get(VideoModel, video_id)
        return _video_from_model(model) if model is not None else None

    def get_by_youtube_id(self, youtube_video_id: str) -> Video | None:
        model = self._session.scalar(select(VideoModel).where(VideoModel.youtube_video_id == youtube_video_id))
        return _video_from_model(model) if model is not None else None

    def save(self, video: Video) -> Video:
        model = self._session.get(VideoModel, video.id)
        if model is None:
            raise LookupError(f"Video {video.id} does not exist.")
        model.canonical_url = video.canonical_url
        model.title = video.title
        model.channel_title = video.channel_title
        model.thumbnail_url = video.thumbnail_url
        model.duration_ms = video.duration_ms
        model.status = video.status
        model.updated_at = video.updated_at
        self._session.flush()
        return video

    def list_recent(self, limit: int = 50) -> list[Video]:
        if limit <= 0:
            return []
        models = self._session.scalars(select(VideoModel).order_by(VideoModel.updated_at.desc()).limit(limit)).all()
        return [_video_from_model(model) for model in models]


class SqlAlchemyIngestJobRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, job: IngestJob) -> IngestJob:
        self._session.add(
            IngestJobModel(
                id=job.id,
                video_id=job.video_id,
                status=job.status,
                current_stage=job.current_stage,
                idempotency_key=job.idempotency_key,
                target_fingerprint=job.target_fingerprint,
                retryable=job.retryable,
                error_code=job.error_code,
                error_message=job.error_message,
                created_at=job.created_at,
                started_at=job.started_at,
                finished_at=job.finished_at,
            )
        )
        self._session.flush()
        return job

    def get(self, job_id: str) -> IngestJob | None:
        model = self._session.get(IngestJobModel, job_id)
        return _job_from_model(model) if model is not None else None

    def get_by_idempotency_key(self, idempotency_key: str) -> IngestJob | None:
        model = self._session.scalar(select(IngestJobModel).where(IngestJobModel.idempotency_key == idempotency_key))
        return _job_from_model(model) if model is not None else None

    def find_active(self, video_id: str, target_fingerprint: str) -> IngestJob | None:
        model = self._session.scalar(
            select(IngestJobModel)
            .where(
                IngestJobModel.video_id == video_id,
                IngestJobModel.target_fingerprint == target_fingerprint,
                IngestJobModel.status.in_(
                    (IngestJobStatus.PENDING, IngestJobStatus.RUNNING, IngestJobStatus.RETRY_WAIT)
                ),
            )
            .order_by(IngestJobModel.created_at.desc())
        )
        return _job_from_model(model) if model is not None else None

    def list_running(self) -> list[IngestJob]:
        models = self._session.scalars(
            select(IngestJobModel).where(IngestJobModel.status == IngestJobStatus.RUNNING)
        ).all()
        return [_job_from_model(model) for model in models]

    def save(self, job: IngestJob) -> IngestJob:
        model = self._session.get(IngestJobModel, job.id)
        if model is None:
            raise LookupError(f"Ingest job {job.id} does not exist.")
        model.status = job.status
        model.current_stage = job.current_stage
        model.idempotency_key = job.idempotency_key
        model.target_fingerprint = job.target_fingerprint
        model.retryable = job.retryable
        model.error_code = job.error_code
        model.error_message = job.error_message
        model.started_at = job.started_at
        model.finished_at = job.finished_at
        self._session.flush()
        return job

    def add_attempt(self, attempt: IngestAttempt) -> IngestAttempt:
        self._session.add(
            IngestAttemptModel(
                id=attempt.id,
                ingest_job_id=attempt.ingest_job_id,
                provider=attempt.provider,
                stage=attempt.stage,
                attempt_number=attempt.attempt_number,
                outcome=attempt.outcome,
                elapsed_ms=attempt.elapsed_ms,
                error_code=attempt.error_code,
                error_message=attempt.error_message,
                created_at=attempt.created_at,
            )
        )
        self._session.flush()
        return attempt

    def list_attempts(self, job_id: str) -> list[IngestAttempt]:
        models = self._session.scalars(
            select(IngestAttemptModel)
            .where(IngestAttemptModel.ingest_job_id == job_id)
            .order_by(IngestAttemptModel.attempt_number)
        ).all()
        return [_attempt_from_model(model) for model in models]


class SqlAlchemyTranscriptRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, transcript: Transcript) -> Transcript:
        self._session.add(
            TranscriptModel(
                id=transcript.id,
                video_id=transcript.video_id,
                provider=transcript.provider,
                provider_version=transcript.provider_version,
                language_code=transcript.language_code,
                transcript_type=transcript.transcript_type,
                content_hash=transcript.content_hash,
                parser_version=transcript.parser_version,
                normalizer_version=transcript.normalizer_version,
                is_active=transcript.is_active,
                fetched_at=transcript.fetched_at,
                created_at=transcript.created_at,
            )
        )
        self._session.flush()
        return transcript

    def get(self, transcript_id: str) -> Transcript | None:
        model = self._session.get(TranscriptModel, transcript_id)
        return _transcript_from_model(model) if model is not None else None

    def add_segments(self, segments: list[TranscriptSegment]) -> list[TranscriptSegment]:
        self._session.add_all(
            [
                TranscriptSegmentModel(
                    id=segment.id,
                    transcript_id=segment.transcript_id,
                    sequence_number=segment.sequence_number,
                    original_text=segment.original_text,
                    normalized_text=segment.normalized_text,
                    start_ms=segment.start_ms,
                    end_ms=segment.end_ms,
                )
                for segment in segments
            ]
        )
        self._session.flush()
        return segments

    def list_segments(self, transcript_id: str) -> list[TranscriptSegment]:
        models = self._session.scalars(
            select(TranscriptSegmentModel)
            .where(TranscriptSegmentModel.transcript_id == transcript_id)
            .order_by(TranscriptSegmentModel.sequence_number)
        ).all()
        return [_segment_from_model(model) for model in models]


class SqlAlchemyIndexRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_version(self, index_version: IndexVersion) -> IndexVersion:
        self._session.add(
            IndexVersionModel(
                id=index_version.id,
                video_id=index_version.video_id,
                transcript_id=index_version.transcript_id,
                fingerprint=index_version.fingerprint,
                chunker_version=index_version.chunker_version,
                chunker_config=index_version.chunker_config,
                embedding_provider=index_version.embedding_provider,
                embedding_model=index_version.embedding_model,
                embedding_revision=index_version.embedding_revision,
                embedding_dimension=index_version.embedding_dimension,
                status=index_version.status,
                created_at=index_version.created_at,
                activated_at=index_version.activated_at,
            )
        )
        self._session.flush()
        return index_version

    def get_version(self, index_version_id: str) -> IndexVersion | None:
        model = self._session.get(IndexVersionModel, index_version_id)
        return _index_version_from_model(model) if model is not None else None

    def add_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        self._session.add_all(
            [
                ChunkModel(
                    id=chunk.id,
                    video_id=chunk.video_id,
                    transcript_id=chunk.transcript_id,
                    index_version_id=chunk.index_version_id,
                    parent_chunk_id=chunk.parent_chunk_id,
                    sequence_number=chunk.sequence_number,
                    chunk_type=chunk.chunk_type,
                    text=chunk.text,
                    start_ms=chunk.start_ms,
                    end_ms=chunk.end_ms,
                    token_count=chunk.token_count,
                )
                for chunk in chunks
            ]
        )
        self._session.flush()
        return chunks

    def add_segment_links(self, links: list[ChunkSegmentLink]) -> list[ChunkSegmentLink]:
        self._session.add_all(
            [
                ChunkSegmentModel(
                    chunk_id=link.chunk_id,
                    transcript_segment_id=link.transcript_segment_id,
                    position=link.position,
                )
                for link in links
            ]
        )
        self._session.flush()
        return links


def _video_from_model(model: VideoModel) -> Video:
    return Video(
        id=model.id,
        youtube_video_id=model.youtube_video_id,
        canonical_url=model.canonical_url,
        title=model.title,
        channel_title=model.channel_title,
        thumbnail_url=model.thumbnail_url,
        duration_ms=model.duration_ms,
        status=model.status,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _job_from_model(model: IngestJobModel) -> IngestJob:
    return IngestJob(
        id=model.id,
        video_id=model.video_id,
        status=model.status,
        current_stage=model.current_stage,
        idempotency_key=model.idempotency_key,
        target_fingerprint=model.target_fingerprint,
        retryable=model.retryable,
        error_code=model.error_code,
        error_message=model.error_message,
        created_at=model.created_at,
        started_at=model.started_at,
        finished_at=model.finished_at,
    )


def _attempt_from_model(model: IngestAttemptModel) -> IngestAttempt:
    return IngestAttempt(
        id=model.id,
        ingest_job_id=model.ingest_job_id,
        provider=model.provider,
        stage=model.stage,
        attempt_number=model.attempt_number,
        outcome=model.outcome,
        elapsed_ms=model.elapsed_ms,
        error_code=model.error_code,
        error_message=model.error_message,
        created_at=model.created_at,
    )


def _transcript_from_model(model: TranscriptModel) -> Transcript:
    return Transcript(
        id=model.id,
        video_id=model.video_id,
        provider=model.provider,
        provider_version=model.provider_version,
        language_code=model.language_code,
        transcript_type=model.transcript_type,
        content_hash=model.content_hash,
        parser_version=model.parser_version,
        normalizer_version=model.normalizer_version,
        is_active=model.is_active,
        fetched_at=model.fetched_at,
        created_at=model.created_at,
    )


def _segment_from_model(model: TranscriptSegmentModel) -> TranscriptSegment:
    return TranscriptSegment(
        id=model.id,
        transcript_id=model.transcript_id,
        sequence_number=model.sequence_number,
        original_text=model.original_text,
        normalized_text=model.normalized_text,
        start_ms=model.start_ms,
        end_ms=model.end_ms,
    )


def _index_version_from_model(model: IndexVersionModel) -> IndexVersion:
    return IndexVersion(
        id=model.id,
        video_id=model.video_id,
        transcript_id=model.transcript_id,
        fingerprint=model.fingerprint,
        chunker_version=model.chunker_version,
        chunker_config=model.chunker_config,
        embedding_provider=model.embedding_provider,
        embedding_model=model.embedding_model,
        embedding_revision=model.embedding_revision,
        embedding_dimension=model.embedding_dimension,
        status=model.status,
        created_at=model.created_at,
        activated_at=model.activated_at,
    )
