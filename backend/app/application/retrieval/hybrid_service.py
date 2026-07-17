from __future__ import annotations

import re
from dataclasses import dataclass
from time import monotonic
from typing import Literal

from app.application.retrieval.fusion import FusedCandidate, SourceCandidate, reciprocal_rank_fusion
from app.application.retrieval.index_service import DenseIndexService
from app.application.retrieval.ports import IndexUnitOfWorkFactory, Reranker
from app.domain.entities import Chunk, ChunkType


RetrievalMode = Literal["lexical", "dense", "hybrid", "reranked"]


@dataclass(frozen=True, slots=True)
class CandidateDiagnostic:
    chunk_id: str
    lexical_rank: int | None
    dense_rank: int | None
    fused_rank: int
    fused_score: float
    reranker_score: float | None


@dataclass(frozen=True, slots=True)
class RetrievalDiagnostics:
    mode: RetrievalMode
    lexical_latency_ms: int
    dense_latency_ms: int
    fusion_latency_ms: int
    reranker_latency_ms: int
    total_latency_ms: int
    reranker_model: str | None
    candidates: tuple[CandidateDiagnostic, ...]


@dataclass(frozen=True, slots=True)
class RetrievedContext:
    chunk: Chunk
    primary_chunk_id: str
    relevance_score: float
    expansion_kind: Literal["primary", "parent", "neighbor"]


@dataclass(frozen=True, slots=True)
class HybridSearchResult:
    context: tuple[RetrievedContext, ...]
    diagnostics: RetrievalDiagnostics


class RerankerUnavailable(RuntimeError):
    pass


class HybridRetrievalService:
    def __init__(
        self,
        uow_factory: IndexUnitOfWorkFactory,
        dense_index: DenseIndexService,
        *,
        reranker: Reranker | None = None,
        candidate_count: int = 20,
        rrf_rank_constant: int = 60,
        reranker_candidate_count: int = 20,
    ) -> None:
        if candidate_count < 20:
            raise ValueError("Each retrieval source must request at least 20 candidates.")
        if reranker_candidate_count <= 0:
            raise ValueError("Reranker candidate count must be positive.")
        self._uow_factory = uow_factory
        self._dense = dense_index
        self._reranker = reranker
        self._candidate_count = candidate_count
        self._rrf_k = rrf_rank_constant
        self._reranker_candidate_count = reranker_candidate_count

    def search(
        self,
        *,
        video_id: str,
        query: str,
        mode: RetrievalMode = "hybrid",
        limit: int = 6,
        expand_context: bool = True,
        max_context_chunks: int = 12,
    ) -> HybridSearchResult:
        if limit <= 0 or max_context_chunks <= 0:
            return self._empty(mode)
        if mode not in {"lexical", "dense", "hybrid", "reranked"}:
            raise ValueError(f"Unsupported retrieval mode: {mode}")
        if mode == "reranked" and self._reranker is None:
            raise RerankerUnavailable("Reranked mode requires an explicitly configured local reranker.")

        total_started = monotonic()
        with self._uow_factory() as uow:
            active = uow.indexes.get_active(video_id)
        if active is None:
            return self._empty(mode, total_started)

        rankings: dict[str, list[SourceCandidate]] = {}
        lexical_ms = dense_ms = reranker_ms = 0
        if mode in {"lexical", "hybrid", "reranked"}:
            started = monotonic()
            with self._uow_factory() as uow:
                lexical = uow.lexical.search(
                    active.id,
                    video_id,
                    query,
                    limit=self._candidate_count,
                )
            lexical_ms = _elapsed_ms(started)
            rankings["lexical"] = [SourceCandidate(match.chunk_id, match.score) for match in lexical]

        if mode in {"dense", "hybrid", "reranked"}:
            started = monotonic()
            dense = self._dense.search(video_id, query, limit=self._candidate_count)
            dense_ms = _elapsed_ms(started)
            rankings["dense"] = [SourceCandidate(hit.chunk.id, hit.score) for hit in dense]

        fusion_started = monotonic()
        fused = reciprocal_rank_fusion(rankings, rank_constant=self._rrf_k)
        fusion_ms = _elapsed_ms(fusion_started)
        with self._uow_factory() as uow:
            candidate_chunks = uow.indexes.get_chunks(active.id, [candidate.chunk_id for candidate in fused])
        chunks_by_id = {chunk.id: chunk for chunk in candidate_chunks}
        fused = [candidate for candidate in fused if candidate.chunk_id in chunks_by_id]

        reranker_scores: dict[str, float] = {}
        ranked = fused
        if mode == "reranked" and self._reranker is not None and fused:
            rerank_pool = fused[: self._reranker_candidate_count]
            started = monotonic()
            scores = self._reranker.score(query, [chunks_by_id[item.chunk_id].text for item in rerank_pool])
            reranker_ms = _elapsed_ms(started)
            if len(scores) != len(rerank_pool):
                raise ValueError("Reranker returned an unexpected number of scores.")
            reranker_scores = {item.chunk_id: float(score) for item, score in zip(rerank_pool, scores, strict=True)}
            ranked = sorted(
                fused,
                key=lambda item: (
                    -reranker_scores.get(item.chunk_id, float("-inf")),
                    -item.fused_score,
                    item.chunk_id,
                ),
            )

        primary = _deduplicate(ranked, chunks_by_id, limit)
        context = self._expand(
            active.id,
            primary,
            chunks_by_id,
            enabled=expand_context,
            max_chunks=max_context_chunks,
        )
        fused_rank = {candidate.chunk_id: rank for rank, candidate in enumerate(fused, start=1)}
        diagnostics = tuple(
            CandidateDiagnostic(
                chunk_id=candidate.chunk_id,
                lexical_rank=candidate.source_ranks.get("lexical"),
                dense_rank=candidate.source_ranks.get("dense"),
                fused_rank=fused_rank[candidate.chunk_id],
                fused_score=round(candidate.fused_score, 8),
                reranker_score=reranker_scores.get(candidate.chunk_id),
            )
            for candidate in ranked
        )
        return HybridSearchResult(
            context=tuple(context),
            diagnostics=RetrievalDiagnostics(
                mode=mode,
                lexical_latency_ms=lexical_ms,
                dense_latency_ms=dense_ms,
                fusion_latency_ms=fusion_ms,
                reranker_latency_ms=reranker_ms,
                total_latency_ms=_elapsed_ms(total_started),
                reranker_model=self._reranker.model_id if mode == "reranked" and self._reranker else None,
                candidates=diagnostics,
            ),
        )

    def _expand(
        self,
        index_version_id: str,
        primary: list[FusedCandidate],
        primary_chunks: dict[str, Chunk],
        *,
        enabled: bool,
        max_chunks: int,
    ) -> list[RetrievedContext]:
        with self._uow_factory() as uow:
            all_chunks = uow.indexes.list_chunks(index_version_id)
        by_id = {chunk.id: chunk for chunk in all_chunks}
        children_by_sequence = {
            chunk.sequence_number: chunk for chunk in all_chunks if chunk.chunk_type is ChunkType.CHILD
        }
        context: list[RetrievedContext] = []
        seen: set[str] = set()
        for candidate in primary:
            chunk = primary_chunks[candidate.chunk_id]
            _append_context(context, seen, chunk, candidate, "primary", max_chunks)
            if not enabled:
                continue
            if chunk.parent_chunk_id and chunk.parent_chunk_id in by_id:
                _append_context(context, seen, by_id[chunk.parent_chunk_id], candidate, "parent", max_chunks)
            for sequence in (chunk.sequence_number - 1, chunk.sequence_number + 1):
                neighbor = children_by_sequence.get(sequence)
                if neighbor is not None:
                    _append_context(context, seen, neighbor, candidate, "neighbor", max_chunks)
        return context

    def _empty(self, mode: RetrievalMode, started: float | None = None) -> HybridSearchResult:
        return HybridSearchResult(
            context=(),
            diagnostics=RetrievalDiagnostics(
                mode=mode,
                lexical_latency_ms=0,
                dense_latency_ms=0,
                fusion_latency_ms=0,
                reranker_latency_ms=0,
                total_latency_ms=_elapsed_ms(started) if started is not None else 0,
                reranker_model=None,
                candidates=(),
            ),
        )


_WORD = re.compile(r"[^\W_]+", re.UNICODE)


def _deduplicate(
    ranked: list[FusedCandidate],
    chunks_by_id: dict[str, Chunk],
    limit: int,
) -> list[FusedCandidate]:
    selected: list[FusedCandidate] = []
    selected_terms: list[set[str]] = []
    for candidate in ranked:
        terms = set(_WORD.findall(chunks_by_id[candidate.chunk_id].text.casefold()))
        if any(_jaccard(terms, existing) >= 0.85 for existing in selected_terms):
            continue
        selected.append(candidate)
        selected_terms.append(terms)
        if len(selected) >= limit:
            break
    return selected


def _jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def _append_context(
    context: list[RetrievedContext],
    seen: set[str],
    chunk: Chunk,
    candidate: FusedCandidate,
    kind: Literal["primary", "parent", "neighbor"],
    max_chunks: int,
) -> None:
    if len(context) >= max_chunks or chunk.id in seen:
        return
    seen.add(chunk.id)
    context.append(RetrievedContext(chunk, candidate.chunk_id, candidate.fused_score, kind))


def _elapsed_ms(started: float) -> int:
    return max(0, round((monotonic() - started) * 1000))
