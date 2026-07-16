# TASK-003: Add Persistent Atomic Ingest Lifecycle

Status: ready

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

## Non-goals

- Redis/Celery
- Full provider rewrite
- SSE progress

## Acceptance criteria

- [ ] Invalid transitions are rejected.
- [ ] Duplicate requests share or reuse the appropriate job.
- [ ] Failure in each publish stage cannot create a false `ready` video.
- [ ] Restart preserves terminal job records and diagnoses interrupted jobs.
- [ ] API reports real stage and stable error envelope.

## Verification

`uv run --project backend pytest backend/tests/unit/ingest backend/tests/integration/ingest_jobs`

## Commit

`feat(ingest): add persistent atomic job lifecycle`
