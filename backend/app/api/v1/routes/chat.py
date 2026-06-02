from fastapi import APIRouter, HTTPException, status

from app.schemas.chat import ChatAskRequest, ChatAskResponse
from app.services.rag.local_store import VideoNotIndexedError
from app.services.rag.video_index_service import ask_video_question


router = APIRouter(prefix="/chat", tags=["chat"])


@router.post(
    "/ask",
    response_model=ChatAskResponse,
    status_code=status.HTTP_200_OK,
)
def ask_question(request: ChatAskRequest) -> ChatAskResponse:
    if not request.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty.",
        )

    try:
        return ask_video_question(
            video_id=request.video_id.strip(),
            question=request.question.strip(),
        )
    except VideoNotIndexedError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
