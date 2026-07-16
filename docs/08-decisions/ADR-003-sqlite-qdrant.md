---
id: ADR-003
status: accepted
date: 2026-07-16
---

# ADR-003: SQLite Canonical Store and Qdrant Derived Index

## Decision

Use SQLite with SQLAlchemy/Alembic as Local V1 canonical storage, SQLite FTS5 for lexical search, and Qdrant local for derived dense vectors.

## Rationale

SQLite keeps local operation simple and transactional. Qdrant local uses an API that can move to server mode later. Separating canonical and derived data makes indexes rebuildable.

## Consequences

Current JSON and Chroma stores become migration sources and then deprecated. Production may replace SQLite with PostgreSQL without changing domain semantics.
