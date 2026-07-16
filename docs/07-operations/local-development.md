---
id: OPS-LOCAL-001
document_status: approved
implementation_status: verified
normative: true
last_verified: 2026-07-16
---

# Supported Local Development Environment

## Supported platforms

- Windows 11: first-class development environment
- Current Ubuntu LTS/Linux: first-class production-compatible environment
- macOS: best effort until covered by a maintained verification report

## Pinned toolchain target

- Python 3.12
- `uv` with `pyproject.toml` and committed `uv.lock`
- Node.js 22 LTS
- npm with committed `package-lock.json`
- Ollama current supported local release

`backend/pyproject.toml` and `backend/uv.lock` are authoritative. `backend/requirements.txt` is a deprecated compatibility snapshot and MUST NOT receive new dependencies.

## Clean setup

From the repository root:

```powershell
# Install uv once, then let uv install the pinned Python toolchain if needed.
python -m pip install --user uv
python -m uv python install 3.12

# Create/synchronize backend/.venv from the committed lockfile.
python -m uv sync --project backend --locked

# Install the frontend from package-lock.json.
npm.cmd --prefix frontend ci

# Run the complete deterministic local gate.
./scripts/verify.ps1
```

On Linux/macOS, use `uv` and `npm` directly and run:

```bash
uv sync --project backend --locked
npm --prefix frontend ci
python3 scripts/verify.py
```

Application startup commands:

```powershell
python -m uv run --project backend uvicorn app.main:app --app-dir backend --reload
npm.cmd --prefix frontend run dev
```

Canonical database migration commands, run explicitly from the repository root:

```powershell
python -m uv run --project backend alembic -c backend/alembic.ini upgrade head
python -m uv run --project backend alembic -c backend/alembic.ini current
```

The default local database path is `backend/data/app.db`. The current API continues to use its JSON stores until TASK-003 adopts the database runtime. Downgrade is intended for migration development and tests, not routine deletion of user data:

```powershell
python -m uv run --project backend alembic -c backend/alembic.ini downgrade base
```

Model downloads and live YouTube/Ollama smoke tests are explicit operations and are not part of `scripts/verify.py`.

## Runtime profiles

### Test

No YouTube, model download, Ollama, or paid provider. Uses fixtures, temporary SQLite, in-memory/local Qdrant, and fake providers.

### Light

- 16 GB RAM recommended
- CPU operation supported with reduced generation speed
- Qwen3 4B generation
- Qwen3 Embedding 0.6B
- Reranker disabled by default

### Standard

- 24-32 GB RAM or suitable GPU
- Qwen3 8B generation
- Multilingual embedding and reranker enabled

## Configuration rules

- Non-secret defaults live in typed configuration and documented profiles.
- Secrets live only in ignored environment files or process environment.
- Startup validates configuration and fails with actionable errors.
- Tests override settings without reading developer credentials.
- Model downloads occur in an explicit setup command.
- Ollama unavailability disables generation, not ingest or retrieval.

## Observability

Logs MUST include request/job ID, video ID where safe, stage, provider name, elapsed time, outcome, and stable error code. Logs MUST NOT contain credentials, full prompts by default, or sensitive provider responses.
