from pathlib import Path

import pytest
from alembic import command
from sqlalchemy import inspect

from app.infrastructure.db.engine import create_database_engine, sqlite_database_url
from app.infrastructure.db.runtime import start_database_runtime
from app.infrastructure.db.migration_guard import DatabaseSchemaError, assert_schema_current, build_alembic_config


CANONICAL_TABLES = {
    "videos",
    "ingest_jobs",
    "ingest_attempts",
    "transcripts",
    "transcript_segments",
    "index_versions",
    "chunks",
    "chunk_segments",
}


def test_upgrade_and_downgrade_initial_schema(tmp_path: Path) -> None:
    database_url = sqlite_database_url(tmp_path / "migration.db")
    config = build_alembic_config(database_url)

    command.upgrade(config, "head")
    engine = create_database_engine(database_url)
    try:
        assert_schema_current(engine, config)
        command.check(config)
        assert CANONICAL_TABLES <= set(inspect(engine).get_table_names())
        with engine.connect() as connection:
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
            assert connection.exec_driver_sql("PRAGMA journal_mode").scalar_one().lower() == "wal"
    finally:
        engine.dispose()

    command.downgrade(config, "base")
    downgraded_engine = create_database_engine(database_url)
    try:
        assert CANONICAL_TABLES.isdisjoint(inspect(downgraded_engine).get_table_names())
    finally:
        downgraded_engine.dispose()


def test_schema_check_rejects_unmigrated_database(tmp_path: Path) -> None:
    database_url = sqlite_database_url(tmp_path / "unmigrated.db")
    engine = create_database_engine(database_url)
    try:
        with pytest.raises(DatabaseSchemaError, match="Run Alembic upgrade explicitly"):
            assert_schema_current(engine, build_alembic_config(database_url))
    finally:
        engine.dispose()


def test_database_runtime_refuses_to_start_with_stale_schema(tmp_path: Path) -> None:
    database_url = sqlite_database_url(tmp_path / "stale.db")

    with pytest.raises(DatabaseSchemaError, match="Database schema is not current"):
        start_database_runtime(database_url)
