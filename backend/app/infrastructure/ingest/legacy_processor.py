from collections.abc import Callable

from app.application.ingest.ports import IngestAttemptReport, IngestFailure, ProcessedVideo, ProcessVideoRequest
from app.application.ingest.transcript import TranscriptAcquisitionError
from app.domain.entities import IngestStage
from app.services.rag.video_index_service import ingest_video_content


class LegacyIngestProcessor:
    """Temporary adapter around the opaque pre-TASK-003 ingest pipeline."""

    name = "legacy_ingest"

    def process(
        self,
        request: ProcessVideoRequest,
        *,
        report_stage: Callable[[IngestStage], None],
        is_cancelled: Callable[[], bool],
    ) -> ProcessedVideo:
        if is_cancelled():
            raise IngestFailure("INGEST_CANCELLED", "Ingest was cancelled.", retryable=False)
        report_stage(IngestStage.FETCHING_TRANSCRIPT)
        attempts: list[IngestAttemptReport] = []
        try:
            response = ingest_video_content(
                request.canonical_url,
                transcript_attempt_collector=attempts.extend,
            )
        except TranscriptAcquisitionError as error:
            raise IngestFailure(
                error.code.value,
                str(error),
                retryable=error.retryable,
                attempts=error.attempts,
            ) from error
        except ValueError as error:
            raise IngestFailure("INVALID_VIDEO_URL", str(error), retryable=False) from error

        if is_cancelled():
            raise IngestFailure("INGEST_CANCELLED", "Ingest was cancelled.", retryable=False)
        return ProcessedVideo(
            title=response.title,
            channel_title=response.channel_title,
            thumbnail_url=response.thumbnail_url,
            duration_ms=response.duration_seconds * 1000 if response.duration_seconds is not None else None,
            attempts=tuple(attempts),
        )
