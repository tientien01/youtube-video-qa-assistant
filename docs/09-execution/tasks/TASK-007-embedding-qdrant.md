# TASK-007: Add Multilingual Embedding and Qdrant Local Index

Status: planned

Depends on: TASK-006

## Objective

Create a rebuildable dense index with provider-independent embedding and vector ports.

## Required reading

- `docs/03-specifications/retrieval-spec.md`
- `docs/08-decisions/ADR-003-sqlite-qdrant.md`

## In scope

- Separate query/document embedding interface.
- Ollama Qwen3 Embedding 0.6B adapter and deterministic fake adapter.
- Qdrant local adapter keyed by index version.
- Batch embedding, dimension discovery, health checks, rebuild, and cleanup.
- Index fingerprint persistence.

## Non-goals

- Production Qdrant server deployment
- Selecting a permanent winning embedding without evaluation
- Reranking

## Acceptance criteria

- [ ] Tests run without Ollama using the fake adapter.
- [ ] Index/query model mismatch is rejected.
- [ ] Rebuild from SQLite produces a queryable active version.
- [ ] Failed rebuild preserves the prior active index.
- [ ] Qdrant is never required to reconstruct canonical transcript data.

## Verification

`uv run --project backend pytest backend/tests/unit/embeddings backend/tests/integration/qdrant_index`

## Commit

`feat(retrieval): add multilingual Qdrant index`
