from __future__ import annotations

from pathlib import Path

from qdrant_client import QdrantClient, models

from app.application.retrieval.ports import VectorMatch, VectorRecord


class QdrantLocalIndex:
    """One local Qdrant collection per immutable SQLite index version."""

    def __init__(self, path: Path | None = None, *, client: QdrantClient | None = None) -> None:
        if client is None and path is None:
            raise ValueError("A Qdrant local path or client is required.")
        if path is not None:
            path.mkdir(parents=True, exist_ok=True)
        self._client = client or QdrantClient(path=str(path))

    def health_check(self) -> bool:
        try:
            self._client.get_collections()
        except Exception:
            return False
        return True

    def close(self) -> None:
        self._client.close()

    def create(self, index_version_id: str, dimension: int) -> None:
        if dimension <= 0:
            raise ValueError("Vector dimension must be positive.")
        collection = _collection_name(index_version_id)
        if self._client.collection_exists(collection):
            self._client.delete_collection(collection)
        self._client.create_collection(
            collection_name=collection,
            vectors_config=models.VectorParams(size=dimension, distance=models.Distance.COSINE),
        )

    def upsert(self, index_version_id: str, records: list[VectorRecord]) -> None:
        if not records:
            return
        self._client.upsert(
            collection_name=_collection_name(index_version_id),
            wait=True,
            points=[
                models.PointStruct(
                    id=record.chunk_id,
                    vector=record.vector,
                    payload={
                        "chunk_id": record.chunk_id,
                        "video_id": record.video_id,
                        "index_version_id": record.index_version_id,
                    },
                )
                for record in records
            ],
        )

    def query(
        self,
        index_version_id: str,
        video_id: str,
        vector: list[float],
        *,
        limit: int,
    ) -> list[VectorMatch]:
        if limit <= 0:
            return []
        response = self._client.query_points(
            collection_name=_collection_name(index_version_id),
            query=vector,
            query_filter=models.Filter(
                must=[models.FieldCondition(key="video_id", match=models.MatchValue(value=video_id))]
            ),
            limit=limit,
            with_payload=True,
        )
        return [
            VectorMatch(chunk_id=str(point.payload["chunk_id"]), score=float(point.score))
            for point in response.points
            if point.payload is not None and "chunk_id" in point.payload
        ]

    def delete(self, index_version_id: str) -> bool:
        collection = _collection_name(index_version_id)
        if not self._client.collection_exists(collection):
            return False
        self._client.delete_collection(collection)
        return True


def _collection_name(index_version_id: str) -> str:
    return f"index_{index_version_id.replace('-', '_')}"
