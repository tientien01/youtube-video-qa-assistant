---
id: EXEC-STATUS-001
document_status: approved
normative: true
last_verified: 2026-07-17
---

# Capability Matrix

This file reports current implementation status. Target behavior lives in specifications.

| Capability | Current implementation | Target status | Next task |
|---|---|---:|---|
| FastAPI `/api/v1` application | Implemented routes for health, video, chat, summary, notes, quiz, debug | `implemented` | TASK-010 |
| React learning workspace | React JavaScript/Vite UI exists; approved evidence-first mock is specified but not implemented | `implemented` | TASK-010, TASK-013 |
| Reproducible Python environment | Python 3.12, backend `pyproject.toml`, committed `uv.lock`, and pinned Node marker | `verified` | Complete |
| Local quality command | Root PowerShell/cross-platform gate; lock, Ruff, incremental Pyright, 114 backend tests, frontend lint/build | `verified` | Expand incrementally |
| Canonical database foundation | SQLite ORM schema, index lifecycle/unit of work, complete embedding identity, and canonical transcript/chunk repositories | `verified` | Complete |
| Schema migrations | Alembic migrations, upgrade/downgrade/drift/schema-start checks | `verified` | Complete |
| Persistent ingest jobs | SQLite state machine, create/status/retry/cancel API, restart recovery, and in-process runner | `verified` | TASK-010 UX |
| YouTube URL validation | Implemented baseline | `implemented` | TASK-004 |
| Transcript extraction | Configurable typed youtube-transcript-api, yt-dlp manual, and yt-dlp automatic provider chain | `verified` | Complete |
| Format-specific caption parsing | Separate bounded VTT, TTML, and SRV3 parsers with malformed-input rejection | `verified` | Complete |
| Transcript provenance/quality | Canonical segments, deterministic hashes/IDs, provider/language/type/parser/normalizer provenance, and coverage diagnostics | `verified` | Complete |
| Atomic/idempotent ingest | Job/video/canonical-transcript publication is atomic and idempotent; new rebuildable index path exists while legacy ingest wiring remains behind a compatibility adapter | `implemented` | TASK-010 migration |
| Fixed word chunking | 140 words, 30-word overlap retained as an evaluation control | `implemented` | TASK-011 evaluation |
| Hierarchical sentence chunking | Deterministic child/parent packing, exact source/timestamp links, whole-unit overlap, hard-limit fallback, Stanza and model-aware tokenizer ports | `verified` | Complete |
| BM25 retrieval | Local JSON BM25 baseline | `implemented` | TASK-008 |
| Dense retrieval | Separate query/document embedding ports, Ollama Qwen3 adapter, deterministic fake, identity validation, batching, and canonical chunk hydration | `verified` | TASK-008 fusion |
| Qdrant local index | Version-keyed local collections, health checks, rebuild/activation/rollback, query, cleanup, and SQLite reconstruction | `verified` | Complete |
| RRF hybrid fusion | Weighted normalized score fusion | `planned` | TASK-008 |
| Cross-encoder reranking | Lexical overlap reranker | `planned` | TASK-008 |
| Retrieval evaluation | Metrics runner/example dataset exists; no curated release dataset | `implemented` | TASK-011 |
| Provider-independent LLM port | Minimal text-generation protocol exists | `implemented` | TASK-009 |
| Gemini adapter | Optional adapter exists | `implemented` | TASK-009 |
| Ollama adapter | Not implemented | `planned` | TASK-009 |
| Structured answer/citation validation | Sources returned separately; no strict model schema validation | `planned` | TASK-009 |
| Vietnamese/English language policy | Transcript selection defaults to ordered `vi`, `en`; no end-to-end retrieval/generation evaluation yet | `implemented` | TASK-012 |
| Production deployment | Intentionally deferred | `planned` | Future production phase |

## Known current risks

- Docs previously described configuration and flow that did not match code; the old manual docs were removed.
- The legacy processor can leave orphan JSON/vector data when it fails; canonical
  SQLite readiness remains safe, and TASK-010 will switch runtime wiring to the rebuildable index path.
- The current oEmbed metadata adapter does not supply duration, so caption-end
  fallback remains common; when a metadata provider supplies duration it takes precedence.
- The legacy API path still defaults to hashing/JSON retrieval until TASK-010 migrates runtime wiring; hashing remains test/migration-only in the canonical path.
- Existing working tree contains user-owned notebook, environment-example, and local data changes; tasks MUST preserve them.
