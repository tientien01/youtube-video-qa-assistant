# TASK-010: Expose Job UX and Typed Frontend Contracts

Status: verified

Depends on: TASK-003, TASK-009

## Objective

Expose real ingest status/retry behavior and begin incremental TypeScript migration using generated API types.

## Required reading

- `docs/05-api/api-guidelines.md`
- `docs/01-architecture/target-architecture.md`

## In scope

- Finalize job create/status/retry/cancel API schemas.
- Reproducibly generate frontend OpenAPI types.
- Migrate video ingest/history API modules and components to TypeScript.
- Replace fake progress with polled real job state.
- Present retryable stage/error information without leaking internals.
- Move Pydantic transport models from `app/schemas/` to `app/api/contracts/`.
- Remove the legacy `app/services/` folder after all production imports migrate.

## Non-goals

- Full frontend rewrite
- SSE
- UI design overhaul

The approved visual overhaul is intentionally isolated in TASK-013. TASK-010
MUST leave typed feature boundaries that TASK-013 can compose without rewriting
API access again.

## Acceptance criteria

- [x] Frontend renders each job terminal/active state.
- [x] Refresh restores persisted job state.
- [x] API schema drift check passes.
- [x] Migrated files contain no handwritten duplicate backend response interfaces.
- [x] Existing chat/learning features remain usable.
- [x] `app/services/` and `app/schemas/` no longer exist.
- [x] Production code has no imports from `app.services` or `app.schemas`.
- [x] API routes call application use cases; application/domain do not import infrastructure.
- [x] Compatibility facades scheduled for removal are gone.

## Verification

```powershell
uv run --project backend pytest backend/tests/integration/ingest_jobs
uv run --project backend python scripts/generate_openapi.py --check
npm --prefix frontend run lint
npm --prefix frontend run test
npm --prefix frontend run build
```

## Commit

`feat(video): add typed ingest job experience`
