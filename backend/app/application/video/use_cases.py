from __future__ import annotations

from dataclasses import dataclass

from app.domain.entities import TranscriptSegment


class TranscriptNotFound(LookupError):
    pass


@dataclass(frozen=True, slots=True)
class VideoTranscript:
    video_id: str
    language_code: str
    segments: tuple[TranscriptSegment, ...]


class VideoTranscriptApplication:
    def __init__(self, uow_factory) -> None:
        self._uow_factory = uow_factory

    def get(self, youtube_video_id: str) -> VideoTranscript:
        with self._uow_factory() as uow:
            video = uow.videos.get_by_youtube_id(youtube_video_id)
            if video is None:
                raise TranscriptNotFound(f"Video {youtube_video_id} was not found.")
            transcript = uow.transcripts.get_active(video.id)
            if transcript is None:
                raise TranscriptNotFound(f"Video {youtube_video_id} has no active transcript.")
            segments = tuple(uow.transcripts.list_segments(transcript.id))
        return VideoTranscript(youtube_video_id, transcript.language_code, segments)
