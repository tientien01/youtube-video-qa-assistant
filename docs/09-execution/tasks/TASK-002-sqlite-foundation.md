# TASK-002: Introduce Canonical SQLite Persistence

Status: ready

Depends on: TASK-001

## Objective

Create the canonical SQLAlchemy/Alembic persistence foundation without yet replacing every JSON store.

## Required reading

- `docs/04-data/storage-and-lifecycle.md`
- `docs/02-domain/domain-model.md`
- `docs/08-decisions/ADR-003-sqlite-qdrant.md`

## In scope

- SQLAlchemy 2.x models for videos, ingest jobs/attempts, transcripts, segments, chunks, mappings, and index versions.
- Alembic initial migration.
- SQLite foreign keys and WAL configuration.
- Repository ports and SQLite adapters.
- Temporary-database integration tests.

## Non-goals

- Deleting JSON stores
- Migrating chat/learning artifacts
- Qdrant or ingest orchestration

## Acceptance criteria

- [ ] Upgrade from empty DB and downgrade are tested.
- [ ] Foreign-key violations fail.
- [ ] Repository tests never use developer data.
- [ ] Domain/application modules do not import SQLAlchemy.
- [ ] Startup reports incompatible schema instead of silently recreating it.

## Verification

`uv run --project backend pytest backend/tests/unit backend/tests/integration/db`

## Commit

`feat(data): add canonical SQLite persistence foundation`
