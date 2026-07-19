from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.application.video import VideoLibraryApplication, VideoNotFound
from app.domain.entities import Chunk, ChunkType, IndexVersion, Transcript, TranscriptType, Video, VideoStatus
from app.infrastructure.db.engine import transactional_session
from app.infrastructure.db.models import ChunkModel, IndexVersionModel, TranscriptModel, VideoModel
from app.infrastructure.db.repositories import (
    SqlAlchemyIndexRepository,
    SqlAlchemyTranscriptRepository,
    SqlAlchemyVideoRepository,
)
from app.infrastructure.db.unit_of_work import SqlAlchemyIngestUnitOfWork


def _application(
    session_factory: sessionmaker[Session],
    *,
    legacy_chunk_count=lambda _video_id: 0,
    delete_legacy_data=lambda _video_id: False,
) -> VideoLibraryApplication:
    return VideoLibraryApplication(
        lambda: SqlAlchemyIngestUnitOfWork(session_factory),
        legacy_chunk_count=legacy_chunk_count,
        delete_legacy_data=delete_legacy_data,
    )


def _seed_ready_video(session_factory: sessionmaker[Session], *, with_index: bool = False) -> Video:
    video = Video(
        youtube_video_id="canonical01",
        canonical_url="https://www.youtube.com/watch?v=canonical01",
        title="Canonical video",
        channel_title="Example channel",
        duration_ms=65_500,
        status=VideoStatus.READY,
    )
    transcript = Transcript(
        video_id=video.id,
        provider="fixture",
        language_code="vi",
        transcript_type=TranscriptType.MANUAL,
        content_hash="canonical-hash",
        parser_version="1",
        normalizer_version="1",
        is_active=True,
    )
    with transactional_session(session_factory) as session:
        SqlAlchemyVideoRepository(session).add(video)
        SqlAlchemyTranscriptRepository(session).add(transcript)
        if with_index:
            index = IndexVersion(
                video_id=video.id,
                transcript_id=transcript.id,
                fingerprint="canonical-index",
                chunker_version="test-v1",
                chunker_config={"target_tokens": 10},
                embedding_provider="fake",
                embedding_model="fake",
                embedding_dimension=2,
            ).activate()
            chunk = Chunk(
                video_id=video.id,
                transcript_id=transcript.id,
                index_version_id=index.id,
                sequence_number=0,
                chunk_type=ChunkType.CHILD,
                text="Canonical chunk.",
                start_ms=0,
                end_ms=1_000,
                token_count=2,
            )
            indexes = SqlAlchemyIndexRepository(session)
            indexes.add_version(index)
            indexes.add_chunks([chunk])
    return video


def test_library_reads_canonical_video_and_legacy_chunk_projection(
    session_factory: sessionmaker[Session],
) -> None:
    video = _seed_ready_video(session_factory)
    application = _application(session_factory, legacy_chunk_count=lambda _video_id: 7)

    listed = application.list()
    selected = application.get(video.youtube_video_id)

    assert listed == [selected]
    assert selected.title == "Canonical video"
    assert selected.duration_seconds == 65
    assert selected.transcript_language == "vi"
    assert selected.chunk_count == 7


def test_library_delete_cascades_sqlite_and_cleans_legacy_data(
    session_factory: sessionmaker[Session],
) -> None:
    video = _seed_ready_video(session_factory, with_index=True)
    cleaned: list[str] = []
    application = _application(
        session_factory,
        delete_legacy_data=lambda video_id: not cleaned.append(video_id),
    )

    assert application.delete(video.youtube_video_id) is True
    assert cleaned == [video.youtube_video_id]

    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(VideoModel)) == 0
        assert session.scalar(select(func.count()).select_from(TranscriptModel)) == 0
        assert session.scalar(select(func.count()).select_from(IndexVersionModel)) == 0
        assert session.scalar(select(func.count()).select_from(ChunkModel)) == 0


def test_library_delete_is_idempotent_for_stale_frontend_entry(
    session_factory: sessionmaker[Session],
) -> None:
    application = _application(session_factory)

    assert application.delete("missing0000") is False

    try:
        application.get("missing0000")
    except VideoNotFound:
        pass
    else:
        raise AssertionError("Missing canonical video should not be returned.")
