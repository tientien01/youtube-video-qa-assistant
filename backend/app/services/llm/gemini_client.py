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
                "maxOutputTokens": 3072,
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
        except httpx.HTTPStatusError as error:
            detail = _short_response_text(error.response)
            raise LlmError(
                f"Gemini request failed with HTTP {error.response.status_code}: {detail}"
            ) from error
        except httpx.TimeoutException as error:
            raise LlmError("Gemini request timed out.") from error
        except httpx.RequestError as error:
            raise LlmError(f"Gemini request failed before receiving a response: {error}") from error

        return _extract_text(response.json())


def _extract_text(payload: dict) -> str:
    candidates = payload.get("candidates")
    if not candidates:
        raise LlmError("Gemini response did not include candidates.")

    first_candidate = candidates[0]
    finish_reason = first_candidate.get("finishReason")
    if finish_reason == "MAX_TOKENS":
        raise LlmError("Gemini response was truncated because it reached the token limit.")

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


def _short_response_text(response: httpx.Response) -> str:
    text = response.text.strip()
    if not text:
        return "empty response body"

    return text[:500]
