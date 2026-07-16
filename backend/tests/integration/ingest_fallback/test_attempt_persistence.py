from collections.abc import Callable

from sqlalchemy.orm import Session, sessionmaker

from app.application.ingest.ports import IngestAttemptReport, ProcessedVideo, ProcessVideoRequest
from app.application.ingest.use_cases import IngestJobApplication
from app.domain.entities import AttemptOutcome, IngestStage
from app.infrastructure.db.unit_of_work import SqlAlchemyIngestUnitOfWork


class FallbackProcessor:
    name = "fallback_pipeline"

    def process(
        self,
        request: ProcessVideoRequest,
        *,
        report_stage: Callable[[IngestStage], None],
        is_cancelled: Callable[[], bool],
    ) -> ProcessedVideo:
        report_stage(IngestStage.FETCHING_TRANSCRIPT)
        return ProcessedVideo(
            title=request.video_id,
            attempts=(
                IngestAttemptReport(
                    provider="youtube_transcript_api",
                    stage=IngestStage.FETCHING_TRANSCRIPT,
                    outcome=AttemptOutcome.FAILED,
                    elapsed_ms=12,
                    error_code="TRANSCRIPT_PROVIDER_BLOCKED",
                    error_message="Provider was blocked.",
                ),
                IngestAttemptReport(
                    provider="yt_dlp_manual",
                    stage=IngestStage.FETCHING_TRANSCRIPT,
                    outcome=AttemptOutcome.SUCCEEDED,
                    elapsed_ms=8,
                ),
            ),
        )


def test_provider_fallback_attempts_are_persisted_in_execution_order(
    session_factory: sessionmaker[Session],
) -> None:
    application = IngestJobApplication(
        lambda: SqlAlchemyIngestUnitOfWork(session_factory),
        FallbackProcessor(),
        target_fingerprint="fallback-v1",
    )
    job = application.create("https://youtu.be/dQw4w9WgXcQ")
    application.execute(job.id)

    with SqlAlchemyIngestUnitOfWork(session_factory) as uow:
        attempts = uow.jobs.list_attempts(job.id)

    assert [attempt.provider for attempt in attempts] == [
        "youtube_transcript_api",
        "yt_dlp_manual",
        "fallback_pipeline",
    ]
    assert attempts[0].error_code == "TRANSCRIPT_PROVIDER_BLOCKED"
    assert attempts[1].outcome is AttemptOutcome.SUCCEEDED
