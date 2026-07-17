from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.domain.entities import Transcript, TranscriptSegment, TranscriptType, Video
from app.infrastructure.db.engine import create_database_engine, create_session_factory, sqlite_database_url
from app.infrastructure.db.migration_guard import build_alembic_config
from app.infrastructure.db.repositories import SqlAlchemyTranscriptRepository, SqlAlchemyVideoRepository
from app.infrastructure.db.unit_of_work import SqlAlchemyIndexUnitOfWork
from app.infrastructure.vector import QdrantLocalIndex


@pytest.fixture
def index_runtime(tmp_path: Path) -> Iterator[tuple[sessionmaker[Session], QdrantLocalIndex, str]]:
    database_url = sqlite_database_url(tmp_path / "app.db")
    command.upgrade(build_alembic_config(database_url), "head")
    engine: Engine = create_database_engine(database_url)
    session_factory = create_session_factory(engine)
    video = Video(
        id="video-1",
        youtube_video_id="dQw4w9WgXcQ",
        canonical_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        title="Dense index fixture",
    )
    transcript = Transcript(
        id="transcript-1",
        video_id=video.id,
        provider="fixture",
        language_code="vi",
        transcript_type=TranscriptType.MANUAL,
        content_hash="canonical-content-hash",
        parser_version="fixture-v1",
        normalizer_version="canonical-v1",
        is_active=True,
    )
    segments = [
        TranscriptSegment(transcript.id, 0, "Alpha retrieval.", "Alpha retrieval.", 0, 1_000, id="segment-0"),
        TranscriptSegment(transcript.id, 1, "Beta indexing.", "Beta indexing.", 1_000, 2_000, id="segment-1"),
        TranscriptSegment(transcript.id, 2, "Gamma evidence.", "Gamma evidence.", 2_000, 3_000, id="segment-2"),
    ]
    with session_factory.begin() as session:
        SqlAlchemyVideoRepository(session).add(video)
        repository = SqlAlchemyTranscriptRepository(session)
        repository.add(transcript)
        repository.add_segments(segments)
    vector_index = QdrantLocalIndex(tmp_path / "qdrant")
    try:
        yield session_factory, vector_index, video.id
    finally:
        vector_index.close()
        engine.dispose()


def uow_factory(session_factory: sessionmaker[Session]):
    return lambda: SqlAlchemyIndexUnitOfWork(session_factory)
