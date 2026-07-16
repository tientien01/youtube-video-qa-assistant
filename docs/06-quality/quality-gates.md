---
id: QUALITY-001
document_status: approved
implementation_status: planned
normative: true
last_verified: 2026-07-16
---

# Quality Gates and Evaluation

## Local gate

CI/CD is intentionally deferred. Every task MUST provide narrow verification and SHOULD pass the complete local gate before a direct commit to `main`.

Target root command:

```powershell
./scripts/verify.ps1
```

It MUST eventually cover:

```text
uv lock --project backend --check
Ruff lint and format check
Pyright type check
Pytest unit/integration/contract tests through `uv run --project backend`
Frontend lint, test, and production build
OpenAPI generation consistency
Documentation links and capability status checks
```

Until that script exists, each task lists the currently available equivalent commands.

## Test layers

| Layer | External network | Purpose |
|---|---:|---|
| Unit | No | Domain rules, parsers, chunk packing, fusion |
| Integration | No | SQLite, Qdrant local, provider fixtures, API |
| Contract | No | Provider ports and OpenAPI compatibility |
| Evaluation | No | Retrieval/generation quality comparisons |
| Smoke | Optional | Manually verify YouTube and Ollama integration |

Deterministic tests MUST NOT download models or contact YouTube during execution.

## Retrieval release gate

An approved evaluation dataset and baseline report MUST exist before changing the default chunker, embedding, fusion, or reranker. Reports include configuration fingerprint, dataset version, quality metrics, latency, hardware profile, and regression decision.

Threshold values are set only after the first curated dataset is reviewed; agents MUST NOT invent favorable thresholds.

## Definition of done

A task is done only when its acceptance criteria pass, migrations are reversible/tested where applicable, related normative docs remain accurate, and capability status is updated. A successful manual demo alone is not completion.
