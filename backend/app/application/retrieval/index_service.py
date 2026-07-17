from __future__ import annotations

import json
import math
from dataclasses import dataclass
from hashlib import sha256
from uuid import NAMESPACE_URL, uuid5

from app.application.chunking import HierarchicalChunker
from app.application.embeddings import EmbeddingIdentity, EmbeddingProvider
from app.application.retrieval.ports import IndexUnitOfWorkFactory, VectorIndex, VectorRecord
from app.domain.entities import Chunk, IndexVersion, IndexVersionStatus


class ActiveTranscriptNotFound(LookupError):
    pass


class EmbeddingModelMismatch(ValueError):
    pass


class IndexBuildError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class DenseSearchHit:
    chunk: Chunk
    score: float


class DenseIndexService:
    """Builds derived vectors from canonical SQLite data and activates them last."""

    def __init__(
        self,
        uow_factory: IndexUnitOfWorkFactory,
        chunker: HierarchicalChunker,
        embedding: EmbeddingProvider,
        vector_index: VectorIndex,
        *,
        embedding_batch_size: int = 32,
    ) -> None:
        if embedding_batch_size <= 0:
            raise ValueError("Embedding batch size must be positive.")
        self._uow_factory = uow_factory
        self._chunker = chunker
        self._embedding = embedding
        self._vectors = vector_index
        self._batch_size = embedding_batch_size

    def health_check(self) -> bool:
        return self._embedding.health_check() and self._vectors.health_check()

    def rebuild(self, video_id: str) -> IndexVersion:
        with self._uow_factory() as uow:
            transcript = uow.transcripts.get_active(video_id)
            if transcript is None:
                raise ActiveTranscriptNotFound(f"Video {video_id} has no active canonical transcript.")
            segments = uow.transcripts.list_segments(transcript.id)
            previous_active = uow.indexes.get_active(video_id)

        chunker_fingerprint = self._chunker.fingerprint(transcript.content_hash)
        provisional = self._chunker.chunk(
            video_id=video_id,
            transcript_id=transcript.id,
            index_version_id="dimension-discovery",
            index_fingerprint=chunker_fingerprint,
            language_code=transcript.language_code,
            segments=segments,
        )
        child_texts = [chunk.text for chunk in provisional.child_chunks]
        vectors = self._embedding.embed_documents(child_texts, batch_size=self._batch_size)
        dimension = _validate_vectors(vectors, expected_count=len(child_texts))
        fingerprint = _index_fingerprint(chunker_fingerprint, self._embedding.identity, dimension)

        with self._uow_factory() as uow:
            existing = uow.indexes.get_by_fingerprint(video_id, fingerprint)
            if existing is not None:
                if existing.status is IndexVersionStatus.READY:
                    return existing
                raise IndexBuildError(
                    f"Index fingerprint {fingerprint} already exists with status {existing.status.value}."
                )

        index_version_id = str(uuid5(NAMESPACE_URL, f"video-knowledge-assistant/index/v1\n{video_id}\n{fingerprint}"))
        chunking = self._chunker.chunk(
            video_id=video_id,
            transcript_id=transcript.id,
            index_version_id=index_version_id,
            index_fingerprint=fingerprint,
            language_code=transcript.language_code,
            segments=segments,
        )
        index_version = IndexVersion(
            id=index_version_id,
            video_id=video_id,
            transcript_id=transcript.id,
            fingerprint=fingerprint,
            chunker_version=chunking.chunker_version,
            chunker_config=self._chunker.config.to_dict(),
            embedding_provider=self._embedding.identity.provider,
            embedding_model=self._embedding.identity.model,
            embedding_revision=self._embedding.identity.revision,
            embedding_dimension=dimension,
            embedding_config=self._embedding.identity.to_config(),
        )

        with self._uow_factory() as uow:
            uow.indexes.add_version(index_version)
            uow.indexes.add_chunks(list(chunking.chunks))
            uow.indexes.add_segment_links(list(chunking.links))
            uow.commit()

        try:
            self._vectors.create(index_version.id, dimension)
            self._vectors.upsert(
                index_version.id,
                [
                    VectorRecord(chunk.id, video_id, index_version.id, vector)
                    for chunk, vector in zip(chunking.child_chunks, vectors, strict=True)
                ],
            )
            with self._uow_factory() as uow:
                activated = uow.indexes.activate(video_id, index_version.id)
                uow.commit()
        except Exception as error:
            self._mark_failed(index_version.id)
            try:
                self._vectors.delete(index_version.id)
            except Exception:
                pass
            raise IndexBuildError(f"Dense index rebuild failed for video {video_id}.") from error

        if previous_active is not None and previous_active.id != activated.id:
            try:
                self._vectors.delete(previous_active.id)
            except Exception:
                pass
        return activated

    def search(self, video_id: str, query: str, *, limit: int = 8) -> list[DenseSearchHit]:
        if limit <= 0:
            return []
        with self._uow_factory() as uow:
            active = uow.indexes.get_active(video_id)
        if active is None:
            return []
        _assert_identity(self._embedding.identity, active)
        vector = self._embedding.embed_query(query)
        if len(vector) != active.embedding_dimension:
            raise EmbeddingModelMismatch(
                f"Query dimension {len(vector)} does not match index dimension {active.embedding_dimension}."
            )
        matches = self._vectors.query(active.id, video_id, vector, limit=limit)
        with self._uow_factory() as uow:
            chunks = uow.indexes.get_chunks(active.id, [match.chunk_id for match in matches])
        chunks_by_id = {chunk.id: chunk for chunk in chunks}
        return [
            DenseSearchHit(chunks_by_id[match.chunk_id], match.score)
            for match in matches
            if match.chunk_id in chunks_by_id
        ]

    def _mark_failed(self, index_version_id: str) -> None:
        try:
            with self._uow_factory() as uow:
                version = uow.indexes.get_version(index_version_id)
                if version is not None and version.status is IndexVersionStatus.BUILDING:
                    uow.indexes.save_version(version.fail())
                    uow.commit()
        except Exception:
            pass


def _validate_vectors(vectors: list[list[float]], *, expected_count: int) -> int:
    if not vectors or len(vectors) != expected_count:
        raise IndexBuildError("Embedding provider returned an unexpected number of vectors.")
    dimension = len(vectors[0])
    if dimension <= 0:
        raise IndexBuildError("Embedding provider returned empty vectors.")
    if any(len(vector) != dimension for vector in vectors):
        raise IndexBuildError("Embedding provider returned inconsistent vector dimensions.")
    if any(not math.isfinite(value) for vector in vectors for value in vector):
        raise IndexBuildError("Embedding provider returned non-finite vector values.")
    return dimension


def _index_fingerprint(chunker_fingerprint: str, identity: EmbeddingIdentity, dimension: int) -> str:
    material = {
        "chunker_fingerprint": chunker_fingerprint,
        "dimension": dimension,
        "embedding": identity.fingerprint_material(),
    }
    return sha256(json.dumps(material, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _assert_identity(identity: EmbeddingIdentity, index_version: IndexVersion) -> None:
    if not identity.matches(index_version):
        raise EmbeddingModelMismatch(
            "Query embedding identity does not match the active index provider, model, revision, "
            "normalization, or instruction policy."
        )
