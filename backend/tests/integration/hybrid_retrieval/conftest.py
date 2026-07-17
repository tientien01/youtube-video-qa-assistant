from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from qdrant_client import QdrantClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.chunking import ChunkerConfig, HierarchicalChunker
from app.application.retrieval import DenseIndexService
from app.domain.entities import Transcript, TranscriptSegment, TranscriptType, Video
from app.infrastructure.db.engine import create_database_engine, create_session_factory, sqlite_database_url
from app.infrastructure.db.migration_guard import build_alembic_config
from app.infrastructure.db.repositories import SqlAlchemyTranscriptRepository, SqlAlchemyVideoRepository
from app.infrastructure.db.unit_of_work import SqlAlchemyIndexUnitOfWork
from app.infrastructure.embeddings import DeterministicFakeEmbedding
from app.infrastructure.vector import QdrantLocalIndex
from tests.unit.chunking.helpers import PunctuationSegmenter, WhitespaceTokenCounter


@pytest.fixture
def hybrid_runtime(tmp_path: Path) -> Iterator[dict[str, object]]:
    database_url = sqlite_database_url(tmp_path / "app.db")
    command.upgrade(build_alembic_config(database_url), "head")
    engine: Engine = create_database_engine(database_url)
    session_factory = create_session_factory(engine)
    _persist_video(
        session_factory,
        video_id="video-1",
        transcript_id="transcript-1",
        youtube_id="dQw4w9WgXcQ",
        texts=["Alpha exact keyword.", "Beta semantic concept.", "Gamma final evidence."],
    )
    _persist_video(
        session_factory,
        video_id="video-2",
        transcript_id="transcript-2",
        youtube_id="otherVideo1",
        texts=["Alpha private second video."],
    )
    qdrant_client = QdrantClient(":memory:")
    vector_index = QdrantLocalIndex(client=qdrant_client)
    embedding = DeterministicFakeEmbedding(dimension=64)
    chunker = HierarchicalChunker(
        PunctuationSegmenter(),
        WhitespaceTokenCounter(),
        ChunkerConfig(child_target_tokens=3, child_max_tokens=5, child_overlap_tokens=0),
    )
    def uow():
        return SqlAlchemyIndexUnitOfWork(session_factory)

    dense = DenseIndexService(uow, chunker, embedding, vector_index)
    dense.rebuild("video-1")
    dense.rebuild("video-2")
    try:
        yield {"session_factory": session_factory, "uow": uow, "dense": dense}
    finally:
        vector_index.close()
        engine.dispose()


def _persist_video(
    session_factory: sessionmaker[Session],
    *,
    video_id: str,
    transcript_id: str,
    youtube_id: str,
    texts: list[str],
) -> None:
    video = Video(
        id=video_id,
        youtube_video_id=youtube_id,
        canonical_url=f"https://youtu.be/{youtube_id}",
        title=f"Fixture {video_id}",
    )
    transcript = Transcript(
        video_id=video.id,
        provider="fixture",
        language_code="en",
        transcript_type=TranscriptType.MANUAL,
        content_hash=f"hash-{transcript_id}",
        parser_version="fixture-v1",
        normalizer_version="canonical-v1",
        id=transcript_id,
        is_active=True,
    )
    segments = [
        TranscriptSegment(
            transcript.id,
            sequence,
            text,
            text,
            sequence * 1_000,
            (sequence + 1) * 1_000,
            id=f"{transcript_id}-segment-{sequence}",
        )
        for sequence, text in enumerate(texts)
    ]
    with session_factory.begin() as session:
        SqlAlchemyVideoRepository(session).add(video)
        repository = SqlAlchemyTranscriptRepository(session)
        repository.add(transcript)
        repository.add_segments(segments)
