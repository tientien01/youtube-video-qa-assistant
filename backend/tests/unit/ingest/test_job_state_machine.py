from datetime import UTC, datetime

import pytest

from app.domain.entities import IngestJob, IngestJobStatus, IngestStage


def test_job_accepts_only_forward_running_transitions() -> None:
    job = IngestJob(video_id="video-id").start(now=datetime(2026, 7, 16, tzinfo=UTC))
    job = job.advance(IngestStage.FETCHING_TRANSCRIPT)

    with pytest.raises(ValueError, match="Invalid ingest stage transition"):
        job.advance(IngestStage.FETCHING_METADATA)

    with pytest.raises(ValueError, match="only after committing"):
        job.succeed()


def test_ready_job_is_terminal() -> None:
    job = IngestJob(video_id="video-id").start().advance(IngestStage.COMMITTING).succeed()

    assert job.status is IngestJobStatus.READY
    assert job.current_stage is IngestStage.COMPLETE
    with pytest.raises(ValueError, match="Cannot cancel"):
        job.cancel()


def test_only_retryable_failure_can_retry() -> None:
    job = IngestJob(video_id="video-id").fail(
        error_code="TRANSCRIPT_NOT_FOUND",
        error_message="Missing",
        retryable=False,
    )

    with pytest.raises(ValueError, match="retryable failed"):
        job.retry()
