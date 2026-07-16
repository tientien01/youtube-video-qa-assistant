import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BACKEND_ROOT = Path(__file__).resolve().parents[2]
LOCAL_ENV_FILE = BACKEND_ROOT / ".env"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_EMBEDDING_PROVIDER = "hashing"
DEFAULT_EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
DEFAULT_VECTOR_STORE_PROVIDER = "local_json"
DEFAULT_CHROMA_PERSIST_DIR = BACKEND_ROOT / "data" / "vector_store" / "chroma"
DEFAULT_DATABASE_PATH = BACKEND_ROOT / "data" / "app.db"


load_dotenv(LOCAL_ENV_FILE)


@dataclass(frozen=True)
class Settings:
    cors_origins: list[str]
    llm_provider: str
    gemini_api_key: str | None
    gemini_model: str
    llm_timeout_seconds: float
    embedding_provider: str
    embedding_model_name: str
    vector_store_provider: str
    chroma_persist_dir: Path
    reranker_enabled: bool
    rerank_top_k: int
    database_url: str


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
        gemini_api_key=gemini_api_key,
        gemini_model=_read_optional_env("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL,
        llm_timeout_seconds=_read_timeout_seconds("LLM_TIMEOUT_SECONDS", default=20.0),
        embedding_provider=(_read_optional_env("EMBEDDING_PROVIDER") or DEFAULT_EMBEDDING_PROVIDER).lower(),
        embedding_model_name=_read_optional_env("EMBEDDING_MODEL_NAME") or DEFAULT_EMBEDDING_MODEL_NAME,
        vector_store_provider=(_read_optional_env("VECTOR_STORE_PROVIDER") or DEFAULT_VECTOR_STORE_PROVIDER).lower(),
        chroma_persist_dir=_read_backend_path("CHROMA_PERSIST_DIR", default=DEFAULT_CHROMA_PERSIST_DIR),
        reranker_enabled=_read_bool("RERANKER_ENABLED", default=False),
        rerank_top_k=_read_positive_int("RERANK_TOP_K", default=8),
        database_url=_read_optional_env("DATABASE_URL") or f"sqlite:///{DEFAULT_DATABASE_PATH.resolve().as_posix()}",
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
    raw_value = _read_optional_env(name)
    if raw_value is None:
        return default

    path = Path(raw_value)
    if path.is_absolute():
        return path

    parts = path.parts
    if parts and parts[0].lower() == "backend":
        return BACKEND_ROOT.joinpath(*parts[1:])

    return BACKEND_ROOT / path
