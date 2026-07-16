from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache
from hashlib import sha256
from importlib.metadata import version
from json import dumps

from app.application.ingest.transcript import (
    TranscriptAcquisition,
    TranscriptProvider,
    TranscriptProviderChain,
)
from app.core.config import get_settings
from app.domain.entities import TranscriptType
from app.infrastructure.ingest.transcript.youtube_transcript_api_provider import YouTubeTranscriptApiProvider
from app.infrastructure.ingest.transcript.yt_dlp_provider import YtDlpTranscriptProvider


def acquire_transcript(video_id: str) -> TranscriptAcquisition:
    settings = get_settings()
    return _provider_chain().acquire(video_id, settings.transcript_preferred_languages)


def transcript_pipeline_fingerprint() -> str:
    settings = get_settings()
    material = dumps(
        {
            "contract": "typed-transcript-v1",
            "providers": settings.transcript_provider_order,
            "languages": settings.transcript_preferred_languages,
            "attempts": settings.transcript_max_attempts_per_provider,
            "youtube_transcript_api": version("youtube-transcript-api"),
            "yt_dlp": version("yt-dlp"),
            "subtitle_parsers": "v1",
        },
        sort_keys=True,
    ).encode()
    return sha256(material).hexdigest()


@lru_cache(maxsize=1)
def _provider_chain() -> TranscriptProviderChain:
    settings = get_settings()
    providers: dict[str, Callable[[], TranscriptProvider]] = {
        "youtube_transcript_api": lambda: YouTubeTranscriptApiProvider(
            connect_timeout_seconds=settings.transcript_connect_timeout_seconds,
            read_timeout_seconds=settings.transcript_read_timeout_seconds,
        ),
        "yt_dlp_manual": lambda: YtDlpTranscriptProvider(
            TranscriptType.MANUAL,
            connect_timeout_seconds=settings.transcript_connect_timeout_seconds,
            read_timeout_seconds=settings.transcript_read_timeout_seconds,
        ),
        "yt_dlp_automatic": lambda: YtDlpTranscriptProvider(
            TranscriptType.GENERATED,
            connect_timeout_seconds=settings.transcript_connect_timeout_seconds,
            read_timeout_seconds=settings.transcript_read_timeout_seconds,
        ),
    }
    unknown = [name for name in settings.transcript_provider_order if name not in providers]
    if unknown:
        raise ValueError(f"Unknown transcript providers: {', '.join(unknown)}")
    if len(set(settings.transcript_provider_order)) != len(settings.transcript_provider_order):
        raise ValueError("Transcript provider order cannot contain duplicates.")
    return TranscriptProviderChain(
        [providers[name]() for name in settings.transcript_provider_order],
        max_attempts_per_provider=settings.transcript_max_attempts_per_provider,
    )
