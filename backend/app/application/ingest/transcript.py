from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from random import random
from time import monotonic, sleep
from typing import Protocol

from app.application.ingest.ports import IngestAttemptReport
from app.domain.entities import AttemptOutcome, IngestStage, TranscriptType


class TranscriptFailureCode(StrEnum):
    VIDEO_UNAVAILABLE = "VIDEO_UNAVAILABLE"
    NOT_FOUND = "TRANSCRIPT_NOT_FOUND"
    PROVIDER_BLOCKED = "TRANSCRIPT_PROVIDER_BLOCKED"
    DOWNLOAD_FAILED = "TRANSCRIPT_DOWNLOAD_FAILED"
    PARSE_FAILED = "TRANSCRIPT_PARSE_FAILED"


class SubtitleFormat(StrEnum):
    STRUCTURED = "structured"
    VTT = "vtt"
    TTML = "ttml"
    SRV3 = "srv3"


@dataclass(frozen=True, slots=True)
class SourceTranscriptSegment:
    text: str
    start_ms: int
    end_ms: int

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("Transcript segment text cannot be empty.")
        if self.start_ms < 0 or self.end_ms <= self.start_ms:
            raise ValueError("Transcript segment timestamps are invalid.")


@dataclass(frozen=True, slots=True)
class TranscriptDocument:
    provider: str
    provider_version: str | None
    language_code: str
    transcript_type: TranscriptType
    source_format: SubtitleFormat
    segments: tuple[SourceTranscriptSegment, ...]

    def __post_init__(self) -> None:
        if not self.segments:
            raise ValueError("Transcript document cannot be empty.")


class TranscriptProviderError(RuntimeError):
    def __init__(
        self,
        code: TranscriptFailureCode,
        message: str,
        *,
        retryable: bool,
        terminal: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable
        self.terminal = terminal


class TranscriptProvider(Protocol):
    name: str

    def fetch(self, video_id: str, preferred_languages: Sequence[str]) -> TranscriptDocument: ...


@dataclass(frozen=True, slots=True)
class TranscriptAcquisition:
    document: TranscriptDocument
    attempts: tuple[IngestAttemptReport, ...]


class TranscriptAcquisitionError(RuntimeError):
    def __init__(
        self,
        code: TranscriptFailureCode,
        message: str,
        *,
        retryable: bool,
        attempts: tuple[IngestAttemptReport, ...],
    ) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable
        self.attempts = attempts


class TranscriptProviderChain:
    def __init__(
        self,
        providers: Sequence[TranscriptProvider],
        *,
        max_attempts_per_provider: int = 2,
        base_backoff_seconds: float = 0.25,
        sleeper: Callable[[float], None] = sleep,
        jitter: Callable[[], float] = random,
    ) -> None:
        if not providers:
            raise ValueError("At least one transcript provider is required.")
        if max_attempts_per_provider <= 0:
            raise ValueError("max_attempts_per_provider must be positive.")
        self._providers = tuple(providers)
        self._max_attempts = max_attempts_per_provider
        self._base_backoff_seconds = max(0.0, base_backoff_seconds)
        self._sleeper = sleeper
        self._jitter = jitter

    def acquire(
        self,
        video_id: str,
        preferred_languages: Sequence[str] = ("vi", "en"),
    ) -> TranscriptAcquisition:
        attempts: list[IngestAttemptReport] = []
        last_error: TranscriptProviderError | None = None
        last_retryable_error: TranscriptProviderError | None = None
        last_parse_error: TranscriptProviderError | None = None

        for provider in self._providers:
            for provider_attempt in range(1, self._max_attempts + 1):
                started = monotonic()
                try:
                    document = provider.fetch(video_id, preferred_languages)
                except TranscriptProviderError as error:
                    last_error = error
                    if error.retryable:
                        last_retryable_error = error
                    if error.code is TranscriptFailureCode.PARSE_FAILED:
                        last_parse_error = error
                    attempts.append(
                        _attempt_report(
                            provider.name,
                            AttemptOutcome.FAILED,
                            started,
                            error.code.value,
                            str(error),
                        )
                    )
                    if error.terminal:
                        raise _acquisition_error(error, attempts) from error
                    if error.retryable and provider_attempt < self._max_attempts:
                        self._sleeper(self._retry_delay(provider_attempt))
                        continue
                    break
                except Exception:
                    wrapped = TranscriptProviderError(
                        TranscriptFailureCode.DOWNLOAD_FAILED,
                        "Transcript provider failed unexpectedly.",
                        retryable=True,
                    )
                    last_error = wrapped
                    last_retryable_error = wrapped
                    attempts.append(
                        _attempt_report(
                            provider.name,
                            AttemptOutcome.FAILED,
                            started,
                            wrapped.code.value,
                            str(wrapped),
                        )
                    )
                    if provider_attempt < self._max_attempts:
                        self._sleeper(self._retry_delay(provider_attempt))
                        continue
                    break
                else:
                    attempts.append(_attempt_report(provider.name, AttemptOutcome.SUCCEEDED, started))
                    return TranscriptAcquisition(document=document, attempts=tuple(attempts))

        if last_error is None:
            last_error = TranscriptProviderError(
                TranscriptFailureCode.NOT_FOUND,
                "Transcript not found for this video.",
                retryable=False,
            )
        raise _acquisition_error(last_retryable_error or last_parse_error or last_error, attempts)

    def _retry_delay(self, attempt_number: int) -> float:
        exponential = self._base_backoff_seconds * (2 ** (attempt_number - 1))
        return exponential + (exponential * 0.25 * max(0.0, min(self._jitter(), 1.0)))


_URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)
_CREDENTIAL_PATTERN = re.compile(r"(?i)\b(api[_-]?key|token|authorization|password|cookie)\s*[=:]\s*[^\s,;]+")


def safe_diagnostic(message: str) -> str:
    compact = " ".join(message.split())
    without_urls = _URL_PATTERN.sub("[redacted-url]", compact)
    without_credentials = _CREDENTIAL_PATTERN.sub(lambda match: f"{match.group(1)}=[redacted]", without_urls)
    return without_credentials[:300]


def language_rank(language_code: str, preferred_languages: Sequence[str]) -> int:
    normalized = language_code.lower()
    for index, requested in enumerate(preferred_languages):
        prefix = requested.lower()
        if normalized == prefix or normalized.startswith(f"{prefix}-"):
            return index
    return len(preferred_languages)


def _attempt_report(
    provider: str,
    outcome: AttemptOutcome,
    started: float,
    error_code: str | None = None,
    error_message: str | None = None,
) -> IngestAttemptReport:
    return IngestAttemptReport(
        provider=provider,
        stage=IngestStage.FETCHING_TRANSCRIPT,
        outcome=outcome,
        elapsed_ms=max(0, round((monotonic() - started) * 1000)),
        error_code=error_code,
        error_message=safe_diagnostic(error_message) if error_message else None,
    )


def _acquisition_error(
    error: TranscriptProviderError,
    attempts: list[IngestAttemptReport],
) -> TranscriptAcquisitionError:
    return TranscriptAcquisitionError(
        error.code,
        safe_diagnostic(str(error)),
        retryable=error.retryable,
        attempts=tuple(attempts),
    )
