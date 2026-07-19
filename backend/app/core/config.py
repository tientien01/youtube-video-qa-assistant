import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from app.core.paths import BACKEND_ROOT, CHROMA_DIR, resolve_data_path, resolve_database_url


LOCAL_ENV_FILE = BACKEND_ROOT / ".env"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_OLLAMA_LLM_MODEL = "qwen3:4b"
DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_EMBEDDING_MODEL = "embeddinggemma"
DEFAULT_OLLAMA_CONTEXT_WINDOW = 8_192
DEFAULT_OLLAMA_KEEP_ALIVE = "30m"
DEFAULT_LLM_TIMEOUT_SECONDS = 120.0
DEFAULT_EMBEDDING_PROVIDER = "hashing"
DEFAULT_EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
DEFAULT_VECTOR_STORE_PROVIDER = "local_json"
DEFAULT_CHROMA_PERSIST_DIR = CHROMA_DIR
DEFAULT_TRANSCRIPT_PROVIDER_ORDER = (
    "youtube_transcript_api",
    "yt_dlp_manual",
    "yt_dlp_automatic",
)
DEFAULT_TRANSCRIPT_LANGUAGES = ("vi", "en")


load_dotenv(LOCAL_ENV_FILE)


@dataclass(frozen=True)
class Settings:
    cors_origins: list[str]
    llm_provider: str
    llm_model: str
    ollama_base_url: str
    ollama_keep_alive: str
    gemini_api_key: str | None
    gemini_model: str
    llm_timeout_seconds: float
    llm_context_window: int
    embedding_provider: str
    embedding_model_name: str
    vector_store_provider: str
    chroma_persist_dir: Path
    reranker_enabled: bool
    rerank_top_k: int
    database_url: str
    transcript_provider_order: tuple[str, ...]
    transcript_preferred_languages: tuple[str, ...]
    transcript_connect_timeout_seconds: float
    transcript_read_timeout_seconds: float
    transcript_max_attempts_per_provider: int


def get_settings() -> Settings:
    gemini_api_key = _read_optional_env("GEMINI_API_KEY")
    provider = _read_optional_env("LLM_PROVIDER")
    if provider is None:
        provider = "gemini" if gemini_api_key else "fallback"
    provider = provider.lower()
    if provider == "gemini" and not gemini_api_key:
        provider = "fallback"

    return Settings(
        cors_origins=_read_list_env(
            "CORS_ORIGINS",
            default=[
                "http://localhost:5173",
                "http://127.0.0.1:5173",
            ],
        ),
        llm_provider=provider,
        llm_model=(
            _read_optional_env("LLM_MODEL")
            or (_read_optional_env("GEMINI_MODEL") if provider == "gemini" else None)
            or (DEFAULT_GEMINI_MODEL if provider == "gemini" else DEFAULT_OLLAMA_LLM_MODEL)
        ),
        ollama_base_url=_read_optional_env("OLLAMA_BASE_URL") or DEFAULT_OLLAMA_BASE_URL,
        ollama_keep_alive=_read_optional_env("OLLAMA_KEEP_ALIVE") or DEFAULT_OLLAMA_KEEP_ALIVE,
        gemini_api_key=gemini_api_key,
        gemini_model=_read_optional_env("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL,
        llm_timeout_seconds=_read_timeout_seconds("LLM_TIMEOUT_SECONDS", default=DEFAULT_LLM_TIMEOUT_SECONDS),
        llm_context_window=_read_positive_int("LLM_CONTEXT_WINDOW", default=DEFAULT_OLLAMA_CONTEXT_WINDOW),
        embedding_provider=(_read_optional_env("EMBEDDING_PROVIDER") or DEFAULT_EMBEDDING_PROVIDER).lower(),
        embedding_model_name=(
            _read_optional_env("EMBEDDING_MODEL")
            or _read_optional_env("EMBEDDING_MODEL_NAME")
            or (
                DEFAULT_OLLAMA_EMBEDDING_MODEL
                if (_read_optional_env("EMBEDDING_PROVIDER") or DEFAULT_EMBEDDING_PROVIDER).lower() == "ollama"
                else DEFAULT_EMBEDDING_MODEL_NAME
            )
        ),
        vector_store_provider=(_read_optional_env("VECTOR_STORE_PROVIDER") or DEFAULT_VECTOR_STORE_PROVIDER).lower(),
        chroma_persist_dir=_read_backend_path("CHROMA_PERSIST_DIR", default=DEFAULT_CHROMA_PERSIST_DIR),
        reranker_enabled=_read_bool("RERANKER_ENABLED", default=False),
        rerank_top_k=_read_positive_int("RERANK_TOP_K", default=8),
        database_url=resolve_database_url(_read_optional_env("DATABASE_URL")),
        transcript_provider_order=tuple(
            _read_list_env("TRANSCRIPT_PROVIDER_ORDER", default=list(DEFAULT_TRANSCRIPT_PROVIDER_ORDER))
        ),
        transcript_preferred_languages=tuple(
            _read_list_env("TRANSCRIPT_PREFERRED_LANGUAGES", default=list(DEFAULT_TRANSCRIPT_LANGUAGES))
        ),
        transcript_connect_timeout_seconds=_read_timeout_seconds("TRANSCRIPT_CONNECT_TIMEOUT_SECONDS", default=5.0),
        transcript_read_timeout_seconds=_read_timeout_seconds("TRANSCRIPT_READ_TIMEOUT_SECONDS", default=20.0),
        transcript_max_attempts_per_provider=_read_positive_int("TRANSCRIPT_MAX_ATTEMPTS", default=2),
    )


def _read_optional_env(name: str) -> str | None:
    value = os.environ.get(name)
    if value is None:
        return None

    stripped_value = value.strip()
    return stripped_value or None


def _read_list_env(name: str, *, default: list[str]) -> list[str]:
    raw_value = _read_optional_env(name)
    if raw_value is None:
        return default

    values = [item.strip() for item in raw_value.split(",") if item.strip()]
    return values or default


def _read_timeout_seconds(name: str, *, default: float) -> float:
    raw_value = _read_optional_env(name)
    if raw_value is None:
        return default

    try:
        return max(float(raw_value), 1.0)
    except ValueError:
        return default


def _read_bool(name: str, *, default: bool) -> bool:
    raw_value = _read_optional_env(name)
    if raw_value is None:
        return default

    return raw_value.lower() in {"1", "true", "yes", "on"}


def _read_positive_int(name: str, *, default: int) -> int:
    raw_value = _read_optional_env(name)
    if raw_value is None:
        return default

    try:
        return max(int(raw_value), 1)
    except ValueError:
        return default


def _read_backend_path(name: str, *, default: Path) -> Path:
    return resolve_data_path(_read_optional_env(name), default=default)
