import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BACKEND_ROOT = Path(__file__).resolve().parents[2]
LOCAL_ENV_FILE = BACKEND_ROOT / ".env"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"


load_dotenv(LOCAL_ENV_FILE)


@dataclass(frozen=True)
class Settings:
    llm_provider: str
    gemini_api_key: str | None
    gemini_model: str
    llm_timeout_seconds: float


def get_settings() -> Settings:
    gemini_api_key = _read_optional_env("GEMINI_API_KEY")
    provider = _read_optional_env("LLM_PROVIDER")
    if provider is None:
        provider = "gemini" if gemini_api_key else "fallback"
    provider = provider.lower()
    if provider == "gemini" and not gemini_api_key:
        provider = "fallback"

    return Settings(
        llm_provider=provider,
        gemini_api_key=gemini_api_key,
        gemini_model=_read_optional_env("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL,
        llm_timeout_seconds=_read_timeout_seconds("LLM_TIMEOUT_SECONDS", default=20.0),
    )


def _read_optional_env(name: str) -> str | None:
    value = os.environ.get(name)
    if value is None:
        return None

    stripped_value = value.strip()
    return stripped_value or None


def _read_timeout_seconds(name: str, *, default: float) -> float:
    raw_value = _read_optional_env(name)
    if raw_value is None:
        return default

    try:
        return max(float(raw_value), 1.0)
    except ValueError:
        return default
