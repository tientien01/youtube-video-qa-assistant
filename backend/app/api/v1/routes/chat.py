import logging

from fastapi import APIRouter, HTTPException, status

from app.api.contracts.chat import ChatAskRequest, ChatAskResponse, ChatHistoryDeleteResponse, ChatHistoryResponse
from app.application.legacy.rag.local_store import VideoNotIndexedError
from app.application.legacy.rag.video_index_service import (
    ask_video_question,
    delete_video_chat_history,
    list_video_chat_history,
)


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
            retrieval_mode=request.retrieval_mode,
            source_chunk_ids=request.source_chunk_ids,
            answer_language=request.answer_language,
        )
    except VideoNotIndexedError as error:
        logger.warning("Question asked before ingest for video_id=%s", request.video_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get(
    "/history/{video_id}",
    response_model=ChatHistoryResponse,
    status_code=status.HTTP_200_OK,
)
def get_chat_history(video_id: str) -> ChatHistoryResponse:
    try:
        return list_video_chat_history(video_id.strip())
    except VideoNotIndexedError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.delete(
    "/history/{video_id}",
    response_model=ChatHistoryDeleteResponse,
    status_code=status.HTTP_200_OK,
)
def clear_chat_history(video_id: str) -> ChatHistoryDeleteResponse:
    try:
        return delete_video_chat_history(video_id.strip())
    except VideoNotIndexedError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
