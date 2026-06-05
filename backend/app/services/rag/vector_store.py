import json
from dataclasses import dataclass
from pathlib import Path

from app.services.rag.embedding_service import cosine_similarity, embedding_service
from app.services.rag.models import RetrievedChunk, TranscriptChunk


@dataclass(frozen=True)
class VectorRecord:
    chunk: TranscriptChunk
    embedding: list[float]


class LocalVectorStore:
    def __init__(self, storage_path: Path | None = None) -> None:
        self._storage_path = storage_path or _default_storage_path()
        self._index: dict[str, list[VectorRecord]] = {}
        self._loaded = False

    def upsert_video(self, video_id: str, chunks: list[TranscriptChunk]) -> None:
        self._ensure_loaded()
        self._index[video_id] = [
            VectorRecord(
                chunk=chunk,
                embedding=embedding_service.embed_text(chunk.text),
            )
            for chunk in chunks
        ]
        self._save()

    def has_video(self, video_id: str) -> bool:
        self._ensure_loaded()
        return bool(self._index.get(video_id))

    def delete_video(self, video_id: str) -> bool:
        self._ensure_loaded()
        if video_id not in self._index:
            return False

        del self._index[video_id]
        self._save()
        return True

    def retrieve(self, video_id: str, question: str, top_k: int = 4) -> list[RetrievedChunk]:
        self._ensure_loaded()
        records = self._index.get(video_id, [])
        if not records:
            return []

        query_embedding = embedding_service.embed_text(question)
        scored_chunks = [
            RetrievedChunk(
                chunk=record.chunk,
                score=cosine_similarity(query_embedding, record.embedding),
            )
            for record in records
        ]
        scored_chunks.sort(key=lambda item: item.score, reverse=True)
        return [item for item in scored_chunks[:top_k] if item.score > 0]

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return

        if self._storage_path.exists():
            raw_data = json.loads(self._storage_path.read_text(encoding="utf-8"))
            self._index = {
                video_id: [
                    VectorRecord(
                        chunk=TranscriptChunk(**record["chunk"]),
                        embedding=record["embedding"],
                    )
                    for record in records
                ]
                for video_id, records in raw_data.items()
            }

        self._loaded = True

    def _save(self) -> None:
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            video_id: [
                {
                    "chunk": record.chunk.__dict__,
                    "embedding": record.embedding,
                }
                for record in records
            ]
            for video_id, records in self._index.items()
        }
        self._storage_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _default_storage_path() -> Path:
    backend_root = Path(__file__).resolve().parents[3]
    return backend_root / "data" / "vector_store" / "local_vector_index.json"


vector_store = LocalVectorStore()
