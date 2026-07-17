from dataclasses import dataclass

from app.core.config import get_settings


@dataclass(frozen=True)
class LlmSettings:
    provider: str
    model: str
    ollama_base_url: str
    gemini_api_key: str | None
    gemini_model: str
    timeout_seconds: float

    @property
    def is_gemini_enabled(self) -> bool:
        return self.provider == "gemini" and bool(self.gemini_api_key)


def load_llm_settings() -> LlmSettings:
    settings = get_settings()

    return LlmSettings(
        provider=settings.llm_provider,
        model=settings.llm_model,
        ollama_base_url=settings.ollama_base_url,
        gemini_api_key=settings.gemini_api_key,
        gemini_model=settings.gemini_model,
        timeout_seconds=settings.llm_timeout_seconds,
    )
