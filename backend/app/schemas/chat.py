from pydantic import BaseModel, Field


class ChatAskRequest(BaseModel):
    video_id: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1)


class ChatSource(BaseModel):
    chunk_id: str
    text: str
    start_seconds: float
    end_seconds: float
    score: float


class ChatAskResponse(BaseModel):
    answer: str
    sources: list[ChatSource]
