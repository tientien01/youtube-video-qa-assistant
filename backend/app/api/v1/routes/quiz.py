from fastapi import APIRouter, HTTPException, status

from app.api.contracts.quiz import QuizRequest, QuizResponse
from app.application.legacy.learning.quiz_service import generate_quiz
from app.application.legacy.rag.local_store import VideoNotIndexedError


router = APIRouter(prefix="/videos", tags=["quiz"])


@router.post(
    "/{video_id}/quiz",
    response_model=QuizResponse,
    status_code=status.HTTP_200_OK,
)
def create_quiz(video_id: str, request: QuizRequest) -> QuizResponse:
    try:
        return generate_quiz(
            video_id=video_id,
            question_count=request.question_count,
            difficulty=request.difficulty,
            question_type=request.question_type,
            mode=request.mode,
            force=request.force,
            source_chunk_ids=request.source_chunk_ids,
        )
    except VideoNotIndexedError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
