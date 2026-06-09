import logging
from dataclasses import dataclass

from app.services.llm.base import LlmClient, LlmError
from app.services.llm.config import load_llm_settings
from app.services.llm.gemini_client import GeminiClient


logger = logging.getLogger(__name__)


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
