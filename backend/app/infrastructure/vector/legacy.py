"""Deprecated JSON/Chroma adapters for the pre-canonical RAG compatibility path."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.paths import VECTOR_STORE_DIR
from app.infrastructure.embeddings.legacy import EmbeddingService, cosine_similarity, embedding_service
from app.application.legacy.rag.models import RetrievedChunk, TranscriptChunk


@dataclass(frozen=True)
class VectorRecord:
    chunk: TranscriptChunk
    embedding: list[float]


class LocalVectorStore:
    def __init__(
        self,
        storage_path: Path | None = None,
        text_embedding_service: EmbeddingService | None = None,
    ) -> None:
        self._storage_path = storage_path or _default_storage_path()
        self._embedding_service = text_embedding_service or embedding_service
        self._index: dict[str, list[VectorRecord]] = {}
        self._loaded = False

    def upsert_video(self, video_id: str, chunks: list[TranscriptChunk]) -> None:
        self._ensure_loaded()
        embeddings = self._embedding_service.embed_texts([chunk.text for chunk in chunks])
        self._index[video_id] = [
            VectorRecord(chunk=chunk, embedding=embeddings[index]) for index, chunk in enumerate(chunks)
        ]
        self._save()

    def health_check(self) -> bool:
        try:
            self._ensure_loaded()
        except (OSError, TypeError, ValueError):
            return False
        return True

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
        query_embedding = self._embedding_service.embed_text(question)
        scored_chunks = [
            RetrievedChunk(chunk=record.chunk, score=cosine_similarity(query_embedding, record.embedding))
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
                    VectorRecord(chunk=TranscriptChunk(**record["chunk"]), embedding=record["embedding"])
                    for record in records
                ]
                for video_id, records in raw_data.items()
            }
        self._loaded = True

    def _save(self) -> None:
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            video_id: [{"chunk": record.chunk.__dict__, "embedding": record.embedding} for record in records]
            for video_id, records in self._index.items()
        }
        self._storage_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


class ChromaVectorStore:
    def __init__(
        self,
        persist_directory: Path | None = None,
        collection_name: str = "youtube_video_chunks",
        text_embedding_service: EmbeddingService | None = None,
    ) -> None:
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings
        except ImportError as error:
            raise RuntimeError("chromadb is required when VECTOR_STORE_PROVIDER=chroma.") from error
        settings = get_settings()
        self._persist_directory = persist_directory or settings.chroma_persist_dir
        self._embedding_service = text_embedding_service or embedding_service
        self._persist_directory.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=str(self._persist_directory),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection: Any = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert_video(self, video_id: str, chunks: list[TranscriptChunk]) -> None:
        self.delete_video(video_id)
        if not chunks:
            return
        embeddings = self._embedding_service.embed_texts([chunk.text for chunk in chunks])
        self._collection.upsert(
            ids=[chunk.chunk_id for chunk in chunks],
            documents=[chunk.text for chunk in chunks],
            embeddings=embeddings,
            metadatas=[
                {
                    "video_id": chunk.video_id,
                    "start_seconds": chunk.start_seconds,
                    "end_seconds": chunk.end_seconds,
                }
                for chunk in chunks
            ],
        )

    def health_check(self) -> bool:
        try:
            self._collection.count()
        except Exception:
            return False
        return True

    def has_video(self, video_id: str) -> bool:
        result = self._collection.get(where={"video_id": video_id}, limit=1, include=["metadatas"])
        return bool(result.get("ids"))

    def delete_video(self, video_id: str) -> bool:
        existing = self._collection.get(where={"video_id": video_id}, include=["metadatas"])
        ids = existing.get("ids", [])
        if not ids:
            return False
        self._collection.delete(ids=ids)
        return True

    def retrieve(self, video_id: str, question: str, top_k: int = 4) -> list[RetrievedChunk]:
        if top_k <= 0:
            return []
        query_embedding = self._embedding_service.embed_text(question)
        result = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where={"video_id": video_id},
            include=["documents", "metadatas", "distances"],
        )
        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        retrieved_chunks = []
        for index, chunk_id in enumerate(ids):
            metadata = metadatas[index]
            score = max(0.0, round(1.0 - float(distances[index]), 6))
            if score <= 0:
                continue
            retrieved_chunks.append(
                RetrievedChunk(
                    chunk=TranscriptChunk(
                        chunk_id=chunk_id,
                        video_id=str(metadata["video_id"]),
                        text=documents[index],
                        start_seconds=float(metadata["start_seconds"]),
                        end_seconds=float(metadata["end_seconds"]),
                    ),
                    score=score,
                )
            )
        return retrieved_chunks


def _default_storage_path() -> Path:
    return VECTOR_STORE_DIR / "local_vector_index.json"


def build_vector_store(provider: str | None = None):
    settings = get_settings()
    selected_provider = (provider or settings.vector_store_provider).lower()
    if selected_provider in {"local_json", "local"}:
        return LocalVectorStore(text_embedding_service=embedding_service)
    if selected_provider == "chroma":
        return ChromaVectorStore(
            persist_directory=settings.chroma_persist_dir,
            text_embedding_service=embedding_service,
        )
    raise ValueError(f"Unsupported vector store provider: {selected_provider}")


vector_store = build_vector_store()
