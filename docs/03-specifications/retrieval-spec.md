---
id: SPEC-RETRIEVAL-001
document_status: approved
implementation_status: planned
normative: true
last_verified: 2026-07-16
related_adrs: [ADR-003, ADR-004]
---

# Embedding and Retrieval Specification

## Target pipeline

```text
query
  +-- SQLite FTS5 lexical candidates
  +-- Qdrant dense candidates
-> Reciprocal Rank Fusion
-> multilingual cross-encoder reranking
-> redundancy control
-> parent/neighbor expansion
-> context budget
```

## Embeddings

- Default local candidate: `qwen3-embedding:0.6b` through an Ollama adapter.
- Required benchmark challenger: `BAAI/bge-m3`.
- Hashing embeddings MAY be used only for deterministic tests and migration comparison.
- Document and query embedding methods MUST be separate even if an adapter shares implementation.
- Index and query MUST use the same model identity, revision, dimension, normalization, and instruction policy.
- Embeddings MUST be batched and the discovered dimension persisted in `IndexVersion`.

No embedding model becomes permanent default until the bilingual project evaluation compares quality, latency, memory, and index time.

## Candidate retrieval

- FTS5 provides the required lexical baseline.
- Qdrant local provides dense retrieval and MUST be treated as derived storage.
- Each source initially returns at least 20 candidates where available.
- Filter by video ID and active index version before fusion.

## Fusion

Local V1 MUST use Reciprocal Rank Fusion instead of directly adding normalized BM25 and cosine scores. Fusion configuration and source ranks MUST be visible in retrieval diagnostics.

## Reranking

- Standard profile uses `BAAI/bge-reranker-v2-m3` on the fused top 15-30 candidates.
- Light profile MAY disable reranking.
- The reranker MUST implement a provider-independent interface.
- Final context normally contains 5-8 unique evidence chunks before expansion.

## Context assembly

- Prefer high relevance while preventing adjacent duplicates from consuming the budget.
- Expand a selected child with its parent or immediate neighbors only when budget allows.
- Preserve citation identity through expansion.
- Never provide a chunk from another video or inactive index version.

## Evaluation gate

Compare lexical, dense, hybrid, and hybrid+reranker variants using Recall@K, Hit Rate@K, MRR, nDCG@K, citation accuracy, latency, memory, and indexing time. The dataset MUST include Vietnamese/English same-language, cross-language, keyword, paraphrase, multi-evidence, and unanswerable queries.
