---
id: ADR-006
status: accepted
date: 2026-07-17
---

# ADR-006: Evidence-Selected Local Retrieval Defaults

## Decision

For the measured Local V1 standard profile, use 140-word chunks with 30-word overlap, `BAAI/bge-m3` normalized embeddings, and lexical+dense Reciprocal Rank Fusion. Keep `qwen3-embedding:0.6b` through Ollama as the service-light alternative. Do not enable the BGE cross-encoder reranker by default.

## Evidence

Dataset `local-v1-bilingual-retrieval@1.0.0` contains twelve reviewed Vietnamese, English, cross-language, keyword, paraphrase, multi-evidence, and unanswerable cases. The reproducible report is committed under `backend/evaluation/reports/`.

The selected variant reached Recall@3 `1.0000`, MRR `1.0000`, nDCG@3 `0.9933`, and citation accuracy `0.3687`, with p95 query latency `191.4174 ms` on the recorded machine. Reranking improved nDCG by `0.0067` but increased p95 latency to `4870.3339 ms`, so the post-baseline `0.01` quality-equivalence rule selects RRF. The hierarchical candidate reached better timestamp granularity but only `0.5833` Recall@3 on this dataset and is not the release default.

## Consequences

- ADR-005 remains the design and implementation record for hierarchical chunking, but its previous default selection is superseded by this measured Local V1 decision.
- Hierarchical chunks remain available as the primary challenger and SHOULD be reevaluated when the reviewed dataset grows.
- Existing explicit user embedding settings are not silently overwritten. Profiles and new indexes adopt the selected defaults; changing an embedding model requires a rebuild.
- Unanswerable false-positive rate remains visible rather than hidden by a fabricated retrieval threshold; grounded generation owns abstention.
