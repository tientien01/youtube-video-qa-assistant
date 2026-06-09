from fastapi import APIRouter, HTTPException, status

from app.schemas.summary import SummaryRequest, SummaryResponse
from app.services.learning.summary_service import generate_video_summary
from app.services.rag.local_store import VideoNotIndexedError


router = APIRouter(prefix="/videos", tags=["summary"])


@router.post(
    "/{video_id}/summary",
    response_model=SummaryResponse,
    status_code=status.HTTP_200_OK,
)
def summarize_video(video_id: str, request: SummaryRequest) -> SummaryResponse:
    try:
        return generate_video_summary(video_id=video_id, mode=request.mode)
    except VideoNotIndexedError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
