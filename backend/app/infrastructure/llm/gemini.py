from __future__ import annotations

import httpx

from app.application.llm.contracts import (
    GenerationRequest,
    GenerationResult,
    GenerationUsage,
    LlmCapabilities,
    LlmContextOverflowError,
    LlmInvalidOutputError,
)
from app.infrastructure.llm.http_errors import raise_mapped_http_error


_GEMINI_API = "https://generativelanguage.googleapis.com/v1beta"


class GeminiLlmProvider:
    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gemini-2.5-flash",
        timeout_seconds: float = 60.0,
        client: httpx.Client | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("Gemini API key is required when Gemini is explicitly selected.")
        self._api_key = api_key
        self._model = model
        self._client = client or httpx.Client(base_url=_GEMINI_API, timeout=timeout_seconds)

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def model(self) -> str:
        return self._model

    @property
    def capabilities(self) -> LlmCapabilities:
        return LlmCapabilities(streaming=False, structured_output=True, usage_metadata=True)

    def health_check(self) -> bool:
        try:
            response = self._client.get(f"/models/{self.model}", headers={"x-goog-api-key": self._api_key})
            response.raise_for_status()
        except httpx.HTTPError:
            return False
        return True

    def generate(self, request: GenerationRequest) -> GenerationResult:
        contents = [
            {
                "role": "model" if message.role == "assistant" else "user",
                "parts": [{"text": message.content}],
            }
            for message in request.messages
        ]
        generation_config: dict[str, object] = {
            "temperature": request.options.temperature,
            "maxOutputTokens": request.options.max_output_tokens,
        }
        if request.response_schema is not None:
            generation_config.update(
                {"responseMimeType": "application/json", "responseJsonSchema": request.response_schema}
            )
        payload: dict[str, object] = {"contents": contents, "generationConfig": generation_config}
        if request.system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": request.system_instruction}]}
        try:
            response = self._client.post(
                f"/models/{self.model}:generateContent",
                headers={"x-goog-api-key": self._api_key},
                json=payload,
                timeout=request.options.timeout_seconds,
            )
            response.raise_for_status()
            body = response.json()
            candidate = body["candidates"][0]
            finish_reason = str(candidate.get("finishReason") or "")
            if finish_reason == "MAX_TOKENS":
                raise LlmContextOverflowError("Gemini output reached the configured token limit.")
            text = "\n".join(
                str(part["text"]).strip()
                for part in candidate["content"]["parts"]
                if isinstance(part, dict) and part.get("text")
            ).strip()
        except httpx.HTTPError as error:
            raise_mapped_http_error("Gemini", error)
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise LlmInvalidOutputError("Gemini returned an invalid response payload.") from error
        usage = body.get("usageMetadata") if isinstance(body.get("usageMetadata"), dict) else {}
        return GenerationResult(
            text=text,
            provider=self.name,
            model=self.model,
            finish_reason=finish_reason or None,
            usage=GenerationUsage(
                input_tokens=_int_or_none(usage.get("promptTokenCount")),
                output_tokens=_int_or_none(usage.get("candidatesTokenCount")),
                total_tokens=_int_or_none(usage.get("totalTokenCount")),
            ),
        )


def _int_or_none(value: object) -> int | None:
    return int(value) if isinstance(value, int | float) else None
