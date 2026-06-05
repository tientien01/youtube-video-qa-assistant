import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


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
        duration_seconds: int | None,
        transcript_language: str | None,
        chunk_count: int,
    ) -> VideoMetadata:
        self._ensure_loaded()
        now = _utc_now()
        existing = self._metadata.get(video_id)

        metadata = VideoMetadata(
            video_id=video_id,
            url=url,
            title=title,
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
            self._metadata = {
                video_id: VideoMetadata(**metadata)
                for video_id, metadata in raw_data.items()
            }

        self._loaded = True

    def _save(self) -> None:
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            video_id: asdict(metadata)
            for video_id, metadata in self._metadata.items()
        }
        self._storage_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _default_storage_path() -> Path:
    backend_root = Path(__file__).resolve().parents[3]
    return backend_root / "data" / "vector_store" / "local_video_metadata.json"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


metadata_store = LocalVideoMetadataStore()
