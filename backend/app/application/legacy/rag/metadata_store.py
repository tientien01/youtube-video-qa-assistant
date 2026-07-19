import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.core.paths import DATA_DIR


@dataclass(frozen=True)
class VideoMetadata:
    video_id: str
    url: str
    title: str
    duration_seconds: int | None
    transcript_language: str | None
    chunk_count: int
    created_at: str
    updated_at: str
    channel_title: str | None = None
    thumbnail_url: str | None = None


class LocalVideoMetadataStore:
    def __init__(self, storage_path: Path | None = None) -> None:
        self._storage_path = storage_path or _default_storage_path()
        self._metadata: dict[str, VideoMetadata] = {}
        self._loaded = False

    def upsert_video(
        self,
        *,
        video_id: str,
        url: str,
        title: str,
        channel_title: str | None = None,
        thumbnail_url: str | None = None,
        duration_seconds: int | None,
        transcript_language: str | None,
        chunk_count: int,
    ) -> VideoMetadata:
        self._ensure_loaded()
        now = _next_updated_at(self._metadata.values())
        existing = self._metadata.get(video_id)

        metadata = VideoMetadata(
            video_id=video_id,
            url=url,
            title=title,
            channel_title=channel_title,
            thumbnail_url=thumbnail_url,
            duration_seconds=duration_seconds,
            transcript_language=transcript_language,
            chunk_count=chunk_count,
            created_at=existing.created_at if existing else now,
            updated_at=now,
        )
        self._metadata[video_id] = metadata
        self._save()
        return metadata

    def get_video(self, video_id: str) -> VideoMetadata | None:
        self._ensure_loaded()
        return self._metadata.get(video_id)

    def list_videos(self) -> list[VideoMetadata]:
        self._ensure_loaded()
        return sorted(
            self._metadata.values(),
            key=lambda metadata: metadata.updated_at,
            reverse=True,
        )

    def delete_video(self, video_id: str) -> bool:
        self._ensure_loaded()
        if video_id not in self._metadata:
            return False

        del self._metadata[video_id]
        self._save()
        return True

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return

        if self._storage_path.exists():
            raw_data = json.loads(self._storage_path.read_text(encoding="utf-8"))
            self._metadata = {video_id: _metadata_from_data(metadata) for video_id, metadata in raw_data.items()}

        self._loaded = True

    def _save(self) -> None:
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {video_id: asdict(metadata) for video_id, metadata in self._metadata.items()}
        self._storage_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _default_storage_path() -> Path:
    return DATA_DIR / "vector_store" / "local_video_metadata.json"


def _next_updated_at(existing_metadata: Iterable[VideoMetadata]) -> str:
    now = datetime.now(UTC)
    latest_timestamp = max(
        (datetime.fromisoformat(metadata.updated_at) for metadata in existing_metadata),
        default=None,
    )
    if latest_timestamp is not None and now <= latest_timestamp:
        now = latest_timestamp + timedelta(microseconds=1)
    return now.isoformat()


def _metadata_from_data(metadata: dict) -> VideoMetadata:
    return VideoMetadata(
        video_id=metadata["video_id"],
        url=metadata["url"],
        title=metadata["title"],
        channel_title=metadata.get("channel_title"),
        thumbnail_url=metadata.get("thumbnail_url"),
        duration_seconds=metadata.get("duration_seconds"),
        transcript_language=metadata.get("transcript_language"),
        chunk_count=metadata["chunk_count"],
        created_at=metadata["created_at"],
        updated_at=metadata["updated_at"],
    )


metadata_store = LocalVideoMetadataStore()
