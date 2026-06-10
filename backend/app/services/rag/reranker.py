from app.services.rag.models import RetrievedChunk
from app.services.rag.text_processing import tokenize


class LexicalReranker:
    def rerank(
        self,
        *,
        question: str,
        candidates: list[RetrievedChunk],
        top_k: int,
    ) -> list[RetrievedChunk]:
        if top_k <= 0 or not candidates:
            return []

        query_terms = set(tokenize(question))
        if not query_terms:
            return candidates[:top_k]

        max_original_score = max(candidate.score for candidate in candidates)
        scored_candidates = [
            RetrievedChunk(
                chunk=candidate.chunk,
                score=round(
                    (0.65 * _safe_normalize(candidate.score, max_original_score))
                    + (0.35 * _token_overlap(query_terms, candidate.chunk.text)),
                    6,
                ),
            )
            for candidate in candidates
        ]
        scored_candidates.sort(key=lambda item: item.score, reverse=True)
        return [item for item in scored_candidates[:top_k] if item.score > 0]


def _safe_normalize(score: float, max_score: float) -> float:
    if max_score <= 0:
        return 0.0

    return score / max_score


def _token_overlap(query_terms: set[str], text: str) -> float:
    chunk_terms = set(tokenize(text))
    if not chunk_terms:
        return 0.0

    return len(query_terms & chunk_terms) / len(query_terms)


reranker = LexicalReranker()
