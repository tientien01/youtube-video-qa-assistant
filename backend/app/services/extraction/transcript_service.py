import html
import re
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
    YouTubeTranscriptApi,
    YouTubeRequestFailed,
)
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError, ExtractorError

from app.schemas.transcript import TranscriptSegment


PREFERRED_LANGUAGE_PREFIXES = ("en", "vi")
SUBTITLE_FORMAT_PRIORITY = ("vtt", "srv3", "ttml")
YOUTUBE_WATCH_URL = "https://www.youtube.com/watch?v={video_id}"
VTT_TIME_PATTERN = re.compile(
    r"(?P<start>\d{1,2}:\d{2}(?::\d{2})?[.,]\d{3})\s+-->\s+"
    r"(?P<end>\d{1,2}:\d{2}(?::\d{2})?[.,]\d{3})"
)
TAG_PATTERN = re.compile(r"<[^>]+>")


class TranscriptNotFoundError(Exception):
    """Raised when a video transcript cannot be found or used."""


class TranscriptFetchError(Exception):
    """Raised when YouTube transcript retrieval fails before transcript selection."""


def fetch_transcript(video_id: str) -> tuple[list[TranscriptSegment], str]:
    try:
        return _fetch_transcript_with_ytdlp(video_id)
    except TranscriptNotFoundError:
        return _fetch_transcript_with_youtube_transcript_api(video_id)


def _fetch_transcript_with_ytdlp(video_id: str) -> tuple[list[TranscriptSegment], str]:
    video_url = YOUTUBE_WATCH_URL.format(video_id=video_id)
    try:
        with YoutubeDL(_yt_dlp_options()) as ydl:
            video_info = ydl.extract_info(video_url, download=False)
    except (DownloadError, ExtractorError) as error:
        raise TranscriptFetchError(
            "yt-dlp could not retrieve YouTube subtitle metadata. The request may be blocked by YouTube."
        ) from error

    subtitle_choice = _select_ytdlp_subtitle(video_info or {})
    if subtitle_choice is None:
        raise TranscriptNotFoundError("Transcript not found for this video.")

    subtitle_url = subtitle_choice["url"]
    try:
        response = requests.get(subtitle_url, timeout=20)
        response.raise_for_status()
    except requests_exceptions.SSLError as error:
        raise TranscriptFetchError(
            "Could not download YouTube subtitles because SSL certificate verification failed."
        ) from error
    except requests_exceptions.RequestException as error:
        raise TranscriptFetchError("Could not download YouTube subtitles.") from error

    segments = _parse_subtitle_text(response.text, subtitle_choice["ext"])
    if not segments:
        raise TranscriptNotFoundError("Transcript is empty.")

    return segments, subtitle_choice["language_code"]


def _yt_dlp_options() -> dict[str, Any]:
    return {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        "socket_timeout": 20,
        "retries": 2,
        "fragment_retries": 2,
    }


def _select_ytdlp_subtitle(video_info: dict[str, Any]) -> dict[str, str] | None:
    subtitles = video_info.get("subtitles") or {}
    automatic_captions = video_info.get("automatic_captions") or {}

    for subtitle_group in (subtitles, automatic_captions):
        choice = _select_subtitle_from_group(subtitle_group)
        if choice is not None:
            return choice

    return None


def _select_subtitle_from_group(subtitle_group: dict[str, list[dict[str, Any]]]) -> dict[str, str] | None:
    for language_code in _preferred_language_codes(subtitle_group):
        entries = subtitle_group.get(language_code) or []
        selected_entry = _select_subtitle_entry(entries)
        if selected_entry is not None:
            return {
                "language_code": language_code,
                "ext": str(selected_entry.get("ext") or "vtt").lower(),
                "url": str(selected_entry["url"]),
            }

    return None


def _preferred_language_codes(subtitle_group: dict[str, list[dict[str, Any]]]) -> list[str]:
    language_codes = list(subtitle_group.keys())
    preferred_codes = [
        language_code
        for language_code in language_codes
        if _is_preferred_language(language_code)
    ]
    return preferred_codes or language_codes


def _select_subtitle_entry(entries: list[dict[str, Any]]) -> dict[str, Any] | None:
    entries_with_url = [entry for entry in entries if entry.get("url")]
    for subtitle_format in SUBTITLE_FORMAT_PRIORITY:
        for entry in entries_with_url:
            if str(entry.get("ext") or "").lower() == subtitle_format:
                return entry

    return entries_with_url[0] if entries_with_url else None


def _parse_subtitle_text(text: str, subtitle_format: str) -> list[TranscriptSegment]:
    if subtitle_format == "vtt":
        return _parse_vtt(text)

    return _parse_vtt(text)


def _parse_vtt(text: str) -> list[TranscriptSegment]:
    segments: list[TranscriptSegment] = []
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    index = 0

    while index < len(lines):
        line = lines[index].strip()
        time_match = VTT_TIME_PATTERN.search(line)
        if time_match is None:
            index += 1
            continue

        start_seconds = _parse_timestamp(time_match.group("start"))
        end_seconds = _parse_timestamp(time_match.group("end"))
        index += 1

        text_lines = []
        while index < len(lines) and lines[index].strip():
            cleaned_line = _clean_subtitle_line(lines[index])
            if cleaned_line:
                text_lines.append(cleaned_line)
            index += 1

        segment_text = _dedupe_words(" ".join(text_lines))
        if segment_text and end_seconds > start_seconds:
            segments.append(
                TranscriptSegment(
                    text=segment_text,
                    start_seconds=start_seconds,
                    end_seconds=end_seconds,
                )
            )

    return _merge_adjacent_duplicate_segments(segments)


def _clean_subtitle_line(line: str) -> str:
    without_tags = TAG_PATTERN.sub("", line)
    decoded = html.unescape(without_tags)
    return " ".join(decoded.split())


def _dedupe_words(text: str) -> str:
    words = text.split()
    if not words:
        return ""

    deduped_words = [words[0]]
    for word in words[1:]:
        if word != deduped_words[-1]:
            deduped_words.append(word)

    return " ".join(deduped_words)


def _merge_adjacent_duplicate_segments(segments: list[TranscriptSegment]) -> list[TranscriptSegment]:
    merged_segments: list[TranscriptSegment] = []
    for segment in segments:
        if merged_segments and segment.text == merged_segments[-1].text:
            previous_segment = merged_segments[-1]
            merged_segments[-1] = TranscriptSegment(
                text=previous_segment.text,
                start_seconds=previous_segment.start_seconds,
                end_seconds=max(previous_segment.end_seconds, segment.end_seconds),
            )
            continue

        merged_segments.append(segment)

    return merged_segments


def _parse_timestamp(value: str) -> float:
    normalized_value = value.replace(",", ".")
    parts = normalized_value.split(":")
    seconds = float(parts[-1])
    minutes = int(parts[-2])
    hours = int(parts[-3]) if len(parts) == 3 else 0
    return (hours * 3600) + (minutes * 60) + seconds


def _fetch_transcript_with_youtube_transcript_api(video_id: str) -> tuple[list[TranscriptSegment], str]:
    try:
        transcript_api = YouTubeTranscriptApi()
        transcript_list = transcript_api.list(video_id)
        transcript = _select_transcript(transcript_list)
        raw_segments = transcript.fetch()
    except (NoTranscriptFound, TranscriptsDisabled) as error:
        raise TranscriptNotFoundError("Transcript not found for this video.") from error
    except VideoUnavailable as error:
        raise TranscriptNotFoundError("Video is unavailable or cannot be accessed.") from error
    except requests_exceptions.SSLError as error:
        raise TranscriptFetchError(
            "Could not connect to YouTube transcript service because SSL certificate verification failed."
        ) from error
    except requests_exceptions.RequestException as error:
        raise TranscriptFetchError("Could not connect to YouTube transcript service.") from error
    except (RequestBlocked, IpBlocked, YouTubeRequestFailed, CouldNotRetrieveTranscript) as error:
        raise TranscriptFetchError(
            "YouTube transcript retrieval was blocked or failed. The deployment IP may be blocked by YouTube."
        ) from error

    segments = [
        segment
        for segment in (_normalize_segment(raw_segment) for raw_segment in raw_segments)
        if segment is not None
    ]
    if not segments:
        raise TranscriptNotFoundError("Transcript is empty.")

    return segments, transcript.language_code


def _select_transcript(transcript_list):
    transcripts = list(transcript_list)
    preferred_transcripts = [
        transcript for transcript in transcripts if _is_preferred_language(transcript.language_code)
    ]
    candidate_transcripts = preferred_transcripts or transcripts

    manual_transcript = next(
        (transcript for transcript in candidate_transcripts if not transcript.is_generated),
        None,
    )
    if manual_transcript is not None:
        return manual_transcript

    generated_transcript = next(
        (transcript for transcript in candidate_transcripts if transcript.is_generated),
        None,
    )
    if generated_transcript is not None:
        return generated_transcript

    raise TranscriptNotFoundError("Usable transcript not found for this video.")


def _is_preferred_language(language_code: str) -> bool:
    normalized_language_code = language_code.lower()
    return any(
        normalized_language_code == prefix or normalized_language_code.startswith(f"{prefix}-")
        for prefix in PREFERRED_LANGUAGE_PREFIXES
    )


def _normalize_segment(segment) -> TranscriptSegment | None:
    text = str(_read_segment_value(segment, "text", "")).strip()

    if not text:
        return None

    start_seconds = float(_read_segment_value(segment, "start", 0))
    duration_seconds = float(_read_segment_value(segment, "duration", 0))

    return TranscriptSegment(
        text=text,
        start_seconds=start_seconds,
        end_seconds=start_seconds + duration_seconds,
    )


def _read_segment_value(segment, key: str, default=None):
    if isinstance(segment, dict):
        return segment.get(key, default)

    return getattr(segment, key, default)
