from typing import Literal

from app.application.retrieval.fusion import SourceCandidate, reciprocal_rank_fusion
from app.core.config import get_settings
from app.application.legacy.rag.local_store import VideoNotIndexedError, rag_store
from app.application.legacy.rag.models import RetrievedChunk
from app.application.legacy.rag.reranker import reranker


RetrievalMode = Literal["bm25", "embedding", "hybrid"]
vector_store = None


def configure_retrieval_runtime(*, configured_vector_store) -> None:
    global vector_store
    vector_store = configured_vector_store


def retrieve_chunks(
    *,
    video_id: str,
    question: str,
    mode: RetrievalMode = "hybrid",
    top_k: int = 4,
) -> list[RetrievedChunk]:
    if vector_store is None:
        raise RuntimeError("Vector store runtime is not configured.")
    candidate_top_k = _candidate_top_k(top_k)

    if mode == "bm25":
        candidates = rag_store.retrieve(video_id=video_id, question=question, top_k=candidate_top_k)
        return _maybe_rerank(question=question, candidates=candidates, top_k=top_k)

    _ensure_vector_index(video_id)

    if mode == "embedding":
        candidates = vector_store.retrieve(video_id=video_id, question=question, top_k=candidate_top_k)
        return _maybe_rerank(question=question, candidates=candidates, top_k=top_k)

    if mode == "hybrid":
        candidates = _retrieve_hybrid(video_id=video_id, question=question, top_k=candidate_top_k)
        return _maybe_rerank(question=question, candidates=candidates, top_k=top_k)

    raise ValueError(f"Unsupported retrieval mode: {mode}")


def _retrieve_hybrid(video_id: str, question: str, top_k: int) -> list[RetrievedChunk]:
    bm25_results = rag_store.retrieve(video_id=video_id, question=question, top_k=top_k * 2)
    embedding_results = vector_store.retrieve(video_id=video_id, question=question, top_k=top_k * 2)

    if not bm25_results and not embedding_results:
        return []

    chunk_by_id = {
        result.chunk.chunk_id: result.chunk
        for result in [*bm25_results, *embedding_results]
    }
    fused = reciprocal_rank_fusion(
        {
            "lexical": [SourceCandidate(item.chunk.chunk_id, item.score) for item in bm25_results],
            "dense": [SourceCandidate(item.chunk.chunk_id, item.score) for item in embedding_results],
        }
    )
    return [
        RetrievedChunk(
            chunk=chunk_by_id[candidate.chunk_id],
            score=round(candidate.fused_score, 8),
        )
        for candidate in fused[:top_k]
    ]


def _candidate_top_k(top_k: int) -> int:
    settings = get_settings()
    if not settings.reranker_enabled:
        return top_k

    return max(top_k, settings.rerank_top_k)


def _maybe_rerank(
    *,
    question: str,
    candidates: list[RetrievedChunk],
    top_k: int,
) -> list[RetrievedChunk]:
    settings = get_settings()
    if not settings.reranker_enabled:
        return candidates[:top_k]

    return reranker.rerank(question=question, candidates=candidates, top_k=top_k)


def _ensure_vector_index(video_id: str) -> None:
    if vector_store.has_video(video_id):
        return

    chunks = rag_store.get_video_chunks(video_id)
    if not chunks:
        raise VideoNotIndexedError("Video has not been indexed yet.")

    vector_store.upsert_video(video_id, chunks)
