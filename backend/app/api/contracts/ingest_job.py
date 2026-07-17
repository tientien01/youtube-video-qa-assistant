from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class IngestJobCreateRequest(BaseModel):
    url: str = Field(..., min_length=1)
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=128)


class IngestJobErrorResponse(BaseModel):
    code: str
    message: str
    stage: str
    retryable: bool


class IngestJobResponse(BaseModel):
    job_id: str
    video_id: str
    status: Literal["pending", "running", "retry_wait", "ready", "failed", "cancelled"]
    stage: Literal[
        "pending",
        "fetching_metadata",
        "fetching_transcript",
        "normalizing",
        "validating",
        "chunking",
        "embedding",
        "committing",
        "complete",
    ]
    target_fingerprint: str | None
    retryable: bool
    error: IngestJobErrorResponse | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
