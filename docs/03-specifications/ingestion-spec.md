---
id: SPEC-INGEST-001
document_status: approved
implementation_status: partial
normative: true
last_verified: 2026-07-16
related_adrs: [ADR-001, ADR-003]
---

# Ingestion Specification

## Contract

Ingest MUST either produce a complete, versioned, queryable video or a diagnosable failure without damaging the last ready version. It cannot promise that every YouTube video is accessible.

## Input and identity

- Accept only supported YouTube URL forms and validated 11-character video IDs.
- Canonicalize a video URL before persistence.
- One active ingest job per video and target fingerprint is allowed.
- Repeating a completed ingest with the same fingerprint MUST be idempotent.

## Provider order

The transcript provider chain MUST be configurable. Initial order:

1. `youtube-transcript-api` structured transcript
2. yt-dlp manual subtitles
3. yt-dlp automatic captions
4. optional local ASR, disabled by default

Fallback decisions MUST use typed provider outcomes, not one generic exception. Attempts MUST record provider, elapsed time, outcome, and safe diagnostic text.

## Transcript selection

- Requested language order defaults to Vietnamese then English when the user gives no preference.
- Within the same preferred language, manual captions outrank generated captions.
- An unrelated manual language MUST NOT outrank a generated requested language.
- The selected transcript records exact language code and `manual`, `generated`, or `asr` type.

## Parsing and normalization

- VTT, TTML, and SRV3 MUST use format-specific parsers or be rejected as unsupported.
- Parsers MUST reject empty output and invalid timestamp ranges.
- Normalization MUST preserve original text, normalized text, source order, and millisecond timestamps.
- Rolling caption duplicates and exact adjacent duplicates MUST be removed without deleting legitimate repetition.
- Validation MUST check monotonic ordering, non-empty content, positive durations, and transcript coverage diagnostics.

## Reliability

- Network calls MUST define connect/read timeouts.
- Retryable failures use bounded exponential backoff with jitter.
- Permanent failures, such as invalid IDs or unavailable videos, MUST NOT loop.
- Cancellation MUST leave no published partial index.
- All exceptions exposed through the API MUST map to a stable error code and stage.

Initial error codes:

```text
INVALID_VIDEO_URL
VIDEO_UNAVAILABLE
TRANSCRIPT_NOT_FOUND
TRANSCRIPT_PROVIDER_BLOCKED
TRANSCRIPT_DOWNLOAD_FAILED
TRANSCRIPT_PARSE_FAILED
TRANSCRIPT_VALIDATION_FAILED
EMBEDDING_PROVIDER_UNAVAILABLE
INDEX_WRITE_FAILED
INGEST_CANCELLED
INTERNAL_INGEST_ERROR
```

## Commit protocol

1. Fetch and construct a staged ingest result.
2. Validate transcript and chunks.
3. Write canonical records within a SQLite transaction.
4. Write a versioned derived vector index.
5. Activate the index version.
6. Mark job and video `ready`.

If steps 3-5 fail, the previously ready version MUST remain queryable. Orphan staged vectors MUST be safe to delete or overwrite.

## Fingerprint

The index fingerprint MUST include:

```text
video_id
transcript_content_hash
transcript_provider/version
parser_version
normalizer_version
chunker_config_hash
embedding_provider/model/revision/dimension
```

## Acceptance matrix

Automated fixtures MUST cover manual/automatic Vietnamese and English captions, multiple languages, no transcript, private/deleted video, malformed formats, rolling duplicates, timeout and retry, re-ingest, provider fallback, atomic failure, and fingerprint changes. Live YouTube tests are optional manual smoke tests and MUST NOT be the deterministic suite.
