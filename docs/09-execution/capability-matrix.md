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
| FastAPI `/api/v1` application | Typed routes include persistent ingest jobs, canonical transcript delivery, and live runtime health contracts | `verified` | Complete |
| React learning workspace | Evidence-first responsive shell synchronizes player, transcript, grounded chat, citations, and evidence; browser fixtures cover runtime and ingest states | `verified` | TASK-012 bilingual verification |
| Reproducible Python environment | Python 3.12, backend `pyproject.toml`, committed `uv.lock`, and pinned Node marker | `verified` | Complete |
| Local quality command | Root PowerShell/cross-platform gate; lock, Ruff, incremental Pyright, backend tests, OpenAPI drift, frontend lint/test/build | `verified` | Expand incrementally |
| Canonical database foundation | SQLite ORM schema, index lifecycle/unit of work, complete embedding identity, and canonical transcript/chunk repositories | `verified` | Complete |
| Schema migrations | Alembic migrations, upgrade/downgrade/drift/schema-start checks | `verified` | Complete |
| Persistent ingest jobs | SQLite state machine, create/status/retry/cancel API, restart recovery, real frontend polling, retry/cancel controls, and refresh restoration | `verified` | Complete |
| YouTube URL validation | Implemented baseline | `implemented` | TASK-004 |
| Transcript extraction | Configurable typed youtube-transcript-api, yt-dlp manual, and yt-dlp automatic provider chain | `verified` | Complete |
| Format-specific caption parsing | Separate bounded VTT, TTML, and SRV3 parsers with malformed-input rejection | `verified` | Complete |
| Transcript provenance/quality | Canonical segments, deterministic hashes/IDs, provider/language/type/parser/normalizer provenance, and coverage diagnostics | `verified` | Complete |
| Atomic/idempotent ingest | Job/video/canonical-transcript publication is atomic and idempotent; local ingest reports real indexing stages and keeps derived index data rebuildable | `implemented` | Local V1 hardening |
| Fixed word chunking | Evaluated Local V1 default: 140 words with 30-word overlap | `verified` | Reevaluate with dataset growth |
| Hierarchical sentence chunking | Verified timestamp-aware challenger; not selected by the v1.0 evaluation dataset | `verified` | Reevaluate with dataset growth |
| BM25 retrieval | Active-version-scoped SQLite FTS5 over canonical child chunks with deterministic ranking | `verified` | Complete |
| Dense retrieval | Separate query/document embedding ports, Ollama Qwen3 adapter, deterministic fake, identity validation, batching, and canonical chunk hydration | `verified` | Complete |
| Qdrant local index | Version-keyed local collections, health checks, rebuild/activation/rollback, query, cleanup, and SQLite reconstruction | `verified` | Complete |
| RRF hybrid fusion | Evaluated standard-profile default with BGE-M3; rank-only fusion retains deterministic ties and diagnostics | `verified` | Complete |
| Cross-encoder reranking | Evaluated opt-in BAAI/bge-reranker-v2-m3; quality gain did not justify measured default latency | `verified` | Reevaluate on stronger hardware |
| Retrieval evaluation | Versioned 12-case reviewed bilingual dataset, reproducible runner, machine-readable/Markdown report, and ADR-006 | `verified` | Expand dataset |
| Provider-independent LLM port | Typed request/result/capability/usage/error contracts with application-owned grounded orchestration | `verified` | Complete |
| Gemini adapter | Explicit opt-in REST adapter behind the common contract with structured output and usage metadata | `verified` | Complete |
| Ollama adapter | Local Qwen3 adapter with structured output, timeout/error mapping, health check, and configurable model/context | `verified` | Complete |
| Structured answer/citation validation | Strict grounded-answer schema, bilingual policy, allowed-citation validation, and one bounded repair attempt | `verified` | Complete |
| Vietnamese/English language policy | Transcript selection defaults to ordered `vi`, `en`; no end-to-end retrieval/generation evaluation yet | `implemented` | TASK-012 |
| Production deployment | Intentionally deferred | `planned` | Future production phase |

## Known current risks

- Docs previously described configuration and flow that did not match code; the old manual docs were removed.
- A failed local ingest can leave rebuildable JSON/Chroma data; canonical SQLite readiness remains safe.
- The current oEmbed metadata adapter does not supply duration, so caption-end
  fallback remains common; when a metadata provider supplies duration it takes precedence.
- The compatibility retrieval path honors the configured Ollama embedding model, while hashing remains test/migration-only.
- The configured local generation path now selects the provider-independent Ollama adapter; Gemini remains explicit opt-in only.
- Existing working tree contains user-owned notebook, environment-example, and local data changes; tasks MUST preserve them.
