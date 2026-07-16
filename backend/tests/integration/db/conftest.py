from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.db.engine import create_database_engine, create_session_factory, sqlite_database_url
from app.infrastructure.db.migration_guard import assert_schema_current, build_alembic_config


@pytest.fixture
def migrated_engine(tmp_path: Path) -> Iterator[Engine]:
    database_url = sqlite_database_url(tmp_path / "app.db")
    config = build_alembic_config(database_url)
    command.upgrade(config, "head")
    engine = create_database_engine(database_url)
    assert_schema_current(engine, config)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def session_factory(migrated_engine: Engine) -> sessionmaker[Session]:
    return create_session_factory(migrated_engine)
