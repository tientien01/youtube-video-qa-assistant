# TASK-001: Establish the Reproducible Local Toolchain

Status: ready

Depends on: none

## Objective

Make backend setup and verification reproducible on Windows 11 and Linux without changing application behavior.

## Required reading

- `docs/07-operations/local-development.md`
- `docs/06-quality/quality-gates.md`
- `docs/08-decisions/ADR-006-language-and-toolchain.md`

## In scope

- Add backend `pyproject.toml` targeting Python 3.12 and migrate declared runtime dependencies.
- Generate and commit `uv.lock`.
- Add development groups for pytest, Ruff, and Pyright.
- Add `.python-version` and `.nvmrc`/equivalent Node version marker.
- Add root `scripts/verify.ps1` and a cross-platform Python or shell-equivalent entry point.
- Document exact clean setup commands.
- Preserve `backend/requirements.txt` only as a clearly deprecated compatibility export if still needed.

## Non-goals

- Dependency upgrades unrelated to Python 3.12 compatibility
- SQLite migration
- Application module refactoring
- Docker or CI/CD

## Acceptance criteria

- [ ] A clean Python 3.12 environment can run `uv sync` from documented instructions.
- [ ] `uv lock --project backend --check` passes and the lockfile is committed.
- [ ] Existing backend tests run through `uv run --project backend pytest` with failures either fixed in scope or accurately reported before commit.
- [ ] Frontend lint and build run through the root verification command.
- [ ] Verification does not read developer secrets or require Ollama/network.
- [ ] Existing user-owned dirty files are not overwritten.

## Verification

```powershell
uv lock --project backend --check
uv run --project backend pytest backend/tests
npm --prefix frontend run lint
npm --prefix frontend run build
./scripts/verify.ps1
```

## Documentation update

Mark reproducible environment and local quality command in the capability matrix according to actual results.

## Commit

`build: establish reproducible local toolchain`
