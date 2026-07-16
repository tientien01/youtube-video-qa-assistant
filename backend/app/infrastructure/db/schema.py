from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Engine


class DatabaseSchemaError(RuntimeError):
    """Raised when the database is not migrated to the expected revision."""


def build_alembic_config(database_url: str | None = None) -> Config:
    backend_root = Path(__file__).resolve().parents[3]
    config = Config(str(backend_root / "alembic.ini"))
    if database_url is not None:
        config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


def assert_schema_current(engine: Engine, config: Config | None = None) -> None:
    alembic_config = config or build_alembic_config(str(engine.url))
    expected_revision = ScriptDirectory.from_config(alembic_config).get_current_head()
    with engine.connect() as connection:
        current_revision = MigrationContext.configure(connection).get_current_revision()

    if current_revision != expected_revision:
        raise DatabaseSchemaError(
            "Database schema is not current: "
            f"expected revision {expected_revision!r}, found {current_revision!r}. "
            "Run Alembic upgrade explicitly before starting the database-backed runtime."
        )
