---
id: SPEC-CHUNK-001
document_status: approved
implementation_status: verified
normative: true
last_verified: 2026-07-17
related_adrs: [ADR-005]
---

# Chunking Specification

## Chosen strategy

Local V1 MUST use library-assisted, timestamp-aware hierarchical sentence chunking. A library owns linguistic sentence segmentation; project code owns timestamp mapping, packing, overlap, hierarchy, and invariants.

## Components

- Default `SentenceSegmenter`: Stanza `tokenize` processor with `vi` and `en` models.
- `TokenCounter`: tokenizer associated with the configured embedding model.
- `ChunkPacker`: project-owned deterministic packing algorithm.
- Optional `SemanticBoundaryStrategy`: experiment only until evaluation approves it.

Stanza models MUST be installed/downloaded explicitly during setup, never unexpectedly during an ingest request. The segmenter pipeline MUST be cached per process.

## Data flow

```text
canonical transcript segments
-> sentence segmentation with character-span mapping
-> sentence records linked to source segments
-> child chunk packing
-> parent window packing
-> overlap and timing validation
```

## Initial defaults

```yaml
strategy: hierarchical_sentence
child_target_tokens: 320
child_max_tokens: 420
child_overlap_tokens: 48
child_max_duration_seconds: 75
parent_target_tokens: 1000
parent_max_tokens: 1400
parent_max_duration_seconds: 300
timing_gap_boundary_seconds: 2.5
semantic_refinement: false
```

These are versioned starting values. Evaluation MAY change them through an ADR or documented experiment.

## Invariants

- Every chunk MUST contain text, ordered source segment IDs, `start_ms`, and `end_ms`.
- Timestamps MUST derive from the first and last source segments, never word-count interpolation.
- Overlap MUST reuse whole sentences or segments when possible and preserve punctuation.
- A child MUST NOT exceed maximum tokens unless one indivisible source unit exceeds it; that exception MUST be recorded.
- Packing SHOULD break at sentence, timing gap, topic boundary, then segment, in that order.
- Parent and child IDs MUST be deterministic for the same fingerprint.
- Retrieval targets child chunks; context expansion MAY add parent or neighboring chunks.

## Poor-caption fallback

If punctuation-based sentence segmentation is unreliable:

1. split on source segment and timing gaps;
2. recursively split an oversized segment by punctuation and whitespace;
3. preserve a span-to-source mapping;
4. enforce token and duration limits.

## Baseline and evaluation

The current fixed segment/word chunker MUST remain available temporarily as the evaluation control. Semantic boundary refinement MUST NOT become default unless it improves retrieval/citation metrics without unacceptable indexing cost.
