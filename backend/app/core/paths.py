"""Canonical filesystem locations for backend-owned runtime data."""

from pathlib import Path

from sqlalchemy.engine import make_url


BACKEND_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = BACKEND_ROOT / "data"
DATABASE_PATH = DATA_DIR / "app.db"
VECTOR_STORE_DIR = DATA_DIR / "vector_store"
CHROMA_DIR = VECTOR_STORE_DIR / "chroma"
QDRANT_DIR = VECTOR_STORE_DIR / "qdrant"


def resolve_data_path(value: str | None, *, default: Path) -> Path:
    """Resolve a configured path without depending on the process working directory.

    Relative paths are backend-relative. A leading ``backend`` component is
    accepted for compatibility with older environment examples and removed so
    it can never produce ``backend/backend``.
    """

    if value is None or not value.strip():
        return default.resolve()

    path = Path(value.strip()).expanduser()
    if path.is_absolute():
        return path.resolve()

    parts = list(path.parts)
    while parts and parts[0].lower() == "backend":
        parts.pop(0)
    return BACKEND_ROOT.joinpath(*parts).resolve()


def resolve_database_url(value: str | None) -> str:
    """Make relative SQLite URLs independent of the current working directory."""

    if value is None or not value.strip():
        return f"sqlite:///{DATABASE_PATH.resolve().as_posix()}"

    url = make_url(value.strip())
    if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
        return value.strip()
    if url.database.startswith("file:"):
        return value.strip()

    database_path = resolve_data_path(url.database, default=DATABASE_PATH)
    return url.set(database=database_path.as_posix()).render_as_string(hide_password=False)
