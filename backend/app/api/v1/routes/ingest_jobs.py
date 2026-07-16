from fastapi import APIRouter, Depends, status

from app.api.dependencies import DatabaseSchemaError, get_ingest_application
from app.application.ingest.use_cases import IngestJobApplication, IngestJobNotFound
from app.core.errors import ApiError
from app.domain.entities import IngestJob
from app.schemas.ingest_job import IngestJobCreateRequest, IngestJobErrorResponse, IngestJobResponse


router = APIRouter(prefix="/ingest-jobs", tags=["ingest-jobs"])


def _application() -> IngestJobApplication:
    try:
        return get_ingest_application()
    except DatabaseSchemaError as error:
        raise ApiError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="DATABASE_SCHEMA_NOT_READY",
            message=str(error),
        ) from error


@router.post("", response_model=IngestJobResponse, status_code=status.HTTP_202_ACCEPTED)
def create_ingest_job(
    request: IngestJobCreateRequest,
    application: IngestJobApplication = Depends(_application),
) -> IngestJobResponse:
    try:
        return _to_response(application.create(request.url, client_idempotency_key=request.idempotency_key))
    except ValueError as error:
        raise ApiError(status.HTTP_400_BAD_REQUEST, "INVALID_VIDEO_URL", str(error)) from error


@router.get("/{job_id}", response_model=IngestJobResponse)
def get_ingest_job(
    job_id: str,
    application: IngestJobApplication = Depends(_application),
) -> IngestJobResponse:
    return _to_response(_get_job(application, job_id))


@router.post("/{job_id}/retry", response_model=IngestJobResponse, status_code=status.HTTP_202_ACCEPTED)
def retry_ingest_job(
    job_id: str,
    application: IngestJobApplication = Depends(_application),
) -> IngestJobResponse:
    try:
        return _to_response(application.retry(job_id))
    except IngestJobNotFound as error:
        raise _not_found(error) from error
    except ValueError as error:
        raise ApiError(status.HTTP_409_CONFLICT, "INGEST_NOT_RETRYABLE", str(error)) from error


@router.post("/{job_id}/cancel", response_model=IngestJobResponse)
def cancel_ingest_job(
    job_id: str,
    application: IngestJobApplication = Depends(_application),
) -> IngestJobResponse:
    try:
        return _to_response(application.cancel(job_id))
    except IngestJobNotFound as error:
        raise _not_found(error) from error
    except ValueError as error:
        raise ApiError(status.HTTP_409_CONFLICT, "INGEST_NOT_CANCELLABLE", str(error)) from error


def _get_job(application: IngestJobApplication, job_id: str) -> IngestJob:
    try:
        return application.get(job_id)
    except IngestJobNotFound as error:
        raise _not_found(error) from error


def _not_found(error: IngestJobNotFound) -> ApiError:
    return ApiError(status.HTTP_404_NOT_FOUND, "INGEST_JOB_NOT_FOUND", str(error))


def _to_response(job: IngestJob) -> IngestJobResponse:
    error = None
    if job.error_code is not None:
        error = IngestJobErrorResponse(
            code=job.error_code,
            message=job.error_message or "Ingest failed.",
            stage=job.current_stage.value,
            retryable=job.retryable,
        )
    return IngestJobResponse(
        job_id=job.id,
        video_id=job.video_id,
        status=job.status.value,
        stage=job.current_stage.value,
        target_fingerprint=job.target_fingerprint,
        retryable=job.retryable,
        error=error,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )
