from __future__ import annotations

import httpx

from app.application.llm.contracts import (
    LlmContextOverflowError,
    LlmRateLimitError,
    LlmTimeoutError,
    LlmUnavailableError,
)


def raise_mapped_http_error(provider: str, error: httpx.HTTPError) -> None:
    if isinstance(error, httpx.TimeoutException):
        raise LlmTimeoutError(f"{provider} generation timed out.") from error
    if isinstance(error, httpx.HTTPStatusError):
        status = error.response.status_code
        detail = _safe_detail(error.response)
        if status == 429:
            raise LlmRateLimitError(f"{provider} rate limit exceeded: {detail}") from error
        if status in {408, 504}:
            raise LlmTimeoutError(f"{provider} generation timed out: {detail}") from error
        if status in {400, 413} and _is_context_error(detail):
            raise LlmContextOverflowError(f"{provider} context window was exceeded: {detail}") from error
        raise LlmUnavailableError(f"{provider} generation failed with HTTP {status}: {detail}") from error
    raise LlmUnavailableError(f"{provider} is unavailable: {error}") from error


def _safe_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return " ".join(response.text.split())[:300] or "empty response"
    if isinstance(payload, dict):
        return " ".join(str(payload.get("error") or payload).split())[:300]
    return "invalid error response"


def _is_context_error(detail: str) -> bool:
    normalized = detail.casefold()
    return any(marker in normalized for marker in ("context", "token limit", "too long", "maximum input"))
