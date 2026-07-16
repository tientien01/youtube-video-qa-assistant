---
id: EXEC-STATUS-001
document_status: approved
normative: true
last_verified: 2026-07-16
---

# Capability Matrix

This file reports current implementation status. Target behavior lives in specifications.

| Capability | Current implementation | Target status | Next task |
|---|---|---:|---|
| FastAPI `/api/v1` application | Implemented routes for health, video, chat, summary, notes, quiz, debug | `implemented` | TASK-010 |
| React learning workspace | React JavaScript/Vite UI exists | `implemented` | TASK-010 |
| Reproducible Python environment | Pinned `requirements.txt`; no pyproject/uv lock | `planned` | TASK-001 |
| Local quality command | Separate manual commands; no root gate | `planned` | TASK-001 |
| Canonical database | Local JSON/file stores | `planned` | TASK-002 |
| Schema migrations | None | `planned` | TASK-002 |
| Persistent ingest jobs | Synchronous request only | `planned` | TASK-003 |
| YouTube URL validation | Implemented baseline | `implemented` | TASK-004 |
| Transcript extraction | yt-dlp then limited API fallback | `implemented` | TASK-004 |
| Format-specific caption parsing | VTT parser used for every advertised format | `planned` | TASK-004 |
| Transcript provenance/quality | Language only; no provider/type/quality record | `planned` | TASK-005 |
| Atomic/idempotent ingest | Independent JSON/vector/metadata writes | `planned` | TASK-003 |
| Fixed word chunking | 140 words, 30-word overlap | `implemented` | TASK-006 |
| Hierarchical sentence chunking | Not implemented | `planned` | TASK-006 |
| BM25 retrieval | Local JSON BM25 baseline | `implemented` | TASK-008 |
| Dense retrieval | Hashing/sentence-transformer and local JSON/Chroma adapters | `implemented` | TASK-007 |
| Qdrant local index | Not implemented | `planned` | TASK-007 |
| RRF hybrid fusion | Weighted normalized score fusion | `planned` | TASK-008 |
| Cross-encoder reranking | Lexical overlap reranker | `planned` | TASK-008 |
| Retrieval evaluation | Metrics runner/example dataset exists; no curated release dataset | `implemented` | TASK-011 |
| Provider-independent LLM port | Minimal text-generation protocol exists | `implemented` | TASK-009 |
| Gemini adapter | Optional adapter exists | `implemented` | TASK-009 |
| Ollama adapter | Not implemented | `planned` | TASK-009 |
| Structured answer/citation validation | Sources returned separately; no strict model schema validation | `planned` | TASK-009 |
| Vietnamese/English language policy | Preferred captions include `en`, `vi`; no end-to-end policy/eval | `planned` | TASK-012 |
| Production deployment | Intentionally deferred | `planned` | Future production phase |

## Known current risks

- Docs previously described configuration and flow that did not match code; the old manual docs were removed.
- Subtitle provider fallback does not cover all retryable/blocking failures.
- SRV3 and TTML selections are currently parsed as VTT.
- Ingest writes are not atomic and cache identity is incomplete.
- Current duration is inferred from the last transcript segment.
- Current hashing embedding is not a production semantic model.
- Existing working tree contains user-owned notebook, environment-example, and local data changes; tasks MUST preserve them.
