---
id: DOCS-INDEX
document_status: approved
normative: true
last_verified: 2026-07-16
---

# Documentation Control Plane

This directory defines both the target product and the safe path from the current codebase to that target. It is designed for humans and AI coding agents.

## Read this first

1. [Product vision](00-product/product-vision.md)
2. [Interface specification](00-product/interface-specification.md)
3. [Target architecture](01-architecture/target-architecture.md)
4. [Current capability matrix](09-execution/capability-matrix.md)
5. [Roadmap and task order](09-execution/roadmap.md)
6. The assigned task under `09-execution/tasks/`

## Document authority

- `normative: true` documents use `MUST`, `SHOULD`, and `MAY` as requirements.
- ADRs record accepted architectural decisions and override older explanatory text.
- Specifications describe target behavior, not implementation status.
- The capability matrix is the only summary of implementation status.
- FastAPI-generated OpenAPI is authoritative for the currently implemented HTTP schema.
- A capability is `verified` only when its acceptance tests pass.

## Status vocabulary

`document_status: approved` means the document itself is reviewed and authoritative. It does not mean the described target exists. Implementation state appears only in the capability matrix and task status.

| Status | Meaning |
|---|---|
| `planned` | Target is specified but implementation has not started. |
| `in_progress` | An active task is implementing the capability. |
| `implemented` | Code exists but the complete acceptance gate has not passed. |
| `verified` | Code and required automated verification pass. |
| `deprecated` | Kept temporarily for migration and must not be extended. |

## Map

| Area | Purpose |
|---|---|
| `00-product` | Users, product outcome, scope, and success measures |
| `01-architecture` | Target system shape and dependency rules |
| `02-domain` | Stable concepts and lifecycle models |
| `03-specifications` | Normative ingest, chunking, retrieval, LLM, and language behavior |
| `04-data` | Ownership, persistence, migrations, and lifecycle |
| `05-api` | API evolution rules; current schema comes from OpenAPI |
| `06-quality` | Local quality gates and evaluation requirements |
| `07-operations` | Supported local environment and operational behavior |
| `08-decisions` | Accepted architecture decision records |
| `09-execution` | Capability status, roadmap, task format, and executable tasks |
| `10-references` | External projects and primary technical references |

## Change discipline

Every implementation task MUST link its normative specifications and ADRs. If code reveals a contradiction, the task MUST stop at the contradiction, update or propose an ADR, and continue only after the target is unambiguous.
