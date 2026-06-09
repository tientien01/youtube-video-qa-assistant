import logging

from app.services.llm.base import LlmClient, LlmError
from app.services.llm.config import load_llm_settings
from app.services.llm.gemini_client import GeminiClient


logger = logging.getLogger(__name__)


def generate_optional_llm_text(
    prompt: str,
    *,
    llm_client: LlmClient | None = None,
    fallback_log_message: str,
) -> str | None:
    client = llm_client or build_configured_llm_client()
    if client is None:
        return None

    try:
        generated_text = client.generate_text(prompt).strip()
    except LlmError as error:
        logger.warning("%s: %s", fallback_log_message, error)
        return None

    if not generated_text:
        logger.warning("%s: empty LLM response", fallback_log_message)
        return None

    return generated_text


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
