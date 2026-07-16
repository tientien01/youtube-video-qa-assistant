---
id: ADR-004
status: accepted
date: 2026-07-16
---

# ADR-004: Hybrid Retrieval with RRF and Reranking

## Decision

Keep a lexical baseline, add multilingual dense retrieval, fuse rankings with Reciprocal Rank Fusion, then optionally rerank with a multilingual cross-encoder.

## Rationale

Lexical search preserves exact-term behavior while dense retrieval handles paraphrase and cross-language queries. Rank fusion avoids treating incomparable score scales as equivalent.

## Consequences

Every advanced stage must be independently disableable and evaluated against the baseline. The current weighted normalized-score fusion is transitional.
