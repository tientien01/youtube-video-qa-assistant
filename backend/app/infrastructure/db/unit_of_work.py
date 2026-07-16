from __future__ import annotations

from types import TracebackType

from sqlalchemy.orm import Session, sessionmaker

from app.application.ports.repositories import IngestJobRepository, VideoRepository
from app.infrastructure.db.repositories import SqlAlchemyIngestJobRepository, SqlAlchemyVideoRepository


class SqlAlchemyIngestUnitOfWork:
    videos: VideoRepository
    jobs: IngestJobRepository

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._session: Session | None = None
        self._committed = False

    def __enter__(self) -> SqlAlchemyIngestUnitOfWork:
        self._session = self._session_factory()
        self.videos = SqlAlchemyVideoRepository(self._session)
        self.jobs = SqlAlchemyIngestJobRepository(self._session)
        return self

    def commit(self) -> None:
        if self._session is None:
            raise RuntimeError("Unit of work has not been entered.")
        self._session.commit()
        self._committed = True

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._session is None:
            return
        if exc_type is not None or not self._committed:
            self._session.rollback()
        self._session.close()
        self._session = None
        self._committed = False
