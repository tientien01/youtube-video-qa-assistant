---
id: OPS-LOCAL-001
document_status: approved
implementation_status: planned
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

The current repository still uses `backend/requirements.txt`; migration is TASK-001.

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
