from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SourceCandidate:
    chunk_id: str
    raw_score: float


@dataclass(frozen=True, slots=True)
class FusedCandidate:
    chunk_id: str
    fused_score: float
    source_ranks: dict[str, int]
    source_scores: dict[str, float]


def reciprocal_rank_fusion(
    rankings: dict[str, list[SourceCandidate]],
    *,
    rank_constant: int = 60,
) -> list[FusedCandidate]:
    """Fuse incomparable retrieval scores using only source rank positions."""

    if rank_constant <= 0:
        raise ValueError("RRF rank constant must be positive.")
    ranks_by_chunk: dict[str, dict[str, int]] = {}
    scores_by_chunk: dict[str, dict[str, float]] = {}
    for source_name in sorted(rankings):
        seen: set[str] = set()
        rank = 0
        for candidate in rankings[source_name]:
            if candidate.chunk_id in seen:
                continue
            seen.add(candidate.chunk_id)
            rank += 1
            ranks_by_chunk.setdefault(candidate.chunk_id, {})[source_name] = rank
            scores_by_chunk.setdefault(candidate.chunk_id, {})[source_name] = candidate.raw_score

    fused = [
        FusedCandidate(
            chunk_id=chunk_id,
            fused_score=sum(1.0 / (rank_constant + rank) for rank in source_ranks.values()),
            source_ranks=source_ranks,
            source_scores=scores_by_chunk[chunk_id],
        )
        for chunk_id, source_ranks in ranks_by_chunk.items()
    ]
    fused.sort(
        key=lambda candidate: (
            -candidate.fused_score,
            min(candidate.source_ranks.values()),
            candidate.chunk_id,
        )
    )
    return fused
