# TASK-004: Implement Typed Transcript Provider Adapters

Status: verified

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
- Migrate transcript acquisition out of `app/services/` into `infrastructure/ingest/`;
  production code MUST NOT add new imports from the legacy transcript service.

## Non-goals

- ASR implementation
- Proxy vendor integration
- Chunking

## Acceptance criteria

- [x] Every retryable provider failure can advance to the next configured provider.
- [x] Permanent video errors do not retry indefinitely.
- [x] An unrelated manual language does not outrank a requested generated language.
- [x] No selected subtitle format is parsed by an incompatible parser.
- [x] Attempt diagnostics contain no secrets or raw excessive payloads.

## Verification

`uv run --project backend pytest backend/tests/unit/ingest/providers backend/tests/integration/ingest_fallback`

Verified with 21 deterministic provider/parser/fallback/boundary tests. The provider
contract follows the installed youtube-transcript-api list/fetch model and
yt-dlp subtitle metadata model. VTT, TTML, and SRV3 have separate parsers;
provider attempts are persisted in execution order with bounded safe diagnostics.

## Commit

`feat(ingest): add typed transcript provider chain`
