---
id: DATA-001
document_status: approved
implementation_status: implemented
normative: true
last_verified: 2026-07-16
related_adrs: [ADR-003]
---

# Storage Ownership and Data Lifecycle

## Ownership

SQLite is the canonical Local V1 database. Qdrant local and FTS indexes are derived and rebuildable.

TASK-002 establishes these canonical foundation tables:

```text
videos
ingest_jobs
ingest_attempts
transcripts
transcript_segments
chunks
chunk_segments
index_versions
```

Later persistence tasks add product-owned data after their lifecycle is specified:

```text
chat_sessions
chat_messages
generated_artifacts
evaluation_runs
```

## Technology

- SQLAlchemy 2.x for persistence mapping
- Alembic for every schema change
- SQLite foreign keys enabled
- WAL mode for local concurrency
- Millisecond integer timestamps for transcript positions
- UTC timestamps for application events

Application startup MUST NOT silently recreate or mutate an incompatible schema. Migrations are explicit and testable.

The current JSON-backed API remains active during migration. `start_database_runtime()` is the fail-fast boundary for database-backed use cases: it verifies the Alembic revision and never calls `create_all`. TASK-003 is the first application flow that adopts this foundation.

## Derived data

Chunks are reproducible from canonical segments and chunker configuration. Embeddings and Qdrant points are reproducible from chunks and embedding configuration. Generated artifacts are not reproducible guarantees and retain their provider/prompt/model metadata.

## Delete

Deleting a video MUST remove or tombstone its transcript, chunks, active vectors, chats, and generated artifacts according to one documented transaction policy. A failed vector deletion MUST be retryable and MUST NOT resurrect the canonical video.

## Migration path

Local JSON and Chroma data are deprecated once SQLite/Qdrant migration is verified. Migration MUST be repeatable, report rejected records, preserve IDs where valid, and leave original files untouched until explicit cleanup.

Production later replaces SQLite with PostgreSQL through persistence adapters and changes Qdrant connection mode from local path to server URL. Domain objects and API semantics MUST not depend on either change.
