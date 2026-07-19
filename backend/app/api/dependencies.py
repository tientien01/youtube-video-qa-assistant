from __future__ import annotations

from dataclasses import dataclass
from threading import Lock

from app.application.ingest.use_cases import IngestJobApplication
from app.application.video import VideoLibraryApplication, VideoTranscriptApplication
from app.application.legacy.rag.local_store import rag_store
from app.application.legacy.rag.video_index_service import delete_legacy_video_data
from app.core.config import get_settings
from app.infrastructure.db.migration_guard import DatabaseSchemaError
from app.infrastructure.db.runtime import DatabaseRuntime, start_database_runtime
from app.infrastructure.db.unit_of_work import SqlAlchemyIngestUnitOfWork
from app.infrastructure.ingest.in_process_runner import InProcessIngestJobRunner
from app.infrastructure.ingest.local_processor import LocalIngestProcessor
from app.infrastructure.ingest.transcript.runtime import transcript_pipeline_fingerprint


@dataclass(slots=True)
class _IngestContainer:
    application: IngestJobApplication
    runner: InProcessIngestJobRunner
    database: DatabaseRuntime


_container: _IngestContainer | None = None
_container_lock = Lock()


def get_ingest_application() -> IngestJobApplication:
    global _container
    if _container is not None:
        return _container.application
    with _container_lock:
        if _container is None:
            settings = get_settings()
            database = start_database_runtime(settings.database_url)

            def uow_factory() -> SqlAlchemyIngestUnitOfWork:
                return SqlAlchemyIngestUnitOfWork(database.session_factory)

            application = IngestJobApplication(
                uow_factory,
                LocalIngestProcessor(),
                target_fingerprint=transcript_pipeline_fingerprint(),
            )
            application.recover_interrupted()
            runner = InProcessIngestJobRunner(application.execute)
            application.attach_runner(runner)
            _container = _IngestContainer(application=application, runner=runner, database=database)
    return _container.application


def get_database_runtime() -> DatabaseRuntime:
    get_ingest_application()
    assert _container is not None
    return _container.database


def get_video_transcript_application() -> VideoTranscriptApplication:
    database = get_database_runtime()
    return VideoTranscriptApplication(lambda: SqlAlchemyIngestUnitOfWork(database.session_factory))


def get_video_library_application() -> VideoLibraryApplication:
    database = get_database_runtime()
    return VideoLibraryApplication(
        lambda: SqlAlchemyIngestUnitOfWork(database.session_factory),
        legacy_chunk_count=rag_store.get_video_chunk_count,
        delete_legacy_data=delete_legacy_video_data,
    )


def close_ingest_runtime() -> None:
    global _container
    with _container_lock:
        if _container is not None:
            _container.runner.shutdown()
            _container.database.close()
            _container = None


__all__ = [
    "DatabaseSchemaError",
    "close_ingest_runtime",
    "get_database_runtime",
    "get_ingest_application",
    "get_video_library_application",
    "get_video_transcript_application",
]
