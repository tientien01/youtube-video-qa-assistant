---
id: ADR-006
status: accepted
date: 2026-07-16
---

# ADR-006: English Technical Canon and Reproducible Toolchain

## Decision

Use English for canonical technical docs and code, while the product supports Vietnamese and English. Target Python 3.12 with uv and Node.js 22 LTS with npm.

## Rationale

One technical language avoids duplicated drifting documentation. Locked dependencies and pinned runtimes make local setup reproducible across Windows and Linux.
