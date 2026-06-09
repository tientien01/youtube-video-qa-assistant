from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.generation import GenerationMetadata


RetrievalMode = Literal["bm25", "embedding", "hybrid"]


class ChatAskRequest(BaseModel):
    video_id: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1)
    retrieval_mode: RetrievalMode = "hybrid"


class ChatSource(BaseModel):
    chunk_id: str
    text: str
    start_seconds: float
    end_seconds: float
    score: float


class ChatAskResponse(BaseModel):
    answer: str
    retrieval_mode: RetrievalMode
    sources: list[ChatSource]
    generation: GenerationMetadata
