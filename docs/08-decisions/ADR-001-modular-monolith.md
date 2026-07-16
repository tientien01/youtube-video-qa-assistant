---
id: ADR-001
status: accepted
date: 2026-07-16
---

# ADR-001: Use a Modular Monolith

## Decision

Keep one FastAPI backend and one React frontend through Local V1. Separate business modules with application ports and dependency rules, not network services.

## Rationale

The project is single-developer, local-first, and has no proven scaling boundary. A modular monolith minimizes operations while preserving future extraction points.

## Consequences

No Redis, Celery, Kafka, Kubernetes, or service mesh is required. Persistent jobs run in-process initially but use a durable job model that can later move to a worker.
