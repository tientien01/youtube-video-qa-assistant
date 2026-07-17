import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.api.contracts.chat import ChatHistoryMessage, ChatSource, RetrievalMode
from app.api.contracts.generation import GenerationMetadata


@dataclass(frozen=True)
class StoredChatMessage:
    message_id: str
    video_id: str
    question: str
    answer: str
    retrieval_mode: str
    sources: list[dict]
    generation: dict
    groundedness_warning: str | None
    created_at: str


class LocalChatHistoryStore:
    def __init__(self, storage_path: Path | None = None) -> None:
        self._storage_path = storage_path or _default_storage_path()
        self._messages_by_video: dict[str, list[StoredChatMessage]] = {}
        self._loaded = False

    def add_message(
        self,
        *,
        video_id: str,
        question: str,
        answer: str,
        retrieval_mode: RetrievalMode,
        sources: list[ChatSource],
        generation: GenerationMetadata,
        groundedness_warning: str | None,
    ) -> ChatHistoryMessage:
        self._ensure_loaded()
        message = StoredChatMessage(
            message_id=str(uuid4()),
            video_id=video_id,
            question=question,
            answer=answer,
            retrieval_mode=retrieval_mode,
            sources=[source.model_dump() for source in sources],
            generation=generation.model_dump(),
            groundedness_warning=groundedness_warning,
            created_at=datetime.now(UTC).isoformat(),
        )
        self._messages_by_video.setdefault(video_id, []).insert(0, message)
        self._save()
        return _message_to_schema(message)

    def list_messages(self, video_id: str) -> list[ChatHistoryMessage]:
        self._ensure_loaded()
        return [
            _message_to_schema(message)
            for message in self._messages_by_video.get(video_id, [])
        ]

    def delete_video(self, video_id: str) -> bool:
        self._ensure_loaded()
        if video_id not in self._messages_by_video:
            return False

        del self._messages_by_video[video_id]
        self._save()
        return True

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return

        if self._storage_path.exists():
            raw_data = json.loads(self._storage_path.read_text(encoding="utf-8"))
            self._messages_by_video = {
                video_id: [
                    StoredChatMessage(**message_data)
                    for message_data in messages
                ]
                for video_id, messages in raw_data.items()
            }

        self._loaded = True

    def _save(self) -> None:
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            video_id: [asdict(message) for message in messages]
            for video_id, messages in self._messages_by_video.items()
        }
        self._storage_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _message_to_schema(message: StoredChatMessage) -> ChatHistoryMessage:
    return ChatHistoryMessage(
        message_id=message.message_id,
        video_id=message.video_id,
        question=message.question,
        answer=message.answer,
        retrieval_mode=message.retrieval_mode,
        sources=[ChatSource(**source) for source in message.sources],
        generation=GenerationMetadata(**message.generation),
        groundedness_warning=message.groundedness_warning,
        created_at=message.created_at,
    )


def _default_storage_path() -> Path:
    backend_root = Path(__file__).resolve().parents[3]
    return backend_root / "data" / "chat_history" / "local_chat_history.json"


chat_history_store = LocalChatHistoryStore()
