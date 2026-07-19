import json
import math
from collections import Counter
from pathlib import Path

from app.core.paths import DATA_DIR
from app.application.legacy.rag.models import RetrievedChunk, TranscriptChunk
from app.application.legacy.rag.text_processing import tokenize


class VideoNotIndexedError(Exception):
    """Raised when a question targets a video that has not been indexed."""


class LocalRagStore:
    def __init__(self, storage_path: Path | None = None) -> None:
        self._storage_path = storage_path or _default_storage_path()
        self._index: dict[str, list[TranscriptChunk]] = {}
        self._loaded = False

    def upsert_video(self, video_id: str, chunks: list[TranscriptChunk]) -> None:
        self._ensure_loaded()
        self._index[video_id] = chunks
        self._save()

    def has_video(self, video_id: str) -> bool:
        self._ensure_loaded()
        return bool(self._index.get(video_id))

    def get_video_chunks(self, video_id: str) -> list[TranscriptChunk]:
        self._ensure_loaded()
        return self._index.get(video_id, [])

    def get_video_chunk_count(self, video_id: str) -> int:
        return len(self.get_video_chunks(video_id))

    def delete_video(self, video_id: str) -> bool:
        self._ensure_loaded()
        if video_id not in self._index:
            return False

        del self._index[video_id]
        self._save()
        return True

    def retrieve(self, video_id: str, question: str, top_k: int = 4) -> list[RetrievedChunk]:
        self._ensure_loaded()
        chunks = self._index.get(video_id)
        if not chunks:
            raise VideoNotIndexedError("Video has not been indexed yet.")

        query_terms = tokenize(question)
        if not query_terms:
            return []

        document_tokens = [tokenize(chunk.text) for chunk in chunks]
        document_frequency = Counter(token for tokens in document_tokens for token in set(tokens))
        average_length = sum(len(tokens) for tokens in document_tokens) / max(len(document_tokens), 1)

        scored_chunks = [
            RetrievedChunk(
                chunk=chunk,
                score=_bm25_score(
                    query_terms=query_terms,
                    document_terms=document_tokens[index],
                    document_frequency=document_frequency,
                    document_count=len(chunks),
                    average_length=average_length,
                ),
            )
            for index, chunk in enumerate(chunks)
        ]

        scored_chunks.sort(key=lambda item: item.score, reverse=True)
        return [item for item in scored_chunks[:top_k] if item.score > 0]

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return

        if self._storage_path.exists():
            raw_data = json.loads(self._storage_path.read_text(encoding="utf-8"))
            self._index = {
                video_id: [TranscriptChunk(**chunk_data) for chunk_data in chunks]
                for video_id, chunks in raw_data.items()
            }

        self._loaded = True

    def _save(self) -> None:
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {video_id: [chunk.__dict__ for chunk in chunks] for video_id, chunks in self._index.items()}
        self._storage_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _default_storage_path() -> Path:
    return DATA_DIR / "vector_store" / "local_rag_index.json"


def _bm25_score(
    query_terms: list[str],
    document_terms: list[str],
    document_frequency: Counter,
    document_count: int,
    average_length: float,
) -> float:
    term_counts = Counter(document_terms)
    document_length = len(document_terms)
    if document_length == 0:
        return 0.0

    k1 = 1.5
    b = 0.75
    score = 0.0

    for term in set(query_terms):
        frequency = term_counts.get(term, 0)
        if frequency == 0:
            continue

        idf = math.log(1 + (document_count - document_frequency[term] + 0.5) / (document_frequency[term] + 0.5))
        denominator = frequency + k1 * (1 - b + b * document_length / max(average_length, 1))
        score += idf * (frequency * (k1 + 1)) / denominator

    return round(score, 6)


rag_store = LocalRagStore()
