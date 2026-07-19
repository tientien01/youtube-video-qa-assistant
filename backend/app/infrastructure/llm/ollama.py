from __future__ import annotations

import json

import httpx

from app.application.llm.contracts import (
    GenerationRequest,
    GenerationResult,
    GenerationUsage,
    LlmCapabilities,
    LlmInvalidOutputError,
)
from app.infrastructure.llm.http_errors import raise_mapped_http_error


class OllamaLlmProvider:
    def __init__(
        self,
        *,
        model: str = "qwen3:4b",
        base_url: str = "http://127.0.0.1:11434",
        context_window: int = 8_192,
        timeout_seconds: float = 120.0,
        keep_alive: str = "30m",
        client: httpx.Client | None = None,
    ) -> None:
        if not model.strip() or context_window <= 0 or not keep_alive.strip():
            raise ValueError("Ollama model, context window, and keep-alive must be configured.")
        self._model = model
        self._context_window = context_window
        self._keep_alive = keep_alive
        self._client = client or httpx.Client(base_url=base_url, timeout=timeout_seconds)

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def model(self) -> str:
        return self._model

    @property
    def capabilities(self) -> LlmCapabilities:
        return LlmCapabilities(streaming=False, structured_output=True, usage_metadata=True)

    def health_check(self) -> bool:
        try:
            response = self._client.get("/api/tags")
            response.raise_for_status()
            payload = response.json()
            names = {
                str(item.get("name") or item.get("model"))
                for item in payload.get("models", [])
                if isinstance(item, dict)
            }
        except (httpx.HTTPError, ValueError, AttributeError):
            return False
        return self.model in names

    def generate(self, request: GenerationRequest) -> GenerationResult:
        messages = []
        if request.system_instruction:
            messages.append({"role": "system", "content": request.system_instruction})
        messages.extend({"role": message.role, "content": message.content} for message in request.messages)
        payload: dict[str, object] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "think": False,
            "keep_alive": self._keep_alive,
            "options": {
                "temperature": request.options.temperature,
                "num_predict": request.options.max_output_tokens,
                "num_ctx": request.options.context_window or self._context_window,
            },
        }
        if request.response_schema is not None:
            payload["format"] = request.response_schema
            messages[-1]["content"] += f"\nJSON schema: {json.dumps(request.response_schema, separators=(',', ':'))}"
        try:
            response = self._client.post("/api/chat", json=payload, timeout=request.options.timeout_seconds)
            response.raise_for_status()
            body = response.json()
            text = str(body["message"]["content"]).strip()
        except httpx.HTTPError as error:
            raise_mapped_http_error("Ollama", error)
        except (KeyError, TypeError, ValueError) as error:
            raise LlmInvalidOutputError("Ollama returned an invalid response payload.") from error
        return GenerationResult(
            text=text,
            provider=self.name,
            model=str(body.get("model") or self.model),
            finish_reason=str(body.get("done_reason")) if body.get("done_reason") else None,
            usage=GenerationUsage(
                input_tokens=_optional_int(body.get("prompt_eval_count")),
                output_tokens=_optional_int(body.get("eval_count")),
                total_tokens=_sum_optional(body.get("prompt_eval_count"), body.get("eval_count")),
            ),
            duration_ms=_nanoseconds_to_ms(body.get("total_duration")),
        )


def _optional_int(value: object) -> int | None:
    return int(value) if isinstance(value, int | float) else None


def _sum_optional(left: object, right: object) -> int | None:
    if not isinstance(left, int | float) or not isinstance(right, int | float):
        return None
    return int(left + right)


def _nanoseconds_to_ms(value: object) -> int | None:
    return round(float(value) / 1_000_000) if isinstance(value, int | float) else None
