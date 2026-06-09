from dataclasses import dataclass

from app.core.config import get_settings


@dataclass(frozen=True)
class LlmSettings:
    provider: str
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
        gemini_api_key=settings.gemini_api_key,
        gemini_model=settings.gemini_model,
        timeout_seconds=settings.llm_timeout_seconds,
    )
