from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.db.engine import create_database_engine, create_session_factory, sqlite_database_url
from app.infrastructure.db.migration_guard import build_alembic_config


@pytest.fixture
def session_factory(tmp_path: Path) -> Iterator[sessionmaker[Session]]:
    database_url = sqlite_database_url(tmp_path / "fallback.db")
    command.upgrade(build_alembic_config(database_url), "head")
    engine: Engine = create_database_engine(database_url)
    try:
        yield create_session_factory(engine)
    finally:
        engine.dispose()
