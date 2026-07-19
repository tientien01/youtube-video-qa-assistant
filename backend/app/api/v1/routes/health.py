from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import text

from app.api.contracts.runtime import RuntimeComponentResponse, RuntimeHealthResponse
from app.api.dependencies import get_database_runtime
from app.core.config import Settings, get_settings
from app.core.paths import BACKEND_ROOT, VECTOR_STORE_DIR
from app.infrastructure.db.runtime import DatabaseRuntime
from app.infrastructure.llm.factory import LlmProviderConfig, create_llm_provider
from app.infrastructure.vector.legacy import vector_store


router = APIRouter(tags=["health"])


@router.get("/health", response_model=RuntimeHealthResponse)
def health_check(database: DatabaseRuntime = Depends(get_database_runtime)) -> RuntimeHealthResponse:
    settings = get_settings()
    sqlite_available = _database_available(database)
    vector_available = vector_store.health_check()
    llm_available = _llm_available(settings)
    operational = sqlite_available and vector_available and llm_available
    return RuntimeHealthResponse(
        status="operational" if operational else "degraded",
        api=RuntimeComponentResponse(status="available", label="API"),
        sqlite=RuntimeComponentResponse(
            status="available" if sqlite_available else "unavailable",
            label="SQLite",
            detail=_database_detail(database),
        ),
        vector_index=RuntimeComponentResponse(
            status="available" if vector_available else "unavailable",
            label="Vector index",
            provider=settings.vector_store_provider,
            detail=_vector_index_detail(settings),
        ),
        llm=RuntimeComponentResponse(
            status="available" if llm_available else "unavailable",
            label="LLM",
            provider=settings.llm_provider,
            model=settings.llm_model,
            detail=None if llm_available else "Configured provider did not pass its live health check.",
        ),
        database_size_bytes=_database_size(database),
    )


def _database_available(database: DatabaseRuntime) -> bool:
    try:
        with database.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        return False
    return True


def _llm_available(settings: Settings) -> bool:
    if settings.llm_provider in {"fallback", "none"}:
        return False
    try:
        provider = create_llm_provider(
            LlmProviderConfig(
                provider=settings.llm_provider,
                model=settings.llm_model,
                base_url=settings.ollama_base_url,
                timeout_seconds=min(settings.llm_timeout_seconds, 3.0),
                context_window=settings.llm_context_window,
                keep_alive=settings.ollama_keep_alive,
                gemini_api_key=settings.gemini_api_key,
            )
        )
        return provider.health_check()
    except (RuntimeError, ValueError):
        return False


def _database_size(database: DatabaseRuntime) -> int | None:
    path = database.engine.url.database
    if not path:
        return None
    try:
        return Path(path).stat().st_size
    except OSError:
        return None


def _database_detail(database: DatabaseRuntime) -> str | None:
    path = database.engine.url.database
    if not path:
        return None
    return f"Canonical: {_display_runtime_path(Path(path))}"


def _vector_index_detail(settings: Settings) -> str | None:
    if settings.vector_store_provider in {"local", "local_json"}:
        path = VECTOR_STORE_DIR / "local_vector_index.json"
    elif settings.vector_store_provider == "chroma":
        path = settings.chroma_persist_dir
    else:
        return None
    return f"Derived: {_display_runtime_path(path)}"


def _display_runtime_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(BACKEND_ROOT.parent)
    except ValueError:
        return resolved.name
    return relative.as_posix()
