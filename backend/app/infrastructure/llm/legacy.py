"""Composition bridge for callers migrating from text-only generation."""

from app.application.legacy.llm.base import LlmClient, LlmError
from app.application.llm.contracts import GenerationOptions, GenerationRequest, LlmError as ProviderError, LlmMessage
from app.core.config import Settings
from app.infrastructure.llm.factory import LlmConfigurationError, LlmProviderConfig, create_llm_provider


def create_legacy_llm_client(settings: Settings) -> LlmClient | None:
    if settings.llm_provider in {"fallback", "none"}:
        return None
    try:
        provider = create_llm_provider(
            LlmProviderConfig(
                provider=settings.llm_provider,
                model=settings.llm_model,
                base_url=settings.ollama_base_url,
                timeout_seconds=settings.llm_timeout_seconds,
                context_window=settings.llm_context_window,
                keep_alive=settings.ollama_keep_alive,
                gemini_api_key=settings.gemini_api_key,
            )
        )
    except LlmConfigurationError:
        return None
    return _ProviderClient(provider, timeout_seconds=settings.llm_timeout_seconds)


class _ProviderClient:
    def __init__(self, provider, *, timeout_seconds: float) -> None:
        self._provider = provider
        self._timeout_seconds = timeout_seconds

    def generate_text(self, prompt: str) -> str:
        try:
            return self._provider.generate(
                GenerationRequest(
                    messages=(LlmMessage("user", prompt),),
                    options=GenerationOptions(timeout_seconds=self._timeout_seconds),
                )
            ).text
        except ProviderError as error:
            raise LlmError(str(error)) from error
