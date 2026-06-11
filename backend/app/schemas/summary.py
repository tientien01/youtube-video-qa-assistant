from typing import Literal

from pydantic import BaseModel

from app.schemas.generation import GenerationMetadata


SummaryMode = Literal["short", "detailed", "timeline"]


class SummaryRequest(BaseModel):
    mode: SummaryMode = "short"
    force: bool = False


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
    generation: GenerationMetadata
