# TASK-004: Implement Typed Transcript Provider Adapters

Status: planned

Depends on: TASK-003

## Objective

Make transcript acquisition fallback complete, typed, observable, and format-correct.

## Required reading

- `docs/03-specifications/ingestion-spec.md`
- `docs/10-references/related-projects.md`

## In scope

- Provider-independent transcript result/error contract.
- Adapters for youtube-transcript-api and yt-dlp.
- Explicit provider ordering and language/manual-auto ranking.
- Format-specific VTT, TTML, and SRV3 parsing or explicit rejection.
- Fixture-based timeout, block, not-found, malformed, and fallback tests.

## Non-goals

- ASR implementation
- Proxy vendor integration
- Chunking

## Acceptance criteria

- [ ] Every retryable provider failure can advance to the next configured provider.
- [ ] Permanent video errors do not retry indefinitely.
- [ ] An unrelated manual language does not outrank a requested generated language.
- [ ] No selected subtitle format is parsed by an incompatible parser.
- [ ] Attempt diagnostics contain no secrets or raw excessive payloads.

## Verification

`uv run --project backend pytest backend/tests/unit/ingest/providers backend/tests/integration/ingest_fallback`

## Commit

`feat(ingest): add typed transcript provider chain`
