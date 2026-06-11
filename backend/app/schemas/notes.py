from typing import Literal

from pydantic import BaseModel

from app.schemas.generation import GenerationMetadata


StudyNotesMode = Literal[
    "concise",
    "detailed",
    "timeline",
    "exam_review",
    "beginner",
    "flashcards",
    "concept_map",
]
StudyNotesLength = Literal["short", "medium", "long"]


class StudyNotesRequest(BaseModel):
    mode: StudyNotesMode = "concise"
    length: StudyNotesLength = "medium"
    learning_goal: str | None = None
    force: bool = False


class StudyNotesSource(BaseModel):
    chunk_id: str
    text: str
    start_seconds: float
    end_seconds: float


class StudyNotesResponse(BaseModel):
    video_id: str
    mode: StudyNotesMode = "concise"
    length: StudyNotesLength = "medium"
    learning_goal: str | None = None
    notes: str
    sources: list[StudyNotesSource]
    cached: bool
    generation: GenerationMetadata
