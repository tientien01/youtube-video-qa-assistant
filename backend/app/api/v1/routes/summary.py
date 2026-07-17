from fastapi import APIRouter, HTTPException, status

from app.api.contracts.summary import SummaryRequest, SummaryResponse
from app.application.legacy.learning.summary_service import generate_video_summary
from app.application.legacy.rag.local_store import VideoNotIndexedError


router = APIRouter(prefix="/videos", tags=["summary"])


@router.post(
    "/{video_id}/summary",
    response_model=SummaryResponse,
    status_code=status.HTTP_200_OK,
)
def summarize_video(video_id: str, request: SummaryRequest) -> SummaryResponse:
    try:
        return generate_video_summary(video_id=video_id, mode=request.mode, force=request.force)
    except VideoNotIndexedError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
