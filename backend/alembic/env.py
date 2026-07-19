from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.infrastructure.db.models import Base
from app.core.paths import resolve_database_url


config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _include_object(object_, name: str | None, type_: str, reflected: bool, compare_to) -> bool:
    del object_, reflected, compare_to
    # FTS5 and its shadow tables are managed by the explicit migration because
    # SQLAlchemy metadata cannot represent SQLite virtual tables and triggers.
    return not (type_ == "table" and name is not None and name.startswith("chunk_fts"))


def _database_url() -> str:
    configured_url = config.get_main_option("sqlalchemy.url").strip()
    if configured_url:
        return resolve_database_url(configured_url)

    environment_url = os.environ.get("DATABASE_URL", "").strip()
    if environment_url:
        return resolve_database_url(environment_url)

    return resolve_database_url(None)


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        render_as_batch=True,
        dialect_opts={"paramstyle": "named"},
        include_object=_include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _database_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        if connection.dialect.name == "sqlite":
            connection.exec_driver_sql("PRAGMA foreign_keys = ON")
            connection.exec_driver_sql("PRAGMA journal_mode = WAL")
            # SQLAlchemy 2 starts an implicit transaction for driver SQL. Commit
            # the PRAGMA setup so Alembic owns and commits the revision transaction.
            connection.commit()
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_as_batch=connection.dialect.name == "sqlite",
            include_object=_include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
