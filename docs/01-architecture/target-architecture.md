---
id: ARCH-001
document_status: approved
implementation_status: planned
normative: true
last_verified: 2026-07-16
related_adrs: [ADR-001, ADR-002, ADR-003, ADR-004]
---

# Target Architecture

## System shape

The application MUST remain a modular monolith through Local V1. Modules communicate through explicit application interfaces, not network calls.

```text
React + TypeScript
        |
        v
FastAPI API
        |
        +-- Video and ingest application module
        +-- Transcript and chunking module
        +-- Indexing and retrieval module
        +-- Chat and learning module
        +-- Evaluation module
                 |
                 +-- SQLite (canonical data)
                 +-- Qdrant local (derived vector index)
                 +-- YouTube provider adapters
                 +-- Ollama provider adapters
```

## Backend module boundaries

The target backend layout is directional; tasks MAY migrate it incrementally.

```text
backend/app/
  api/                 HTTP transport and request/response contracts
  core/                configuration, errors, logging
  domain/              provider-independent entities and invariants
  application/         use cases and ports
  infrastructure/
    db/                SQLAlchemy and Alembic
    ingest/            YouTube and optional ASR adapters
    embeddings/        Ollama and test embedding adapters
    vector/            Qdrant adapter
    llm/               Ollama, Gemini, and fake adapters
  modules/
    video/
    retrieval/
    chat/
    learning/
    evaluation/
```

The migration MUST favor small moves over a repository-wide rewrite.

`app/services/` is a legacy migration source, not a target architecture layer. New
orchestration MUST be implemented as application use cases. Technology-specific
code MUST move to infrastructure modules as the corresponding task replaces it.
TASK-010 removes the legacy folder after all production imports have migrated.

Naming rules:

- Prefer `use_case.py` for application orchestration.
- Use `repository` for canonical persistence and `client` or `provider` for an
  external capability. Do not stack suffixes such as `ProviderAdapterService`.
- API Pydantic models are contracts, not database schema. The target location is
  `app/api/contracts/`.
- Alembic migrations define database schema history. Runtime revision checking is
  named `migration_guard.py`, not the ambiguous `schema.py`.

## Required ports

```python
class TranscriptProvider(Protocol): ...
class EmbeddingProvider(Protocol): ...
class TokenCounter(Protocol): ...
class SentenceSegmenter(Protocol): ...
class VectorIndex(Protocol): ...
class Reranker(Protocol): ...
class LlmProvider(Protocol): ...
class IngestJobRunner(Protocol): ...
```

Provider SDK types MUST NOT cross these ports. Domain and application layers MUST NOT import Ollama, Gemini, Qdrant, yt-dlp, or FastAPI SDK types.

## Runtime profiles

| Profile | Required services | Purpose |
|---|---|---|
| `test` | SQLite temporary DB, fake providers | Deterministic automated tests |
| `light` | SQLite, Qdrant local, Ollama | CPU-first local use; reranker optional |
| `standard` | SQLite, Qdrant local, Ollama | Stronger model and reranker |
| `production` | PostgreSQL, Qdrant server, external worker | Future deployment target |

Ingest and retrieval MUST remain usable when the LLM is unavailable. Generation endpoints MUST report provider unavailability explicitly.

## Dependency rules

- API handlers validate transport data and call application use cases.
- Application use cases own orchestration and transaction boundaries.
- Domain objects own invariants and contain no infrastructure imports.
- Infrastructure adapters implement application ports.
- A top-level `services` layer MUST NOT exist in the Local V1 target.
- The vector index is rebuildable and is never the canonical transcript store.
- Framework-specific RAG chains MUST NOT become the business-logic boundary.

## Main flows

### Ingest

```text
POST job -> persistent job -> metadata -> transcript provider chain
-> normalize -> validate -> hierarchical chunk -> embed -> stage index
-> atomic canonical commit -> publish index -> ready
```

### Question answering

```text
question -> language policy -> lexical + dense retrieval -> RRF
-> rerank -> parent/neighbor expansion -> context budget
-> LLM structured answer -> citation validation -> response
```

## Evolution constraints

- Local V1 MUST NOT require Redis, Celery, Docker, or a paid API.
- A persistent SQLite job table and in-process runner are sufficient locally.
- Later worker extraction MUST preserve the same job state machine and API semantics.
- Frontend JavaScript MUST migrate to TypeScript incrementally, not by a big-bang rewrite.
