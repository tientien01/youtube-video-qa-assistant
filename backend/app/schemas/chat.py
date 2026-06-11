from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.generation import GenerationMetadata


RetrievalMode = Literal["bm25", "embedding", "hybrid"]


class ChatAskRequest(BaseModel):
    video_id: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1)
    retrieval_mode: RetrievalMode = "hybrid"
    source_chunk_ids: list[str] = []


class ChatSource(BaseModel):
    chunk_id: str
    text: str
    start_seconds: float
    end_seconds: float
    score: float


class ChatAskResponse(BaseModel):
    message_id: str | None = None
    answer: str
    retrieval_mode: RetrievalMode
    sources: list[ChatSource]
    generation: GenerationMetadata
    groundedness_warning: str | None = None


class ChatHistoryMessage(BaseModel):
    message_id: str
    video_id: str
    question: str
    answer: str
    retrieval_mode: RetrievalMode
    sources: list[ChatSource]
    generation: GenerationMetadata
    groundedness_warning: str | None = None
    created_at: str


class ChatHistoryResponse(BaseModel):
    video_id: str
    messages: list[ChatHistoryMessage]


class ChatHistoryDeleteResponse(BaseModel):
    video_id: str
    deleted: bool
