from collections.abc import Sequence

import pytest

from app.application.ingest.transcript import (
    SourceTranscriptSegment,
    SubtitleFormat,
    TranscriptDocument,
    TranscriptFailureCode,
    TranscriptProviderChain,
    TranscriptProviderError,
    safe_diagnostic,
)
from app.domain.entities import AttemptOutcome, TranscriptType


DOCUMENT = TranscriptDocument(
    provider="fallback",
    provider_version="1",
    language_code="vi",
    transcript_type=TranscriptType.GENERATED,
    source_format=SubtitleFormat.STRUCTURED,
    segments=(SourceTranscriptSegment("Xin chào", 0, 1000),),
)


class FakeProvider:
    def __init__(self, name: str, outcomes: list[TranscriptDocument | TranscriptProviderError]) -> None:
        self.name = name
        self.outcomes = outcomes
        self.calls = 0

    def fetch(self, video_id: str, preferred_languages: Sequence[str]) -> TranscriptDocument:
        assert video_id == "dQw4w9WgXcQ"
        assert tuple(preferred_languages) == ("vi", "en")
        outcome = self.outcomes[min(self.calls, len(self.outcomes) - 1)]
        self.calls += 1
        if isinstance(outcome, TranscriptProviderError):
            raise outcome
        return outcome


def test_retryable_failure_retries_then_advances_to_next_provider() -> None:
    blocked = TranscriptProviderError(
        TranscriptFailureCode.PROVIDER_BLOCKED,
        "Provider blocked",
        retryable=True,
    )
    primary = FakeProvider("primary", [blocked])
    fallback = FakeProvider("fallback", [DOCUMENT])
    delays: list[float] = []
    chain = TranscriptProviderChain(
        [primary, fallback],
        max_attempts_per_provider=2,
        sleeper=delays.append,
        jitter=lambda: 0,
    )

    result = chain.acquire("dQw4w9WgXcQ")

    assert result.document == DOCUMENT
    assert primary.calls == 2
    assert fallback.calls == 1
    assert delays == [0.25]
    assert [attempt.outcome for attempt in result.attempts] == [
        AttemptOutcome.FAILED,
        AttemptOutcome.FAILED,
        AttemptOutcome.SUCCEEDED,
    ]


def test_terminal_video_error_stops_without_fallback_or_retry() -> None:
    unavailable = TranscriptProviderError(
        TranscriptFailureCode.VIDEO_UNAVAILABLE,
        "Video unavailable",
        retryable=False,
        terminal=True,
    )
    primary = FakeProvider("primary", [unavailable])
    fallback = FakeProvider("fallback", [DOCUMENT])

    with pytest.raises(Exception) as captured:
        TranscriptProviderChain([primary, fallback]).acquire("dQw4w9WgXcQ")

    assert captured.value.code is TranscriptFailureCode.VIDEO_UNAVAILABLE
    assert primary.calls == 1
    assert fallback.calls == 0


@pytest.mark.parametrize(
    "code",
    [TranscriptFailureCode.NOT_FOUND, TranscriptFailureCode.PARSE_FAILED],
)
def test_provider_specific_permanent_failure_advances_without_retry(code: TranscriptFailureCode) -> None:
    primary = FakeProvider(
        "primary",
        [TranscriptProviderError(code, "Provider-specific failure", retryable=False)],
    )
    fallback = FakeProvider("fallback", [DOCUMENT])

    result = TranscriptProviderChain([primary, fallback], max_attempts_per_provider=3).acquire("dQw4w9WgXcQ")

    assert result.document == DOCUMENT
    assert primary.calls == 1
    assert fallback.calls == 1


def test_diagnostics_are_bounded_and_remove_urls_and_credentials() -> None:
    diagnostic = safe_diagnostic(
        "download https://captions.example/file?token=secret "
        "authorization=Bearer-secret cookie=session-secret " + ("x" * 500)
    )

    assert "captions.example" not in diagnostic
    assert "Bearer-secret" not in diagnostic
    assert "session-secret" not in diagnostic
    assert len(diagnostic) <= 300
