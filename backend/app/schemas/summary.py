from typing import Literal

from pydantic import BaseModel


SummaryMode = Literal["short", "detailed", "timeline"]


class SummaryRequest(BaseModel):
    mode: SummaryMode = "short"


class SummarySource(BaseModel):
    chunk_id: str
    text: str
    start_seconds: float
    end_seconds: float


class SummaryResponse(BaseModel):
    video_id: str
    mode: SummaryMode
    summary: str
    sources: list[SummarySource]
    cached: bool
