# TASK-003: Add Persistent Atomic Ingest Lifecycle

Status: verified

Depends on: TASK-002

## Objective

Replace synchronous opaque ingest orchestration with a persistent job state machine and safe publication protocol.

## Required reading

- `docs/03-specifications/ingestion-spec.md`
- `docs/02-domain/domain-model.md`
- `docs/05-api/api-guidelines.md`

## In scope

- State transitions and transition validation.
- One in-process job runner.
- Per-video concurrency guard and idempotency key.
- Typed job errors, attempts, timings, retry/cancel hooks.
- Staged canonical commit and preservation of last ready version.
- Job create/status API; keep old ingest endpoint temporarily as a compatibility facade.
- Application ingest use cases become the only location for new lifecycle orchestration.
- The opaque legacy ingest service is called through a temporary infrastructure adapter;
  TASK-003 does not add new business logic to `app/services/`.

## Non-goals

- Redis/Celery
- Full provider rewrite
- Deleting `app/services/` before its transcript, retrieval, and generation users migrate
- SSE progress

## Acceptance criteria

- [x] Invalid transitions are rejected.
- [x] Duplicate requests share or reuse the appropriate job.
- [x] Failure in each publish stage cannot create a false `ready` video.
- [x] Restart preserves terminal job records and diagnoses interrupted jobs.
- [x] API reports real stage and stable error envelope.
- [x] API routes for ingest jobs call application use cases rather than legacy services.
- [x] Domain and application ingest modules contain no SQLAlchemy, FastAPI, or provider SDK imports.

## Verification

`uv run --project backend pytest backend/tests/unit/ingest backend/tests/integration/ingest_jobs`

Verified with 10 focused tests and the complete local gate: 86 backend tests,
Ruff, incremental Pyright, frontend lint, and frontend build. The compatibility
processor reports only stages it can observe; TASK-004–007 replace its opaque
internals and provide detailed provider/chunking/embedding progress.

## Commit

`feat(ingest): add persistent atomic job lifecycle`
