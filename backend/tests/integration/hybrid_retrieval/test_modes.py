import pytest

from app.application.retrieval.hybrid_service import HybridRetrievalService, RerankerUnavailable


class _FixtureReranker:
    model_id = "fixture/reranker-v1"

    def score(self, query: str, documents: list[str], *, batch_size: int = 8) -> list[float]:
        del query, batch_size
        return [10.0 if "Gamma" in document else float(index) for index, document in enumerate(documents)]


@pytest.mark.parametrize("mode", ["lexical", "dense", "hybrid", "reranked"])
def test_modes_are_independently_queryable_with_diagnostics(hybrid_runtime, mode: str) -> None:
    service = HybridRetrievalService(
        hybrid_runtime["uow"],
        hybrid_runtime["dense"],
        reranker=_FixtureReranker(),
    )

    result = service.search(video_id="video-1", query="alpha evidence", mode=mode, limit=3)

    assert result.context
    assert all(item.chunk.video_id == "video-1" for item in result.context)
    assert result.diagnostics.mode == mode
    assert result.diagnostics.total_latency_ms >= 0
    assert result.diagnostics.candidates
    assert all(candidate.fused_rank > 0 for candidate in result.diagnostics.candidates)
    if mode in {"lexical", "hybrid", "reranked"}:
        assert any(candidate.lexical_rank is not None for candidate in result.diagnostics.candidates)
    if mode in {"dense", "hybrid", "reranked"}:
        assert any(candidate.dense_rank is not None for candidate in result.diagnostics.candidates)
    if mode == "reranked":
        assert result.diagnostics.reranker_model == "fixture/reranker-v1"
        assert any(candidate.reranker_score is not None for candidate in result.diagnostics.candidates)


def test_filters_prevent_cross_video_leakage(hybrid_runtime) -> None:
    service = HybridRetrievalService(hybrid_runtime["uow"], hybrid_runtime["dense"])

    result = service.search(video_id="video-1", query="alpha private", mode="hybrid", limit=10)

    assert result.context
    assert {item.chunk.video_id for item in result.context} == {"video-1"}
    assert all("second video" not in item.chunk.text for item in result.context)


def test_light_profile_runs_without_reranker_model(hybrid_runtime) -> None:
    service = HybridRetrievalService(hybrid_runtime["uow"], hybrid_runtime["dense"])

    result = service.search(video_id="video-1", query="semantic concept", mode="hybrid")

    assert result.context
    assert result.diagnostics.reranker_model is None
    assert result.diagnostics.reranker_latency_ms == 0
    with pytest.raises(RerankerUnavailable, match="explicitly configured"):
        service.search(video_id="video-1", query="semantic concept", mode="reranked")


def test_parent_and_neighbor_expansion_preserves_primary_identity(hybrid_runtime) -> None:
    service = HybridRetrievalService(hybrid_runtime["uow"], hybrid_runtime["dense"])

    result = service.search(video_id="video-1", query="beta", mode="lexical", limit=1, max_context_chunks=4)

    assert result.context[0].expansion_kind == "primary"
    assert all(item.primary_chunk_id == result.context[0].chunk.id for item in result.context)
    assert {item.expansion_kind for item in result.context} >= {"primary", "parent", "neighbor"}
