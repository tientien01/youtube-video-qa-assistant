from dataclasses import dataclass

import pytest
import requests

from app.application.ingest.transcript import TranscriptFailureCode, TranscriptProviderError
from app.domain.entities import TranscriptType
from app.infrastructure.ingest.transcript.youtube_transcript_api_provider import YouTubeTranscriptApiProvider
from app.infrastructure.ingest.transcript.yt_dlp_provider import YtDlpTranscriptProvider


@dataclass
class Snippet:
    text: str
    start: float
    duration: float


class ApiTranscript:
    language_code = "vi"
    is_generated = True

    def fetch(self):
        return [Snippet("Nội dung", 1.0, 2.0)]


class FakeApi:
    def list(self, _video_id: str):
        return [ApiTranscript()]


def test_youtube_transcript_api_adapter_returns_typed_document() -> None:
    document = YouTubeTranscriptApiProvider(api_factory=FakeApi).fetch("dQw4w9WgXcQ", ("vi", "en"))

    assert document.provider == "youtube_transcript_api"
    assert document.language_code == "vi"
    assert document.transcript_type is TranscriptType.GENERATED
    assert document.segments[0].start_ms == 1000
    assert document.segments[0].end_ms == 3000


class FakeYdl:
    def __init__(self, _options):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def extract_info(self, _url: str, *, download: bool):
        assert not download
        return {"subtitles": {"vi": [{"ext": "vtt", "url": "https://example/subtitle"}]}}


def timeout_get(_url: str, **_kwargs):
    raise requests.Timeout("secret URL should not escape")


def test_ytdlp_adapter_maps_download_timeout_to_retryable_failure() -> None:
    provider = YtDlpTranscriptProvider(
        TranscriptType.MANUAL,
        ydl_factory=FakeYdl,
        http_get=timeout_get,
    )

    with pytest.raises(TranscriptProviderError) as captured:
        provider.fetch("dQw4w9WgXcQ", ("vi", "en"))

    assert captured.value.code is TranscriptFailureCode.DOWNLOAD_FAILED
    assert captured.value.retryable
