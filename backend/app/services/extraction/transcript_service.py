from youtube_transcript_api import (
    NoTranscriptFound,
    TranscriptsDisabled,
    YouTubeTranscriptApi,
)

from app.schemas.transcript import TranscriptSegment


PREFERRED_LANGUAGE_PREFIXES = ("en", "vi")


class TranscriptNotFoundError(Exception):
    """Raised when a video transcript cannot be found or used."""


def fetch_transcript(video_id: str) -> tuple[list[TranscriptSegment], str]:
    try:
        transcript_api = YouTubeTranscriptApi()
        transcript_list = transcript_api.list(video_id)
        transcript = _select_transcript(transcript_list)
        raw_segments = transcript.fetch()
    except (NoTranscriptFound, TranscriptsDisabled) as error:
        raise TranscriptNotFoundError("Transcript not found for this video.") from error

    language_code = transcript.language_code
    segments = [
        segment
        for segment in (_normalize_segment(raw_segment) for raw_segment in raw_segments)
        if segment is not None
    ]

    if not segments:
        raise TranscriptNotFoundError("Transcript is empty.")

    return segments, language_code


def _select_transcript(transcript_list):
    transcripts = list(transcript_list)
    preferred_transcripts = [
        transcript for transcript in transcripts if _is_preferred_transcript(transcript)
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


def _is_preferred_transcript(transcript) -> bool:
    language_code = transcript.language_code.lower()
    return any(
        language_code == prefix or language_code.startswith(f"{prefix}-")
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
