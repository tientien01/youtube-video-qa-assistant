from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.generation import GenerationMetadata


QuizDifficulty = Literal["easy", "medium", "hard"]
QuizQuestionType = Literal["multiple_choice", "true_false", "short_answer", "mixed"]
GeneratedQuizQuestionType = Literal["multiple_choice", "true_false", "short_answer"]
QuizMode = Literal["practice", "exam", "concept_check"]


class QuizRequest(BaseModel):
    question_count: int = Field(default=5, ge=1, le=20)
    difficulty: QuizDifficulty = "medium"
    question_type: QuizQuestionType = "mixed"
    mode: QuizMode = "practice"
    force: bool = False
    source_chunk_ids: list[str] = []


class QuizSource(BaseModel):
    chunk_id: str
    text: str
    start_seconds: float
    end_seconds: float


class QuizQuestion(BaseModel):
    question_id: str
    question_type: GeneratedQuizQuestionType
    question: str
    options: list[str]
    correct_answer: str
    explanation: str
    source: QuizSource


class QuizResponse(BaseModel):
    video_id: str
    difficulty: QuizDifficulty
    question_type: QuizQuestionType
    mode: QuizMode = "practice"
    attempt_id: str | None = None
    questions: list[QuizQuestion]
    sources: list[QuizSource]
    cached: bool
    generation: GenerationMetadata | None = None
