---
id: DOMAIN-001
document_status: approved
implementation_status: partial
normative: true
last_verified: 2026-07-16
---

# Domain Model and Lifecycles

## Core entities

| Entity | Responsibility |
|---|---|
| `Video` | Stable YouTube identity and user-visible metadata |
| `IngestJob` | Persistent execution state, attempts, errors, and timings |
| `Transcript` | Selected transcript version and provenance |
| `TranscriptSegment` | Canonical text with exact start/end time |
| `Chunk` | Derived retrieval unit linked to source segments and optional parent |
| `IndexVersion` | Fingerprint of transcript, chunker, embedding, and vector index |
| `ChatSession` | Conversation scoped to a video or future collection |
| `Citation` | Reference to source chunk/segments and timestamp range |
| `GeneratedArtifact` | Summary, notes, quiz, or other derived output |

## Ingest job lifecycle

```text
pending -> fetching_metadata -> fetching_transcript -> normalizing
-> validating -> chunking -> embedding -> committing -> ready
```

Any active state MAY transition to `retry_wait`, `failed`, or `cancelled`. `retry_wait` MAY resume only at a safe stage. A terminal job MUST retain a machine-readable stage, error code, retryability flag, attempts, and diagnostics.

## Video readiness

A video is `ready` only when its canonical transcript, segments, chunks, and active index version are consistent. Generated artifacts are not required for readiness.

## Provenance invariants

- Every transcript records provider, language, transcript type, fetch time, and content hash.
- Every chunk references ordered source segment IDs.
- Every citation references persisted chunks and derives its timestamps from source segments.
- Derived data records its producing configuration fingerprint.
