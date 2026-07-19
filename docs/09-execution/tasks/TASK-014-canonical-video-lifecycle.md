# TASK-014: Canonical Video Library Lifecycle

Status: verified

Depends on: TASK-002, TASK-003, TASK-007, TASK-010

## Objective

Make SQLite authoritative for video library reads and deletion while keeping
deprecated JSON/Chroma cleanup safe and rebuildable.

## Required reading

- `docs/04-data/storage-and-lifecycle.md`
- `docs/05-api/api-guidelines.md`
- `docs/08-decisions/ADR-003-sqlite-qdrant.md`
- `docs/00-product/interface-specification.md`

## In scope

- Canonical SQLite list/get/delete application flow.
- Idempotent deletion for stale browser entries.
- Best-effort cleanup of deprecated local JSON/Chroma data.
- Server-authoritative frontend library reconciliation.
- One backend runtime-data root independent of process working directory.
- Safe archival of previously misplaced runtime directories.

## Non-goals

- Migrating chat and generated artifacts into new SQLite tables.
- Removing compatibility retrieval implementations.
- Production Qdrant server deployment.

## Invariants

- SQLite remains the canonical Local V1 store.
- Deleting canonical data cascades transcripts, chunks, and ingest records.
- Derived-store cleanup failure cannot resurrect a canonical video.
- Existing user runtime data is archived before cleanup.

## Acceptance criteria

- [x] Video list/get reads canonical SQLite state.
- [x] Repeated delete returns successfully without `Video has not been indexed yet`.
- [x] Frontend removes browser-only stale video entries after server sync.
- [x] All default runtime paths resolve below `backend/data` from any working directory.
- [x] Misplaced runtime data remains available under `backend/data/legacy/misplaced`.
- [x] Complete repository verification passes.

## Verification

```powershell
python -m uv run --project backend pytest
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend run test
npm.cmd --prefix frontend run build
python scripts/verify.py
```

## Documentation update

- `docs/04-data/storage-and-lifecycle.md`
- `docs/07-operations/local-development.md`
- `docs/09-execution/capability-matrix.md`

## Commit

`fix(video): make SQLite library lifecycle canonical`
