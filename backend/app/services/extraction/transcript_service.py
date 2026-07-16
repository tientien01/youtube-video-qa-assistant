"""Deprecated transcript compatibility exports; remove with the legacy service layer."""

from app.application.ingest.transcript import (
    TranscriptAcquisitionError,
    TranscriptFailureCode,
)


class TranscriptNotFoundError(TranscriptAcquisitionError):
    def __init__(self, message: str) -> None:
        super().__init__(
            TranscriptFailureCode.NOT_FOUND,
            message,
            retryable=False,
            attempts=(),
        )


class TranscriptFetchError(TranscriptAcquisitionError):
    def __init__(self, message: str) -> None:
        super().__init__(
            TranscriptFailureCode.DOWNLOAD_FAILED,
            message,
            retryable=True,
            attempts=(),
        )


__all__ = ["TranscriptFetchError", "TranscriptNotFoundError"]
