# TASK-010: Expose Job UX and Typed Frontend Contracts

Status: planned

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

## Non-goals

- Full frontend rewrite
- SSE
- UI design overhaul

## Acceptance criteria

- [ ] Frontend renders each job terminal/active state.
- [ ] Refresh restores persisted job state.
- [ ] API schema drift check passes.
- [ ] Migrated files contain no handwritten duplicate backend response interfaces.
- [ ] Existing chat/learning features remain usable.

## Verification

```powershell
uv run --project backend pytest backend/tests/integration/api
npm --prefix frontend run lint
npm --prefix frontend run test
npm --prefix frontend run build
```

## Commit

`feat(video): add typed ingest job experience`
