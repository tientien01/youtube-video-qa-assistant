from dataclasses import dataclass

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.db.engine import create_database_engine, create_session_factory
from app.infrastructure.db.migration_guard import assert_schema_current


@dataclass(frozen=True, slots=True)
class DatabaseRuntime:
    engine: Engine
    session_factory: sessionmaker[Session]

    def close(self) -> None:
        self.engine.dispose()


def start_database_runtime(database_url: str, *, echo: bool = False) -> DatabaseRuntime:
    """Open a migrated database or fail without mutating its schema."""

    engine = create_database_engine(database_url, echo=echo)
    try:
        assert_schema_current(engine)
    except Exception:
        engine.dispose()
        raise
    return DatabaseRuntime(engine=engine, session_factory=create_session_factory(engine))
