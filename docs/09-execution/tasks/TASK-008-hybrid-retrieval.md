# TASK-008: Implement FTS5, RRF, and Multilingual Reranking

Status: planned

Depends on: TASK-007

## Objective

Replace transitional score weighting with inspectable hybrid retrieval and optional cross-encoder reranking.

## Required reading

- `docs/03-specifications/retrieval-spec.md`
- `docs/08-decisions/ADR-004-hybrid-retrieval.md`

## In scope

- SQLite FTS5 candidate retrieval.
- Dense candidate retrieval from active Qdrant version.
- Reciprocal Rank Fusion with deterministic tie handling.
- `BAAI/bge-reranker-v2-m3` adapter, optional in light profile.
- Deduplication, parent/neighbor expansion, and retrieval diagnostics.

## Non-goals

- Declaring quality success without TASK-011
- LLM answer changes

## Acceptance criteria

- [ ] Unit fixtures prove RRF using ranks rather than raw score addition.
- [ ] Filters prevent cross-video/version leakage.
- [ ] Lexical, dense, hybrid, and reranked modes remain independently testable.
- [ ] Light profile works without the reranker model.
- [ ] Diagnostics expose source rank, fused rank, reranker score, and latency.

## Verification

`uv run --project backend pytest backend/tests/unit/retrieval backend/tests/integration/hybrid_retrieval`

## Commit

`feat(retrieval): add RRF hybrid search and reranking`
