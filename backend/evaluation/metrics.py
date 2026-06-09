from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievalMetrics:
    precision_at_k: float
    recall_at_k: float
    mrr: float


def compute_retrieval_metrics(
    *,
    retrieved_chunk_ids: list[str],
    expected_chunk_ids: list[str],
) -> RetrievalMetrics:
    expected = set(expected_chunk_ids)
    if not expected:
        return RetrievalMetrics(precision_at_k=0.0, recall_at_k=0.0, mrr=0.0)

    retrieved = retrieved_chunk_ids
    relevant_hits = [chunk_id for chunk_id in retrieved if chunk_id in expected]
    precision = len(relevant_hits) / max(len(retrieved), 1)
    recall = len(set(relevant_hits)) / len(expected)
    reciprocal_rank = _reciprocal_rank(retrieved, expected)

    return RetrievalMetrics(
        precision_at_k=round(precision, 4),
        recall_at_k=round(recall, 4),
        mrr=round(reciprocal_rank, 4),
    )


def average_metrics(metrics: list[RetrievalMetrics]) -> RetrievalMetrics:
    if not metrics:
        return RetrievalMetrics(precision_at_k=0.0, recall_at_k=0.0, mrr=0.0)

    return RetrievalMetrics(
        precision_at_k=round(
            sum(item.precision_at_k for item in metrics) / len(metrics),
            4,
        ),
        recall_at_k=round(
            sum(item.recall_at_k for item in metrics) / len(metrics),
            4,
        ),
        mrr=round(sum(item.mrr for item in metrics) / len(metrics), 4),
    )


def _reciprocal_rank(retrieved_chunk_ids: list[str], expected_chunk_ids: set[str]) -> float:
    for index, chunk_id in enumerate(retrieved_chunk_ids, start=1):
        if chunk_id in expected_chunk_ids:
            return 1 / index

    return 0.0
