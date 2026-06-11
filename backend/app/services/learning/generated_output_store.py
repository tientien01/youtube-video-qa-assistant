import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class GeneratedOutput:
    video_id: str
    output_type: str
    mode: str
    content: str
    source_chunk_ids: list[str]
    created_at: str
    updated_at: str
    generation_mode: str = "fallback"
    provider: str = "fallback"
    fallback_reason: str | None = None


class LocalGeneratedOutputStore:
    def __init__(self, storage_path: Path | None = None) -> None:
        self._storage_path = storage_path or _default_storage_path()
        self._outputs: dict[str, dict[str, dict[str, GeneratedOutput]]] = {}
        self._loaded = False

    def get_output(
        self,
        *,
        video_id: str,
        output_type: str,
        mode: str,
    ) -> GeneratedOutput | None:
        self._ensure_loaded()
        return self._outputs.get(output_type, {}).get(video_id, {}).get(mode)

    def upsert_output(
        self,
        *,
        video_id: str,
        output_type: str,
        mode: str,
        content: str,
        source_chunk_ids: list[str],
        generation_mode: str = "fallback",
        provider: str = "fallback",
        fallback_reason: str | None = None,
    ) -> GeneratedOutput:
        self._ensure_loaded()
        existing_output = self.get_output(
            video_id=video_id,
            output_type=output_type,
            mode=mode,
        )
        now = _utc_now()
        generated_output = GeneratedOutput(
            video_id=video_id,
            output_type=output_type,
            mode=mode,
            content=content,
            source_chunk_ids=source_chunk_ids,
            created_at=existing_output.created_at if existing_output else now,
            updated_at=now,
            generation_mode=generation_mode,
            provider=provider,
            fallback_reason=fallback_reason,
        )

        self._outputs.setdefault(output_type, {}).setdefault(video_id, {})[mode] = generated_output
        self._save()
        return generated_output

    def delete_video(self, video_id: str) -> bool:
        self._ensure_loaded()
        deleted = False
        for outputs_by_video in self._outputs.values():
            if video_id in outputs_by_video:
                del outputs_by_video[video_id]
                deleted = True

        if deleted:
            self._save()

        return deleted

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return

        if self._storage_path.exists():
            raw_data = json.loads(self._storage_path.read_text(encoding="utf-8"))
            self._outputs = {
                output_type: {
                    video_id: {
                        mode: _generated_output_from_data(output_data)
                        for mode, output_data in outputs_by_mode.items()
                    }
                    for video_id, outputs_by_mode in outputs_by_video.items()
                }
                for output_type, outputs_by_video in raw_data.items()
            }

        self._loaded = True

    def _save(self) -> None:
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            output_type: {
                video_id: {
                    mode: output.__dict__
                    for mode, output in outputs_by_mode.items()
                }
                for video_id, outputs_by_mode in outputs_by_video.items()
            }
            for output_type, outputs_by_video in self._outputs.items()
        }
        self._storage_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _default_storage_path() -> Path:
    backend_root = Path(__file__).resolve().parents[3]
    return backend_root / "data" / "generated_outputs" / "local_generated_outputs.json"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _generated_output_from_data(output_data: dict) -> GeneratedOutput:
    return GeneratedOutput(
        video_id=output_data["video_id"],
        output_type=output_data["output_type"],
        mode=output_data["mode"],
        content=output_data["content"],
        source_chunk_ids=list(output_data.get("source_chunk_ids", [])),
        created_at=output_data["created_at"],
        updated_at=output_data["updated_at"],
        generation_mode=output_data.get("generation_mode", "fallback"),
        provider=output_data.get("provider", "fallback"),
        fallback_reason=output_data.get("fallback_reason"),
    )


generated_output_store = LocalGeneratedOutputStore()
