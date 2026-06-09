from collections.abc import Callable

import httpx

from app.services.llm.base import LlmError


GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
HttpPost = Callable[..., httpx.Response]


class GeminiClient:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: float = 20.0,
        http_post: HttpPost | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._http_post = http_post or httpx.post

    def generate_text(self, prompt: str) -> str:
        endpoint = f"{GEMINI_API_BASE_URL}/models/{self._model}:generateContent"
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 512,
            },
        }

        try:
            response = self._http_post(
                endpoint,
                headers={"x-goog-api-key": self._api_key},
                json=payload,
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise LlmError("Gemini request failed.") from error

        return _extract_text(response.json())


def _extract_text(payload: dict) -> str:
    candidates = payload.get("candidates")
    if not candidates:
        raise LlmError("Gemini response did not include candidates.")

    first_candidate = candidates[0]
    content = first_candidate.get("content") or {}
    parts = content.get("parts") or []
    text = "\n".join(
        str(part.get("text", "")).strip()
        for part in parts
        if isinstance(part, dict) and part.get("text")
    ).strip()

    if not text:
        raise LlmError("Gemini response did not include text.")

    return text
