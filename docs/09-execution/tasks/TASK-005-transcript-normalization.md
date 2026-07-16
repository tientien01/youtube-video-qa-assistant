# TASK-005: Normalize and Version Transcript Provenance

Status: verified

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

- [x] Normalization is deterministic.
- [x] Legitimate repeated speech is retained by fixtures.
- [x] Invalid ordering/ranges fail before chunking.
- [x] Re-fetching equivalent content produces the same content hash.
- [x] Metadata duration is not inferred solely from the last caption when provider metadata exists.

## Verification

`uv run --project backend pytest backend/tests/unit/transcripts backend/tests/integration/transcript_persistence`

Verified with 7 deterministic normalization/publication tests and the full local
quality gate. Canonical text uses Unicode NFKC, HTML entity decoding, whitespace
normalization, time-bounded rolling-caption deduplication, SHA-256 content hashes,
and UUIDv5 transcript/segment identities. Parser and normalizer provenance are
versioned independently. SQLite activation is transactional and reuses an
equivalent canonical version without duplicating segments.

## Commit

`feat(transcript): add canonical normalization and provenance`
