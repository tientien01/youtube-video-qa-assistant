import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


@dataclass(frozen=True)
class StoredQuizAttempt:
    attempt_id: str
    video_id: str
    mode: str
    difficulty: str
    question_type: str
    question_count: int
    source_chunk_ids: list[str]
    created_at: str


class LocalQuizAttemptStore:
    def __init__(self, storage_path: Path | None = None) -> None:
        self._storage_path = storage_path or _default_storage_path()
        self._attempts_by_video: dict[str, list[StoredQuizAttempt]] = {}
        self._loaded = False

    def add_attempt(
        self,
        *,
        video_id: str,
        mode: str,
        difficulty: str,
        question_type: str,
        question_count: int,
        source_chunk_ids: list[str],
    ) -> StoredQuizAttempt:
        self._ensure_loaded()
        attempt = StoredQuizAttempt(
            attempt_id=str(uuid4()),
            video_id=video_id,
            mode=mode,
            difficulty=difficulty,
            question_type=question_type,
            question_count=question_count,
            source_chunk_ids=source_chunk_ids,
            created_at=datetime.now(UTC).isoformat(),
        )
        self._attempts_by_video.setdefault(video_id, []).insert(0, attempt)
        self._save()
        return attempt

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return

        if self._storage_path.exists():
            raw_data = json.loads(self._storage_path.read_text(encoding="utf-8"))
            self._attempts_by_video = {
                video_id: [
                    StoredQuizAttempt(**attempt_data)
                    for attempt_data in attempts
                ]
                for video_id, attempts in raw_data.items()
            }

        self._loaded = True

    def _save(self) -> None:
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            video_id: [asdict(attempt) for attempt in attempts]
            for video_id, attempts in self._attempts_by_video.items()
        }
        self._storage_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _default_storage_path() -> Path:
    backend_root = Path(__file__).resolve().parents[4]
    return backend_root / "data" / "quiz_attempts" / "local_quiz_attempts.json"


quiz_attempt_store = LocalQuizAttemptStore()
