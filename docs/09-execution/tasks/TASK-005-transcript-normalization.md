# TASK-005: Normalize and Version Transcript Provenance

Status: planned

Depends on: TASK-004

## Objective

Produce validated canonical segments and a reproducible transcript fingerprint.

## Required reading

- `docs/03-specifications/ingestion-spec.md`
- `docs/04-data/storage-and-lifecycle.md`

## In scope

- Original and normalized text.
- Millisecond timestamps and stable segment IDs.
- Rolling-caption deduplication.
- Provider/language/type/version provenance.
- Quality diagnostics and content hash.

## Acceptance criteria

- [ ] Normalization is deterministic.
- [ ] Legitimate repeated speech is retained by fixtures.
- [ ] Invalid ordering/ranges fail before chunking.
- [ ] Re-fetching equivalent content produces the same content hash.
- [ ] Metadata duration is not inferred solely from the last caption when provider metadata exists.

## Verification

`uv run --project backend pytest backend/tests/unit/transcripts backend/tests/integration/transcript_persistence`

## Commit

`feat(transcript): add canonical normalization and provenance`
