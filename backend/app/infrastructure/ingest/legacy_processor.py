from collections.abc import Callable

from app.application.ingest.ports import IngestFailure, ProcessedVideo, ProcessVideoRequest
from app.domain.entities import IngestStage
from app.services.extraction.transcript_service import TranscriptFetchError, TranscriptNotFoundError
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
        try:
            response = ingest_video_content(request.canonical_url)
        except TranscriptNotFoundError as error:
            raise IngestFailure("TRANSCRIPT_NOT_FOUND", str(error), retryable=False) from error
        except TranscriptFetchError as error:
            raise IngestFailure("TRANSCRIPT_DOWNLOAD_FAILED", str(error), retryable=True) from error
        except ValueError as error:
            raise IngestFailure("INVALID_VIDEO_URL", str(error), retryable=False) from error

        if is_cancelled():
            raise IngestFailure("INGEST_CANCELLED", "Ingest was cancelled.", retryable=False)
        return ProcessedVideo(
            title=response.title,
            channel_title=response.channel_title,
            thumbnail_url=response.thumbnail_url,
            duration_ms=response.duration_seconds * 1000 if response.duration_seconds is not None else None,
        )
