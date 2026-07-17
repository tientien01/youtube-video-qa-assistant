from app.application.retrieval.fusion import SourceCandidate, reciprocal_rank_fusion


def test_rrf_uses_ranks_instead_of_raw_score_addition() -> None:
    rankings = {
        "lexical": [SourceCandidate("shared", 0.0001), SourceCandidate("lexical-only", 999_999.0)],
        "dense": [SourceCandidate("shared", -500.0), SourceCandidate("dense-only", 1.0)],
    }

    fused = reciprocal_rank_fusion(rankings, rank_constant=60)

    assert [candidate.chunk_id for candidate in fused] == ["shared", "dense-only", "lexical-only"]
    assert fused[0].source_ranks == {"dense": 1, "lexical": 1}
    assert fused[0].source_scores == {"dense": -500.0, "lexical": 0.0001}


def test_rrf_deduplicates_source_results_and_breaks_ties_by_chunk_id() -> None:
    rankings = {
        "lexical": [
            SourceCandidate("b", 3.0),
            SourceCandidate("b", 2.0),
            SourceCandidate("a", 1.0),
        ]
    }

    fused = reciprocal_rank_fusion(rankings)

    assert [candidate.chunk_id for candidate in fused] == ["b", "a"]
    assert [candidate.source_ranks["lexical"] for candidate in fused] == [1, 2]


def test_rrf_rejects_invalid_rank_constant() -> None:
    try:
        reciprocal_rank_fusion({}, rank_constant=0)
    except ValueError as error:
        assert "positive" in str(error)
    else:
        raise AssertionError("Expected invalid RRF constant to fail.")
