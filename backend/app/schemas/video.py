from typing import Literal

from pydantic import BaseModel, Field

class VideoIngestRequest(BaseModel):
    url: str = Field(..., min_length=1)

class VideoIngestResponse(BaseModel):
    video_id: str
    title: str
    url: str
    duration_seconds: int | None
    transcript_language: str | None
    chunk_count: int
    status: Literal['pending', 'ready', 'transcript_not_found', 'failed']