from pydantic import BaseModel, Field

from app.api.contracts.chat import RetrievalMode


class RetrievalDebugRequest(BaseModel):
    video_id: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1)
    retrieval_mode: RetrievalMode = "hybrid"
    top_k: int = Field(default=4, ge=1, le=20)


class RetrievalDebugChunk(BaseModel):
    chunk_id: str
    text: str
    start_seconds: float
    end_seconds: float
    score: float


class RetrievalDebugResponse(BaseModel):
    video_id: str
    question: str
    retrieval_mode: RetrievalMode
    top_k: int
    latency_ms: float
    chunks: list[RetrievalDebugChunk]
