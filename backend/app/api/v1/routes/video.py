from fastapi import APIRouter, HTTPException, status

from app.schemas.video import VideoIngestRequest, VideoIngestResponse
from app.services.extraction.transcript_service import TranscriptNotFoundError
from app.services.rag.video_index_service import ingest_video_content


router = APIRouter(prefix='/videos', tags=["video"])

@router.post(
    '/ingest',
    response_model=VideoIngestResponse,
    status_code=status.HTTP_200_OK,
)
def ingest_video(request: VideoIngestRequest) -> VideoIngestResponse:
    try:
        return ingest_video_content(request.url)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    except TranscriptNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
