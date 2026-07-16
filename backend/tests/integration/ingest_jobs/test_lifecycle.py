from collections.abc import Callable
from dataclasses import replace

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.application.ingest.ports import IngestFailure, ProcessedVideo, ProcessVideoRequest
from app.application.ingest.use_cases import IngestJobApplication
from app.domain.entities import IngestJobStatus, IngestStage, Video, VideoStatus
from app.infrastructure.db.unit_of_work import SqlAlchemyIngestUnitOfWork


VIDEO_URL = "https://youtu.be/dQw4w9WgXcQ"


class FakeProcessor:
    name = "fake"

    def __init__(self, failure: IngestFailure | None = None) -> None:
        self.failure = failure
        self.calls = 0

    def process(
        self,
        request: ProcessVideoRequest,
        *,
        report_stage: Callable[[IngestStage], None],
        is_cancelled: Callable[[], bool],
    ) -> ProcessedVideo:
        self.calls += 1
        assert request.video_id == "dQw4w9WgXcQ"
        assert not is_cancelled()
        report_stage(IngestStage.FETCHING_TRANSCRIPT)
        if self.failure is not None:
            raise self.failure
        report_stage(IngestStage.CHUNKING)
        report_stage(IngestStage.EMBEDDING)
        return ProcessedVideo(title="Persistent video", duration_ms=12_000)


def _application(
    session_factory: sessionmaker[Session],
    processor: FakeProcessor,
) -> IngestJobApplication:
    return IngestJobApplication(
        lambda: SqlAlchemyIngestUnitOfWork(session_factory),
        processor,
        target_fingerprint="test-pipeline-v1",
    )


def test_duplicate_create_reuses_job_and_success_is_persistent(
    session_factory: sessionmaker[Session],
) -> None:
    processor = FakeProcessor()
    application = _application(session_factory, processor)

    first = application.create(VIDEO_URL)
    duplicate = application.create("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert duplicate.id == first.id

    application.execute(first.id)
    completed = application.get(first.id)
    assert completed.status is IngestJobStatus.READY
    assert completed.current_stage is IngestStage.COMPLETE
    assert processor.calls == 1

    restarted = _application(session_factory, FakeProcessor())
    assert restarted.create(VIDEO_URL).id == first.id
    with SqlAlchemyIngestUnitOfWork(session_factory) as uow:
        video = uow.videos.get(first.video_id)
        assert video is not None
        assert video.status is VideoStatus.READY
        assert video.title == "Persistent video"
        assert len(uow.jobs.list_attempts(first.id)) == 1


def test_failure_is_diagnosable_and_can_be_retried(session_factory: sessionmaker[Session]) -> None:
    processor = FakeProcessor(IngestFailure("TRANSCRIPT_DOWNLOAD_FAILED", "Timed out", retryable=True))
    application = _application(session_factory, processor)
    job = application.create(VIDEO_URL)

    application.execute(job.id)
    failed = application.get(job.id)
    assert failed.status is IngestJobStatus.FAILED
    assert failed.current_stage is IngestStage.FETCHING_TRANSCRIPT
    assert failed.error_code == "TRANSCRIPT_DOWNLOAD_FAILED"
    assert failed.retryable

    processor.failure = None
    retried = application.retry(job.id)
    assert retried.status is IngestJobStatus.PENDING
    application.execute(job.id)
    assert application.get(job.id).status is IngestJobStatus.READY


def test_cancelled_job_cannot_publish(session_factory: sessionmaker[Session]) -> None:
    application = _application(session_factory, FakeProcessor())
    job = application.create(VIDEO_URL)

    cancelled = application.cancel(job.id)
    application.execute(job.id)

    assert cancelled.status is IngestJobStatus.CANCELLED
    assert application.get(job.id).status is IngestJobStatus.CANCELLED
    with SqlAlchemyIngestUnitOfWork(session_factory) as uow:
        video = uow.videos.get(job.video_id)
        assert video is not None
        assert video.status is VideoStatus.PENDING


def test_restart_marks_running_job_interrupted(session_factory: sessionmaker[Session]) -> None:
    application = _application(session_factory, FakeProcessor())
    job = application.create(VIDEO_URL)
    with SqlAlchemyIngestUnitOfWork(session_factory) as uow:
        uow.jobs.save(job.start())
        video = uow.videos.get(job.video_id)
        assert video is not None
        uow.videos.save(replace(video, status=VideoStatus.PROCESSING))
        uow.commit()

    restarted = _application(session_factory, FakeProcessor())
    assert restarted.recover_interrupted() == 1
    recovered = restarted.get(job.id)
    assert recovered.status is IngestJobStatus.FAILED
    assert recovered.error_code == "INGEST_PROCESS_INTERRUPTED"
    assert recovered.retryable


class _RejectReadyRepository:
    def __init__(self, wrapped) -> None:
        self._wrapped = wrapped

    def __getattr__(self, name: str):
        return getattr(self._wrapped, name)

    def save(self, job):
        if job.status is IngestJobStatus.READY:
            raise RuntimeError("simulated publish failure")
        return self._wrapped.save(job)


class _RejectReadyUnitOfWork(SqlAlchemyIngestUnitOfWork):
    def __enter__(self):
        entered = super().__enter__()
        self.jobs = _RejectReadyRepository(self.jobs)
        return entered


def test_publish_failure_rolls_back_and_preserves_last_ready_video(
    session_factory: sessionmaker[Session],
) -> None:
    with SqlAlchemyIngestUnitOfWork(session_factory) as uow:
        existing = uow.videos.add(
            Video(
                youtube_video_id="dQw4w9WgXcQ",
                canonical_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                title="Last ready title",
                status=VideoStatus.READY,
            )
        )
        uow.commit()

    application = IngestJobApplication(
        lambda: _RejectReadyUnitOfWork(session_factory),
        FakeProcessor(),
        target_fingerprint="test-pipeline-v1",
    )
    job = application.create(VIDEO_URL)

    with pytest.raises(RuntimeError, match="simulated publish failure"):
        application.execute(job.id)

    assert application.get(job.id).status is IngestJobStatus.FAILED
    with SqlAlchemyIngestUnitOfWork(session_factory) as uow:
        video = uow.videos.get(existing.id)
        assert video is not None
        assert video.status is VideoStatus.READY
        assert video.title == "Last ready title"
