# TASK-011: Establish the Retrieval Release Gate

Status: verified

Depends on: TASK-006, TASK-008

## Objective

Create a reviewed bilingual dataset and reproducible report that selects chunking, embedding, and retrieval defaults based on evidence.

## Required reading

- `docs/06-quality/quality-gates.md`
- `docs/03-specifications/retrieval-spec.md`
- `docs/03-specifications/chunking-spec.md`

## In scope

- Versioned dataset schema and curation guide.
- Representative Vietnamese/English and cross-language cases.
- Fixed-word versus hierarchical chunking comparison.
- Qwen3 Embedding versus BGE-M3 comparison.
- Lexical, dense, RRF, and reranked comparison.
- Machine-readable and Markdown reports with hardware/config fingerprints.

## Non-goals

- Fabricated thresholds
- Using only synthetic LLM-generated labels without review

## Acceptance criteria

- [x] Every question has reviewed relevant segment/chunk evidence or an unanswerable label.
- [x] Report contains all specified quality and cost metrics.
- [x] Runs are reproducible from committed config and dataset version.
- [x] Default selection is recorded in a follow-up ADR with tradeoffs.

## Verification

`uv run --project backend python -m app.modules.evaluation.run --config backend/evaluation/local-v1.yaml`

## Commit

`test(retrieval): establish bilingual evaluation gate`
