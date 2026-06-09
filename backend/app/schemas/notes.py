from pydantic import BaseModel

from app.schemas.generation import GenerationMetadata


class StudyNotesSource(BaseModel):
    chunk_id: str
    text: str
    start_seconds: float
    end_seconds: float


class StudyNotesResponse(BaseModel):
    video_id: str
    notes: str
    sources: list[StudyNotesSource]
    cached: bool
    generation: GenerationMetadata
