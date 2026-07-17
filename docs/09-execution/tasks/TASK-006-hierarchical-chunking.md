# TASK-006: Implement Hierarchical Timestamp-Aware Chunking

Status: verified

Depends on: TASK-005

## Objective

Replace fixed word chunks with deterministic library-assisted child/parent chunks while retaining the old chunker as an evaluation control.

## Required reading

- `docs/03-specifications/chunking-spec.md`
- `docs/08-decisions/ADR-005-library-assisted-chunking.md`

## In scope

- `SentenceSegmenter` and `TokenCounter` ports.
- Stanza Vietnamese/English adapter with explicit model setup.
- Model-aware tokenizer adapter.
- Character/span mapping back to source segments.
- Child/parent packing, timing-gap boundaries, whole-unit overlap, and poor-punctuation fallback.
- Versioned chunker configuration and deterministic IDs.

## Non-goals

- Making semantic boundaries the default
- Retrieval changes
- Downloading models during an ingest request

## Acceptance criteria

- [x] Every chunk maps to valid ordered source segment IDs and exact derived timestamps.
- [x] Vietnamese and English fixtures preserve sentence boundaries better than the fixed-word baseline cases.
- [x] Missing punctuation and oversized segments respect hard limits through documented fallback.
- [x] Same input/config produces byte-equivalent chunk records and IDs.
- [x] Stanza unavailability produces an actionable setup error or configured deterministic fallback.

## Verification

`uv run --project backend pytest backend/tests/unit/chunking backend/tests/integration/chunk_pipeline`

## Commit

`feat(chunking): add hierarchical timestamp-aware chunker`
