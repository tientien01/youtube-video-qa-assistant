---
id: EXEC-ROADMAP-001
document_status: approved
normative: true
last_verified: 2026-07-17
---

# Implementation Roadmap

## Execution policy

Tasks run in dependency order and commit directly to `main` after local verification. One task equals one focused commit unless a migration task explicitly documents multiple checkpoints.

```text
TASK-001 Reproducible toolchain
    |
    v
TASK-002 SQLite foundation
    |
    v
TASK-003 Persistent ingest lifecycle
    |
    +--> TASK-004 Transcript adapters/parsers
    |          |
    |          v
    |     TASK-005 Normalize/provenance
    |          |
    |          v
    |     TASK-006 Hierarchical chunking
    |          |
    |          v
    |     TASK-007 Embedding/Qdrant
    |          |
    |          v
    |     TASK-008 Hybrid retrieval/reranking
    |
    +--> TASK-009 LLM-independent Ollama
               |
               v
          TASK-010 API/frontend migration
               |
               v
          TASK-013 Approved workspace UI

TASK-006 + TASK-008 + TASK-009
    -> TASK-011 Evaluation release gate

TASK-011 + TASK-013
    -> TASK-012 Bilingual product verification
```

## Milestones

| Milestone | Exit condition |
|---|---|
| Foundation | TASK-001 and TASK-002 verified |
| Reliable ingest | TASK-003 through TASK-006 verified |
| Serious retrieval | TASK-007, TASK-008, TASK-011 verified |
| Local bilingual product | TASK-009, TASK-010, TASK-012, TASK-013 verified |
| Production readiness | Separate future roadmap after Local V1 evidence |

## Ready now

`TASK-001` through `TASK-007` are verified. `TASK-008` is ready to add FTS5,
RRF fusion, and multilingual reranking over canonical child chunks. `TASK-009`
may proceed independently on the LLM branch of the roadmap.
