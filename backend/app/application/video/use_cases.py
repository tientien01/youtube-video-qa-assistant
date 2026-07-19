from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from app.domain.entities import TranscriptSegment, Video, VideoStatus


logger = logging.getLogger(__name__)


class TranscriptNotFound(LookupError):
    pass


class VideoNotFound(LookupError):
    pass


@dataclass(frozen=True, slots=True)
class VideoTranscript:
    video_id: str
    language_code: str
    segments: tuple[TranscriptSegment, ...]


@dataclass(frozen=True, slots=True)
class VideoLibraryItem:
    video_id: str
    title: str
    url: str
    channel_title: str | None
    thumbnail_url: str | None
    duration_seconds: int | None
    transcript_language: str | None
    chunk_count: int
    created_at: str
    updated_at: str


class VideoLibraryApplication:
    """Read and delete videos from SQLite, the canonical Local V1 store."""

    def __init__(
        self,
        uow_factory,
        *,
        legacy_chunk_count: Callable[[str], int] | None = None,
        delete_legacy_data: Callable[[str], bool] | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._legacy_chunk_count = legacy_chunk_count or (lambda _video_id: 0)
        self._delete_legacy_data = delete_legacy_data or (lambda _video_id: False)

    def list(self, *, limit: int = 50) -> list[VideoLibraryItem]:
        with self._uow_factory() as uow:
            return [
                self._to_item(video, uow)
                for video in uow.videos.list_recent(limit)
                if video.status is VideoStatus.READY
            ]

    def get(self, youtube_video_id: str) -> VideoLibraryItem:
        with self._uow_factory() as uow:
            video = uow.videos.get_by_youtube_id(youtube_video_id)
            if video is None or video.status is not VideoStatus.READY:
                raise VideoNotFound(f"Video {youtube_video_id} was not found in the local library.")
            return self._to_item(video, uow)

    def delete(self, youtube_video_id: str) -> bool:
        """Delete canonical data idempotently, then clean deprecated stores.

        SQLite deletion is committed first so a derived-store failure can never
        restore a canonical video. A later repeated DELETE retries legacy cleanup.
        """

        canonical_deleted = False
        with self._uow_factory() as uow:
            video = uow.videos.get_by_youtube_id(youtube_video_id)
            if video is not None:
                canonical_deleted = uow.videos.delete(video.id)
                uow.commit()

        try:
            legacy_deleted = self._delete_legacy_data(youtube_video_id)
        except Exception:
            logger.exception("Legacy cleanup failed for video_id=%s", youtube_video_id)
            legacy_deleted = False
        return canonical_deleted or legacy_deleted

    def _to_item(self, video: Video, uow) -> VideoLibraryItem:
        transcript = uow.transcripts.get_active(video.id)
        index_version = uow.indexes.get_active(video.id)
        canonical_chunk_count = (
            len(uow.indexes.list_chunks(index_version.id, child_only=True)) if index_version is not None else 0
        )
        return VideoLibraryItem(
            video_id=video.youtube_video_id,
            title=video.title,
            url=video.canonical_url,
            channel_title=video.channel_title,
            thumbnail_url=video.thumbnail_url,
            duration_seconds=video.duration_ms // 1000 if video.duration_ms is not None else None,
            transcript_language=transcript.language_code if transcript is not None else None,
            chunk_count=canonical_chunk_count or self._legacy_chunk_count(video.youtube_video_id),
            created_at=video.created_at.isoformat(),
            updated_at=video.updated_at.isoformat(),
        )


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
