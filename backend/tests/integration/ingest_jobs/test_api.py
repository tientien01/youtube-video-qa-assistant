import os
from collections.abc import Callable


os.environ["LLM_PROVIDER"] = "fallback"
os.environ["EMBEDDING_PROVIDER"] = "hashing"
os.environ["VECTOR_STORE_PROVIDER"] = "local_json"

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.api.v1.routes.ingest_jobs import _application
from app.application.ingest.ports import ProcessedVideo, ProcessVideoRequest
from app.application.ingest.use_cases import IngestJobApplication
from app.domain.entities import IngestStage
from app.infrastructure.db.unit_of_work import SqlAlchemyIngestUnitOfWork
from app.main import app


class NoopProcessor:
    name = "noop"

    def process(
        self,
        request: ProcessVideoRequest,
        *,
        report_stage: Callable[[IngestStage], None],
        is_cancelled: Callable[[], bool],
    ) -> ProcessedVideo:
        return ProcessedVideo(title=request.video_id)


def test_job_api_exposes_persistent_state_and_stable_errors(session_factory: sessionmaker[Session]) -> None:
    application = IngestJobApplication(
        lambda: SqlAlchemyIngestUnitOfWork(session_factory),
        NoopProcessor(),
        target_fingerprint="api-test-v1",
    )
    app.dependency_overrides[_application] = lambda: application
    try:
        with TestClient(app) as client:
            created = client.post("/api/v1/ingest-jobs", json={"url": "https://youtu.be/dQw4w9WgXcQ"})
            assert created.status_code == 202
            assert created.json()["status"] == "pending"

            job_id = created.json()["job_id"]
            status_response = client.get(f"/api/v1/ingest-jobs/{job_id}")
            assert status_response.status_code == 200
            assert status_response.json()["job_id"] == job_id

            missing = client.get("/api/v1/ingest-jobs/missing")
            assert missing.status_code == 404
            assert missing.json()["error"]["code"] == "INGEST_JOB_NOT_FOUND"

            invalid = client.post("/api/v1/ingest-jobs", json={"url": "https://example.com/video"})
            assert invalid.status_code == 400
            assert invalid.json()["error"]["code"] == "INVALID_VIDEO_URL"
    finally:
        app.dependency_overrides.clear()
