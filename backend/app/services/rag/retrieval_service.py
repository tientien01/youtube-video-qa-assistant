from typing import Literal

from app.services.rag.local_store import VideoNotIndexedError, rag_store
from app.services.rag.models import RetrievedChunk
from app.services.rag.vector_store import vector_store


RetrievalMode = Literal["bm25", "embedding", "hybrid"]


def retrieve_chunks(
    *,
    video_id: str,
    question: str,
    mode: RetrievalMode = "hybrid",
    top_k: int = 4,
) -> list[RetrievedChunk]:
    if mode == "bm25":
        return rag_store.retrieve(video_id=video_id, question=question, top_k=top_k)

    _ensure_vector_index(video_id)

    if mode == "embedding":
        return vector_store.retrieve(video_id=video_id, question=question, top_k=top_k)

    if mode == "hybrid":
        return _retrieve_hybrid(video_id=video_id, question=question, top_k=top_k)

    raise ValueError(f"Unsupported retrieval mode: {mode}")


def _retrieve_hybrid(video_id: str, question: str, top_k: int) -> list[RetrievedChunk]:
    bm25_results = rag_store.retrieve(video_id=video_id, question=question, top_k=top_k * 2)
    embedding_results = vector_store.retrieve(video_id=video_id, question=question, top_k=top_k * 2)

    if not bm25_results and not embedding_results:
        return []

    bm25_scores = _normalize_scores(bm25_results)
    embedding_scores = _normalize_scores(embedding_results)
    chunk_by_id = {
        result.chunk.chunk_id: result.chunk
        for result in [*bm25_results, *embedding_results]
    }

    scored_chunks = [
        RetrievedChunk(
            chunk=chunk,
            score=round(
                (0.45 * bm25_scores.get(chunk_id, 0.0))
                + (0.55 * embedding_scores.get(chunk_id, 0.0)),
                6,
            ),
        )
        for chunk_id, chunk in chunk_by_id.items()
    ]
    scored_chunks.sort(key=lambda item: item.score, reverse=True)
    return [item for item in scored_chunks[:top_k] if item.score > 0]


def _ensure_vector_index(video_id: str) -> None:
    if vector_store.has_video(video_id):
        return

    chunks = rag_store.get_video_chunks(video_id)
    if not chunks:
        raise VideoNotIndexedError("Video has not been indexed yet.")

    vector_store.upsert_video(video_id, chunks)


def _normalize_scores(results: list[RetrievedChunk]) -> dict[str, float]:
    if not results:
        return {}

    max_score = max(result.score for result in results)
    if max_score <= 0:
        return {}

    return {
        result.chunk.chunk_id: round(result.score / max_score, 6)
        for result in results
        if result.score > 0
    }
