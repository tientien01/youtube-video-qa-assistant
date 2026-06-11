import logging
import re
from datetime import UTC, datetime, timedelta
from dataclasses import dataclass

from app.services.llm.base import LlmClient, LlmError
from app.services.llm.config import load_llm_settings
from app.services.llm.gemini_client import GeminiClient


logger = logging.getLogger(__name__)
_provider_cooldowns: dict[str, datetime] = {}


@dataclass(frozen=True)
class OptionalLlmResult:
    text: str | None
    generation_mode: str
    provider: str
    fallback_reason: str | None = None


def generate_optional_llm_text(
    prompt: str,
    *,
    llm_client: LlmClient | None = None,
    fallback_log_message: str,
) -> str | None:
    return generate_optional_llm_result(
        prompt,
        llm_client=llm_client,
        fallback_log_message=fallback_log_message,
    ).text


def generate_optional_llm_result(
    prompt: str,
    *,
    llm_client: LlmClient | None = None,
    fallback_log_message: str,
) -> OptionalLlmResult:
    provider = "injected" if llm_client is not None else _configured_provider_name()
    cooldown_remaining = _cooldown_remaining_seconds(provider)
    if cooldown_remaining is not None:
        return OptionalLlmResult(
            text=None,
            generation_mode="fallback",
            provider=provider,
            fallback_reason=(
                f"LLM provider '{provider}' is temporarily rate-limited. "
                f"Retry after about {cooldown_remaining} seconds."
            ),
        )

    client = llm_client or build_configured_llm_client()
    if client is None:
        return OptionalLlmResult(
            text=None,
            generation_mode="fallback",
            provider="fallback",
            fallback_reason=f"LLM provider '{provider}' is not configured.",
        )

    try:
        generated_text = client.generate_text(prompt).strip()
    except LlmError as error:
        _record_provider_cooldown(provider=provider, error_message=str(error))
        logger.warning("%s: %s", fallback_log_message, error)
        return OptionalLlmResult(
            text=None,
            generation_mode="fallback",
            provider=provider,
            fallback_reason=str(error),
        )

    if not generated_text:
        logger.warning("%s: empty LLM response", fallback_log_message)
        return OptionalLlmResult(
            text=None,
            generation_mode="fallback",
            provider=provider,
            fallback_reason="LLM returned an empty response.",
        )

    return OptionalLlmResult(
        text=generated_text,
        generation_mode="llm",
        provider=provider,
    )


def build_configured_llm_client() -> LlmClient | None:
    settings = load_llm_settings()
    if settings.is_gemini_enabled and settings.gemini_api_key is not None:
        return GeminiClient(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            timeout_seconds=settings.timeout_seconds,
        )

    if settings.provider not in {"fallback", "none"}:
        logger.warning(
            "LLM provider '%s' is not configured, using fallback",
            settings.provider,
        )

    return None


def _configured_provider_name() -> str:
    return load_llm_settings().provider


def _cooldown_remaining_seconds(provider: str) -> int | None:
    cooldown_until = _provider_cooldowns.get(provider)
    if cooldown_until is None:
        return None

    remaining_seconds = int((cooldown_until - datetime.now(UTC)).total_seconds())
    if remaining_seconds <= 0:
        del _provider_cooldowns[provider]
        return None

    return remaining_seconds


def _record_provider_cooldown(*, provider: str, error_message: str) -> None:
    if provider == "injected" or not _is_rate_limit_error(error_message):
        return

    retry_seconds = _extract_retry_seconds(error_message) or 60
    _provider_cooldowns[provider] = datetime.now(UTC) + timedelta(seconds=retry_seconds)


def _is_rate_limit_error(error_message: str) -> bool:
    normalized_message = error_message.lower()
    return (
        "http 429" in normalized_message
        or "resource_exhausted" in normalized_message
        or "quota exceeded" in normalized_message
        or "rate limit" in normalized_message
    )


def _extract_retry_seconds(error_message: str) -> int | None:
    match = re.search(r"retry in ([0-9]+(?:\.[0-9]+)?)s", error_message, flags=re.IGNORECASE)
    if match is None:
        return None

    return max(int(float(match.group(1))), 1)
