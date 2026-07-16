from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from importlib.metadata import version
from typing import Any

import requests
from requests import exceptions as requests_exceptions
from youtube_transcript_api import (
    CouldNotRetrieveTranscript,
    IpBlocked,
    NoTranscriptFound,
    RequestBlocked,
    TranscriptsDisabled,
    VideoUnavailable,
    YouTubeRequestFailed,
    YouTubeTranscriptApi,
)

from app.application.ingest.transcript import (
    SourceTranscriptSegment,
    SubtitleFormat,
    TranscriptDocument,
    TranscriptFailureCode,
    TranscriptProviderError,
    language_rank,
)
from app.domain.entities import TranscriptType


class _TimeoutSession(requests.Session):
    def __init__(self, timeout: tuple[float, float]) -> None:
        super().__init__()
        self._timeout = timeout

    def request(self, method: str, url: str, **kwargs):
        kwargs.setdefault("timeout", self._timeout)
        return super().request(method, url, **kwargs)


class YouTubeTranscriptApiProvider:
    name = "youtube_transcript_api"

    def __init__(
        self,
        *,
        connect_timeout_seconds: float = 5.0,
        read_timeout_seconds: float = 20.0,
        api_factory: Callable[[], Any] | None = None,
    ) -> None:
        timeout = (connect_timeout_seconds, read_timeout_seconds)
        self._api_factory = api_factory or (lambda: YouTubeTranscriptApi(http_client=_TimeoutSession(timeout)))

    def fetch(self, video_id: str, preferred_languages: Sequence[str]) -> TranscriptDocument:
        try:
            transcript_list = self._api_factory().list(video_id)
            transcript = select_transcript(transcript_list, preferred_languages)
            snippets = transcript.fetch()
        except (NoTranscriptFound, TranscriptsDisabled) as error:
            raise TranscriptProviderError(
                TranscriptFailureCode.NOT_FOUND,
                "youtube-transcript-api found no usable transcript.",
                retryable=False,
            ) from error
        except VideoUnavailable as error:
            raise TranscriptProviderError(
                TranscriptFailureCode.VIDEO_UNAVAILABLE,
                "Video is unavailable or cannot be accessed.",
                retryable=False,
                terminal=True,
            ) from error
        except (RequestBlocked, IpBlocked) as error:
            raise TranscriptProviderError(
                TranscriptFailureCode.PROVIDER_BLOCKED,
                "youtube-transcript-api was blocked by YouTube.",
                retryable=True,
            ) from error
        except (YouTubeRequestFailed, CouldNotRetrieveTranscript, requests_exceptions.RequestException) as error:
            raise TranscriptProviderError(
                TranscriptFailureCode.DOWNLOAD_FAILED,
                "youtube-transcript-api could not retrieve transcript data.",
                retryable=True,
            ) from error

        segments = tuple(_source_segment(snippet) for snippet in snippets if _segment_text(snippet))
        if not segments:
            raise TranscriptProviderError(
                TranscriptFailureCode.PARSE_FAILED,
                "youtube-transcript-api returned an empty transcript.",
                retryable=False,
            )
        return TranscriptDocument(
            provider=self.name,
            provider_version=version("youtube-transcript-api"),
            language_code=str(transcript.language_code),
            transcript_type=TranscriptType.GENERATED if transcript.is_generated else TranscriptType.MANUAL,
            source_format=SubtitleFormat.STRUCTURED,
            segments=segments,
        )


def select_transcript(transcripts: Iterable[Any], preferred_languages: Sequence[str]) -> Any:
    candidates = list(transcripts)
    if not candidates:
        raise TranscriptProviderError(
            TranscriptFailureCode.NOT_FOUND,
            "youtube-transcript-api found no transcript candidates.",
            retryable=False,
        )
    return min(
        enumerate(candidates),
        key=lambda item: (
            language_rank(str(item[1].language_code), preferred_languages),
            1 if item[1].is_generated else 0,
            item[0],
        ),
    )[1]


def _source_segment(snippet: Any) -> SourceTranscriptSegment:
    start_ms = round(float(_value(snippet, "start", 0)) * 1000)
    duration_ms = round(float(_value(snippet, "duration", 0)) * 1000)
    try:
        return SourceTranscriptSegment(
            text=_segment_text(snippet),
            start_ms=start_ms,
            end_ms=start_ms + duration_ms,
        )
    except ValueError as error:
        raise TranscriptProviderError(
            TranscriptFailureCode.PARSE_FAILED,
            "youtube-transcript-api returned an invalid transcript segment.",
            retryable=False,
        ) from error


def _segment_text(snippet: Any) -> str:
    return str(_value(snippet, "text", "")).strip()


def _value(value: Any, key: str, default: Any) -> Any:
    return value.get(key, default) if isinstance(value, dict) else getattr(value, key, default)
