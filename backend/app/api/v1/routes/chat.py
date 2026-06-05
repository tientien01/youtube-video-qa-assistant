import logging

from fastapi import APIRouter, HTTPException, status

from app.schemas.chat import ChatAskRequest, ChatAskResponse
from app.services.rag.local_store import VideoNotIndexedError
from app.services.rag.video_index_service import ask_video_question


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


@router.post(
    "/ask",
    response_model=ChatAskResponse,
    status_code=status.HTTP_200_OK,
)
def ask_question(request: ChatAskRequest) -> ChatAskResponse:
    if not request.question.strip():
        logger.warning("Rejected empty chat question for video_id=%s", request.video_id)
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
        logger.warning("Question asked before ingest for video_id=%s", request.video_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
