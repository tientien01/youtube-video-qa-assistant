import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.application.chunking import ChunkerConfig, HierarchicalChunker
from app.application.retrieval.index_service import DenseIndexService, EmbeddingModelMismatch, IndexBuildError
from app.application.retrieval.ports import VectorRecord
from app.domain.entities import IndexVersionStatus
from app.infrastructure.db.unit_of_work import SqlAlchemyIndexUnitOfWork
from app.infrastructure.embeddings import DeterministicFakeEmbedding
from app.infrastructure.vector import QdrantLocalIndex
from tests.integration.qdrant_index.conftest import uow_factory
from tests.unit.chunking.helpers import PunctuationSegmenter, WhitespaceTokenCounter


def _chunker() -> HierarchicalChunker:
    return HierarchicalChunker(
        PunctuationSegmenter(),
        WhitespaceTokenCounter(),
        ChunkerConfig(child_target_tokens=2, child_max_tokens=4, child_overlap_tokens=0),
    )


def _service(
    session_factory: sessionmaker[Session],
    vector_index,
    embedding: DeterministicFakeEmbedding,
) -> DenseIndexService:
    return DenseIndexService(uow_factory(session_factory), _chunker(), embedding, vector_index, embedding_batch_size=2)


def test_rebuild_from_sqlite_is_queryable_and_active(index_runtime) -> None:
    session_factory, vector_index, video_id = index_runtime
    service = _service(session_factory, vector_index, DeterministicFakeEmbedding(dimension=64))

    version = service.rebuild(video_id)
    hits = service.search(video_id, "alpha retrieval", limit=3)

    assert version.status is IndexVersionStatus.READY
    assert version.embedding_dimension == 64
    assert hits
    assert "Alpha" in hits[0].chunk.text
    assert service.health_check()


def test_query_model_mismatch_is_rejected(index_runtime) -> None:
    session_factory, vector_index, video_id = index_runtime
    _service(session_factory, vector_index, DeterministicFakeEmbedding(model="model-a")).rebuild(video_id)
    mismatched = _service(session_factory, vector_index, DeterministicFakeEmbedding(model="model-b"))

    with pytest.raises(EmbeddingModelMismatch, match="identity does not match"):
        mismatched.search(video_id, "alpha")


def test_failed_rebuild_preserves_previous_active_index(index_runtime) -> None:
    session_factory, vector_index, video_id = index_runtime
    original = _service(session_factory, vector_index, DeterministicFakeEmbedding(model="model-a"))
    previous = original.rebuild(video_id)
    failing = _FailingUpsertIndex(vector_index)

    with pytest.raises(IndexBuildError, match="rebuild failed"):
        _service(session_factory, failing, DeterministicFakeEmbedding(model="model-b")).rebuild(video_id)

    with SqlAlchemyIndexUnitOfWork(session_factory) as uow:
        active = uow.indexes.get_active(video_id)
    assert active is not None
    assert active.id == previous.id
    assert original.search(video_id, "alpha")


def test_canonical_chunks_survive_derived_index_deletion(index_runtime) -> None:
    session_factory, vector_index, video_id = index_runtime
    version = _service(session_factory, vector_index, DeterministicFakeEmbedding()).rebuild(video_id)

    assert vector_index.delete(version.id)
    with SqlAlchemyIndexUnitOfWork(session_factory) as uow:
        chunks = uow.indexes.list_chunks(version.id)
        segments = uow.transcripts.list_segments(version.transcript_id)

    assert chunks
    assert segments
    assert {chunk.transcript_id for chunk in chunks} == {version.transcript_id}


class _FailingUpsertIndex:
    def __init__(self, delegate: QdrantLocalIndex) -> None:
        self._delegate = delegate

    def health_check(self) -> bool:
        return self._delegate.health_check()

    def create(self, index_version_id: str, dimension: int) -> None:
        self._delegate.create(index_version_id, dimension)

    def upsert(self, index_version_id: str, records: list[VectorRecord]) -> None:
        raise RuntimeError("fixture upsert failure")

    def query(self, index_version_id: str, video_id: str, vector: list[float], *, limit: int):
        return self._delegate.query(index_version_id, video_id, vector, limit=limit)

    def delete(self, index_version_id: str) -> bool:
        return self._delegate.delete(index_version_id)
