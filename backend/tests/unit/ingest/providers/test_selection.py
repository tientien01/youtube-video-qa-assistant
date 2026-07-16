from dataclasses import dataclass

import pytest

from app.application.ingest.transcript import TranscriptFailureCode, TranscriptProviderError
from app.domain.entities import TranscriptType
from app.infrastructure.ingest.transcript.youtube_transcript_api_provider import select_transcript
from app.infrastructure.ingest.transcript.yt_dlp_provider import select_track


@dataclass
class ApiTranscript:
    language_code: str
    is_generated: bool


def test_requested_generated_transcript_outranks_unrelated_manual_transcript() -> None:
    unrelated_manual = ApiTranscript("fr", False)
    requested_generated = ApiTranscript("vi", True)

    selected = select_transcript([unrelated_manual, requested_generated], ("vi", "en"))

    assert selected is requested_generated


def test_language_preference_order_precedes_manual_generated_rank() -> None:
    english_manual = ApiTranscript("en", False)
    vietnamese_generated = ApiTranscript("vi", True)

    selected = select_transcript([english_manual, vietnamese_generated], ("vi", "en"))

    assert selected is vietnamese_generated


def test_ytdlp_manual_provider_defers_to_requested_automatic_caption() -> None:
    video_info = {
        "subtitles": {"fr": [{"ext": "vtt", "url": "https://example/manual"}]},
        "automatic_captions": {"vi": [{"ext": "vtt", "url": "https://example/auto"}]},
    }

    with pytest.raises(TranscriptProviderError) as captured:
        select_track(video_info, TranscriptType.MANUAL, ("vi", "en"))

    assert captured.value.code is TranscriptFailureCode.NOT_FOUND
    automatic = select_track(video_info, TranscriptType.GENERATED, ("vi", "en"))
    assert automatic.language_code == "vi"
    assert automatic.transcript_type is TranscriptType.GENERATED


def test_ytdlp_uses_only_supported_format_entries() -> None:
    video_info = {
        "subtitles": {
            "vi": [
                {"ext": "json3", "url": "https://example/json"},
                {"ext": "ttml", "url": "https://example/ttml"},
            ]
        }
    }

    selected = select_track(video_info, TranscriptType.MANUAL, ("vi", "en"))

    assert selected.subtitle_format.value == "ttml"
