from dataclasses import dataclass

import httpx

from app.application.llm.contracts import LlmProvider
from app.infrastructure.llm.gemini import GeminiLlmProvider
from app.infrastructure.llm.ollama import OllamaLlmProvider


class LlmConfigurationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class LlmProviderConfig:
    provider: str = "ollama"
    model: str = "qwen3:4b"
    base_url: str = "http://127.0.0.1:11434"
    timeout_seconds: float = 120.0
    context_window: int = 8_192
    keep_alive: str = "30m"
    gemini_api_key: str | None = None


def create_llm_provider(
    config: LlmProviderConfig,
    *,
    client: httpx.Client | None = None,
) -> LlmProvider:
    provider = config.provider.casefold().strip()
    if provider == "ollama":
        return OllamaLlmProvider(
            model=config.model,
            base_url=config.base_url,
            timeout_seconds=config.timeout_seconds,
            context_window=config.context_window,
            keep_alive=config.keep_alive,
            client=client,
        )
    if provider == "gemini":
        if not config.gemini_api_key:
            raise LlmConfigurationError("Gemini was selected explicitly but GEMINI_API_KEY is missing.")
        return GeminiLlmProvider(
            api_key=config.gemini_api_key,
            model=config.model,
            timeout_seconds=config.timeout_seconds,
            client=client,
        )
    raise LlmConfigurationError(f"Unsupported LLM provider: {config.provider!r}.")
