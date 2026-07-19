from pathlib import Path

from sqlalchemy.engine import make_url

from app.core.paths import (
    BACKEND_ROOT,
    CHROMA_DIR,
    DATA_DIR,
    DATABASE_PATH,
    resolve_data_path,
    resolve_database_url,
)


def test_default_runtime_paths_share_one_backend_data_root() -> None:
    assert DATABASE_PATH == DATA_DIR / "app.db"
    assert CHROMA_DIR == DATA_DIR / "vector_store" / "chroma"
    assert DATA_DIR.parent == BACKEND_ROOT


def test_backend_prefixed_relative_path_never_duplicates_backend_directory() -> None:
    resolved = resolve_data_path("backend/data/vector_store/chroma", default=CHROMA_DIR)
    duplicated = Path("backend") / "backend" / "data"

    assert resolved == CHROMA_DIR.resolve()
    assert duplicated.as_posix() not in resolved.as_posix()


def test_repeated_backend_prefixes_are_normalized_for_legacy_configuration() -> None:
    resolved = resolve_data_path("backend/backend/data/vector_store/chroma", default=CHROMA_DIR)

    assert resolved == CHROMA_DIR.resolve()


def test_relative_sqlite_url_uses_canonical_database_path() -> None:
    resolved = make_url(resolve_database_url("sqlite:///backend/data/app.db"))

    assert Path(resolved.database or "") == DATABASE_PATH.resolve()


def test_non_sqlite_database_url_is_not_rewritten() -> None:
    url = "postgresql://localhost/video_qa"

    assert resolve_database_url(url) == url
