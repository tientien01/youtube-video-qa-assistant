from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from importlib.metadata import version
from typing import Any, cast

import requests
from requests import exceptions as requests_exceptions
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError, ExtractorError

from app.application.ingest.transcript import (
    SubtitleFormat,
    TranscriptDocument,
    TranscriptFailureCode,
    TranscriptProviderError,
    language_rank,
)
from app.domain.entities import TranscriptType
from app.infrastructure.ingest.transcript.parsers import SubtitleParseError, parse_subtitle


YOUTUBE_WATCH_URL = "https://www.youtube.com/watch?v={video_id}"
FORMAT_PRIORITY = (SubtitleFormat.VTT, SubtitleFormat.SRV3, SubtitleFormat.TTML)


@dataclass(frozen=True, slots=True)
class SubtitleTrack:
    language_code: str
    transcript_type: TranscriptType
    subtitle_format: SubtitleFormat
    url: str


class YtDlpTranscriptProvider:
    def __init__(
        self,
        transcript_type: TranscriptType,
        *,
        connect_timeout_seconds: float = 5.0,
        read_timeout_seconds: float = 20.0,
        ydl_factory: Callable[[dict[str, Any]], Any] | None = None,
        http_get: Callable[..., Any] = requests.get,
    ) -> None:
        if transcript_type not in {TranscriptType.MANUAL, TranscriptType.GENERATED}:
            raise ValueError("yt-dlp provider supports manual or generated transcripts only.")
        self.transcript_type = transcript_type
        self.name = "yt_dlp_manual" if transcript_type is TranscriptType.MANUAL else "yt_dlp_automatic"
        self._connect_timeout = connect_timeout_seconds
        self._read_timeout = read_timeout_seconds
        self._ydl_factory = ydl_factory or (lambda options: YoutubeDL(params=cast(Any, options)))
        self._http_get = http_get

    def fetch(self, video_id: str, preferred_languages: Sequence[str]) -> TranscriptDocument:
        try:
            with self._ydl_factory(self._options()) as ydl:
                video_info = cast(
                    dict[str, Any],
                    ydl.extract_info(YOUTUBE_WATCH_URL.format(video_id=video_id), download=False) or {},
                )
        except (DownloadError, ExtractorError) as error:
            raise _metadata_error(error) from error

        track = select_track(video_info, self.transcript_type, preferred_languages)
        try:
            response = self._http_get(
                track.url,
                timeout=(self._connect_timeout, self._read_timeout),
            )
            response.raise_for_status()
        except requests_exceptions.Timeout as error:
            raise TranscriptProviderError(
                TranscriptFailureCode.DOWNLOAD_FAILED,
                f"{self.name} subtitle download timed out.",
                retryable=True,
            ) from error
        except requests_exceptions.RequestException as error:
            raise TranscriptProviderError(
                TranscriptFailureCode.DOWNLOAD_FAILED,
                f"{self.name} could not download subtitle data.",
                retryable=True,
            ) from error

        try:
            segments = parse_subtitle(response.text, track.subtitle_format)
        except SubtitleParseError as error:
            raise TranscriptProviderError(
                TranscriptFailureCode.PARSE_FAILED,
                f"{self.name} returned malformed {track.subtitle_format.value} subtitles.",
                retryable=False,
            ) from error
        return TranscriptDocument(
            provider=self.name,
            provider_version=version("yt-dlp"),
            language_code=track.language_code,
            transcript_type=track.transcript_type,
            source_format=track.subtitle_format,
            segments=segments,
        )

    def _options(self) -> dict[str, Any]:
        return {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
            "socket_timeout": self._read_timeout,
            "retries": 0,
            "fragment_retries": 0,
        }


def select_track(
    video_info: dict[str, Any],
    transcript_type: TranscriptType,
    preferred_languages: Sequence[str],
) -> SubtitleTrack:
    manual = video_info.get("subtitles") or {}
    automatic = video_info.get("automatic_captions") or {}
    selected_group = manual if transcript_type is TranscriptType.MANUAL else automatic

    preferred = _ranked_tracks(selected_group, transcript_type, preferred_languages, preferred_only=True)
    if preferred:
        return preferred[0]

    # A requested generated caption must outrank an unrelated manual caption.
    if transcript_type is TranscriptType.MANUAL:
        preferred_automatic = _ranked_tracks(
            automatic,
            TranscriptType.GENERATED,
            preferred_languages,
            preferred_only=True,
        )
        if preferred_automatic:
            raise TranscriptProviderError(
                TranscriptFailureCode.NOT_FOUND,
                "No preferred-language manual subtitle; trying automatic captions.",
                retryable=False,
            )

    fallback = _ranked_tracks(selected_group, transcript_type, preferred_languages, preferred_only=False)
    if not fallback:
        raise TranscriptProviderError(
            TranscriptFailureCode.NOT_FOUND,
            f"No supported {transcript_type.value} subtitle track was found.",
            retryable=False,
        )
    return fallback[0]


def _ranked_tracks(
    group: dict[str, list[dict[str, Any]]],
    transcript_type: TranscriptType,
    preferred_languages: Sequence[str],
    *,
    preferred_only: bool,
) -> list[SubtitleTrack]:
    ranked: list[tuple[tuple[int, int, int], SubtitleTrack]] = []
    for language_order, (language_code, entries) in enumerate(group.items()):
        rank = language_rank(language_code, preferred_languages)
        if preferred_only and rank >= len(preferred_languages):
            continue
        for entry_order, entry in enumerate(entries or []):
            subtitle_format = _supported_format(entry.get("ext"))
            url = entry.get("url")
            if subtitle_format is None or not url:
                continue
            format_rank = FORMAT_PRIORITY.index(subtitle_format)
            ranked.append(
                (
                    (rank, format_rank, language_order + entry_order),
                    SubtitleTrack(
                        language_code=language_code,
                        transcript_type=transcript_type,
                        subtitle_format=subtitle_format,
                        url=str(url),
                    ),
                )
            )
    ranked.sort(key=lambda item: item[0])
    return [track for _, track in ranked]


def _supported_format(value: Any) -> SubtitleFormat | None:
    try:
        return SubtitleFormat(str(value).lower())
    except ValueError:
        return None


def _metadata_error(error: Exception) -> TranscriptProviderError:
    message = str(error).lower()
    if any(marker in message for marker in ("private video", "video unavailable", "removed", "does not exist")):
        return TranscriptProviderError(
            TranscriptFailureCode.VIDEO_UNAVAILABLE,
            "Video is unavailable or cannot be accessed.",
            retryable=False,
            terminal=True,
        )
    if any(marker in message for marker in ("429", "blocked", "too many requests")):
        return TranscriptProviderError(
            TranscriptFailureCode.PROVIDER_BLOCKED,
            "yt-dlp subtitle metadata request was blocked by YouTube.",
            retryable=True,
        )
    return TranscriptProviderError(
        TranscriptFailureCode.DOWNLOAD_FAILED,
        "yt-dlp could not retrieve subtitle metadata.",
        retryable=True,
    )
