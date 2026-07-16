from collections.abc import Callable

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.application.ingest.normalization import normalize_transcript
from app.application.ingest.ports import ProcessedVideo, ProcessVideoRequest
from app.application.ingest.transcript import SourceTranscriptSegment, SubtitleFormat, TranscriptDocument
from app.application.ingest.use_cases import IngestJobApplication
from app.domain.entities import IngestStage, TranscriptType
from app.infrastructure.db.models import TranscriptModel, TranscriptSegmentModel
from app.infrastructure.db.unit_of_work import SqlAlchemyIngestUnitOfWork


VIDEO_URL = "https://youtu.be/dQw4w9WgXcQ"


def _publication(text: str = "Canonical transcript"):
    return normalize_transcript(
        TranscriptDocument(
            provider="fixture",
            provider_version="1.2.3",
            language_code="en",
            transcript_type=TranscriptType.MANUAL,
            source_format=SubtitleFormat.VTT,
            segments=(SourceTranscriptSegment(text, 0, 1_000),),
        )
    )


class _Processor:
    name = "canonical_fixture"

    def __init__(self, transcript=None) -> None:
        self.transcript = transcript or _publication()

    def process(
        self,
        request: ProcessVideoRequest,
        *,
        report_stage: Callable[[IngestStage], None],
        is_cancelled: Callable[[], bool],
    ) -> ProcessedVideo:
        report_stage(IngestStage.FETCHING_TRANSCRIPT)
        report_stage(IngestStage.NORMALIZING)
        report_stage(IngestStage.VALIDATING)
        return ProcessedVideo(title="Canonical video", transcript=self.transcript)


def _application(session_factory, fingerprint: str, uow=SqlAlchemyIngestUnitOfWork, transcript=None):
    return IngestJobApplication(
        lambda: uow(session_factory),
        _Processor(transcript),
        target_fingerprint=fingerprint,
    )


def test_canonical_transcript_and_stable_segments_are_published_once(
    session_factory: sessionmaker[Session],
) -> None:
    first = _application(session_factory, "pipeline-v1")
    first_job = first.create(VIDEO_URL)
    first.execute(first_job.id)

    with SqlAlchemyIngestUnitOfWork(session_factory) as uow:
        active = uow.transcripts.get_active(first_job.video_id)
        assert active is not None
        assert active.quality_diagnostics["canonical_segment_count"] == 1
        first_segments = uow.transcripts.list_segments(active.id)

    equivalent = _application(session_factory, "pipeline-v2")
    equivalent_job = equivalent.create(VIDEO_URL)
    equivalent.execute(equivalent_job.id)

    with SqlAlchemyIngestUnitOfWork(session_factory) as uow:
        current = uow.transcripts.get_active(first_job.video_id)
        assert current is not None
        assert current.id == active.id
        assert uow.transcripts.list_segments(current.id) == first_segments
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(TranscriptModel)) == 1
        assert session.scalar(select(func.count()).select_from(TranscriptSegmentModel)) == 1


class _RejectActivationRepository:
    def __init__(self, wrapped) -> None:
        self._wrapped = wrapped

    def __getattr__(self, name: str):
        return getattr(self._wrapped, name)

    def activate(self, video_id: str, transcript_id: str) -> None:
        self._wrapped.activate(video_id, transcript_id)
        raise RuntimeError("simulated transcript activation failure")


class _RejectActivationUnitOfWork(SqlAlchemyIngestUnitOfWork):
    def __enter__(self):
        entered = super().__enter__()
        self.transcripts = _RejectActivationRepository(self.transcripts)
        return entered


def test_failed_publication_preserves_previous_active_transcript(
    session_factory: sessionmaker[Session],
) -> None:
    first = _application(session_factory, "pipeline-v1")
    first_job = first.create(VIDEO_URL)
    first.execute(first_job.id)
    with SqlAlchemyIngestUnitOfWork(session_factory) as uow:
        previous = uow.transcripts.get_active(first_job.video_id)
        assert previous is not None

    failing = _application(
        session_factory,
        "pipeline-v2",
        _RejectActivationUnitOfWork,
        _publication("A newer transcript"),
    )
    failing_job = failing.create(VIDEO_URL)
    with pytest.raises(RuntimeError, match="activation failure"):
        failing.execute(failing_job.id)

    with SqlAlchemyIngestUnitOfWork(session_factory) as uow:
        active = uow.transcripts.get_active(first_job.video_id)
        assert active is not None
        assert active.id == previous.id
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(TranscriptModel)) == 1
