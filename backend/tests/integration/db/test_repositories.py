import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.domain.entities import (
    AttemptOutcome,
    Chunk,
    ChunkSegmentLink,
    ChunkType,
    IndexVersion,
    IngestAttempt,
    IngestJob,
    IngestStage,
    Transcript,
    TranscriptSegment,
    TranscriptType,
    Video,
)
from app.infrastructure.db.engine import transactional_session
from app.infrastructure.db.models import (
    ChunkSegmentModel,
    IngestJobModel,
    TranscriptModel,
    VideoModel,
)
from app.infrastructure.db.repositories import (
    SqlAlchemyIndexRepository,
    SqlAlchemyIngestJobRepository,
    SqlAlchemyTranscriptRepository,
    SqlAlchemyVideoRepository,
)


def test_repositories_persist_complete_canonical_graph(session_factory: sessionmaker[Session]) -> None:
    video = Video(
        youtube_video_id="dQw4w9WgXcQ",
        canonical_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        title="Persistence example",
        duration_ms=120_000,
    )
    job = IngestJob(video_id=video.id)
    attempt = IngestAttempt(
        ingest_job_id=job.id,
        provider="youtube-transcript-api",
        stage=IngestStage.FETCHING_TRANSCRIPT,
        attempt_number=1,
        outcome=AttemptOutcome.SUCCEEDED,
        elapsed_ms=25,
    )
    transcript = Transcript(
        video_id=video.id,
        provider="youtube-transcript-api",
        language_code="en",
        transcript_type=TranscriptType.MANUAL,
        content_hash="transcript-hash",
        parser_version="1",
        normalizer_version="1",
        is_active=True,
    )
    segments = [
        TranscriptSegment(
            transcript_id=transcript.id,
            sequence_number=0,
            original_text="First segment.",
            normalized_text="First segment.",
            start_ms=0,
            end_ms=2_000,
        ),
        TranscriptSegment(
            transcript_id=transcript.id,
            sequence_number=1,
            original_text="Second segment.",
            normalized_text="Second segment.",
            start_ms=2_000,
            end_ms=4_000,
        ),
    ]
    index_version = IndexVersion(
        video_id=video.id,
        transcript_id=transcript.id,
        fingerprint="index-fingerprint",
        chunker_version="hierarchical-v1",
        chunker_config={"target_tokens": 320},
        embedding_provider="fake",
        embedding_model="fake-model",
        embedding_dimension=8,
    )
    parent = Chunk(
        video_id=video.id,
        transcript_id=transcript.id,
        index_version_id=index_version.id,
        sequence_number=0,
        chunk_type=ChunkType.PARENT,
        text="First segment. Second segment.",
        start_ms=0,
        end_ms=4_000,
        token_count=6,
    )
    child = Chunk(
        video_id=video.id,
        transcript_id=transcript.id,
        index_version_id=index_version.id,
        parent_chunk_id=parent.id,
        sequence_number=0,
        chunk_type=ChunkType.CHILD,
        text="First segment.",
        start_ms=0,
        end_ms=2_000,
        token_count=3,
    )

    with transactional_session(session_factory) as session:
        SqlAlchemyVideoRepository(session).add(video)
        job_repository = SqlAlchemyIngestJobRepository(session)
        job_repository.add(job)
        job_repository.add_attempt(attempt)
        transcript_repository = SqlAlchemyTranscriptRepository(session)
        transcript_repository.add(transcript)
        transcript_repository.add_segments(segments)
        index_repository = SqlAlchemyIndexRepository(session)
        index_repository.add_version(index_version)
        index_repository.add_chunks([parent, child])
        index_repository.add_segment_links(
            [
                ChunkSegmentLink(parent.id, segments[0].id, 0),
                ChunkSegmentLink(parent.id, segments[1].id, 1),
                ChunkSegmentLink(child.id, segments[0].id, 0),
            ]
        )

    with session_factory() as session:
        assert SqlAlchemyVideoRepository(session).get_by_youtube_id(video.youtube_video_id) == video
        assert SqlAlchemyIngestJobRepository(session).get(job.id) == job
        assert SqlAlchemyTranscriptRepository(session).list_segments(transcript.id) == segments
        assert SqlAlchemyIndexRepository(session).get_version(index_version.id) == index_version
        links = session.scalars(
            select(ChunkSegmentModel)
            .where(ChunkSegmentModel.chunk_id == parent.id)
            .order_by(ChunkSegmentModel.position)
        ).all()
        assert [link.transcript_segment_id for link in links] == [segments[0].id, segments[1].id]


def test_foreign_keys_are_enforced(session_factory: sessionmaker[Session]) -> None:
    orphan_job = IngestJob(video_id="missing-video")
    with pytest.raises(IntegrityError):
        with transactional_session(session_factory) as session:
            SqlAlchemyIngestJobRepository(session).add(orphan_job)


def test_transaction_rolls_back_all_writes(session_factory: sessionmaker[Session]) -> None:
    first = Video(
        youtube_video_id="duplicate-id",
        canonical_url="https://www.youtube.com/watch?v=duplicate-id",
        title="First",
    )
    duplicate = Video(
        youtube_video_id="duplicate-id",
        canonical_url="https://www.youtube.com/watch?v=duplicate-id",
        title="Duplicate",
    )

    with pytest.raises(IntegrityError):
        with transactional_session(session_factory) as session:
            repository = SqlAlchemyVideoRepository(session)
            repository.add(first)
            repository.add(duplicate)

    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(VideoModel)) == 0


def test_deleting_video_cascades_canonical_children(session_factory: sessionmaker[Session]) -> None:
    video = Video(
        youtube_video_id="cascade-id",
        canonical_url="https://www.youtube.com/watch?v=cascade-id",
        title="Cascade",
    )
    job = IngestJob(video_id=video.id)
    transcript = Transcript(
        video_id=video.id,
        provider="fixture",
        language_code="vi",
        transcript_type=TranscriptType.GENERATED,
        content_hash="cascade-hash",
        parser_version="1",
        normalizer_version="1",
    )

    with transactional_session(session_factory) as session:
        SqlAlchemyVideoRepository(session).add(video)
        SqlAlchemyIngestJobRepository(session).add(job)
        SqlAlchemyTranscriptRepository(session).add(transcript)

    with transactional_session(session_factory) as session:
        model = session.get(VideoModel, video.id)
        assert model is not None
        session.delete(model)

    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(VideoModel)) == 0
        assert session.scalar(select(func.count()).select_from(IngestJobModel)) == 0
        assert session.scalar(select(func.count()).select_from(TranscriptModel)) == 0
