---
id: ADR-005
status: accepted
date: 2026-07-16
---

# ADR-005: Library-Assisted, Project-Owned Video Chunking

## Decision

Use Stanza for Vietnamese/English sentence segmentation and a model-aware tokenizer for token counts. Keep timestamp mapping, hierarchy, overlap, and packing in project code.

## Rationale

Linguistic libraries improve sentence boundaries, while generic RAG splitters do not own video-specific timestamp provenance and lifecycle invariants.

## Consequences

Stanza models are explicit local assets. A fallback handles punctuation-poor captions. Semantic boundary detection remains an evaluated strategy, not the default.
