from fastapi import APIRouter, HTTPException, status

from app.schemas.video import VideoIngestRequest, VideoIngestResponse
from app.services.extraction.transcript_service import (
    TranscriptNotFoundError,
    fetch_transcript,
)
from app.services.extraction.video_url_service import extract_youtube_video_id


router = APIRouter(prefix='/videos', tags=["video"])

@router.post(
    '/ingest',
    response_model=VideoIngestResponse,
    status_code=status.HTTP_200_OK,
)
def ingest_video(request: VideoIngestRequest) -> VideoIngestResponse:
    try:
        video_id = extract_youtube_video_id(request.url)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e 

    try:
        transcript_segments, language_code = fetch_transcript(video_id)
    except TranscriptNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e

    return VideoIngestResponse(
        video_id=video_id,
        title="Mock video title",
        url=f"https://www.youtube.com/watch?v={video_id}",
        duration_seconds=None,
        transcript_language=language_code,
        chunk_count=len(transcript_segments),
        status="transcript_fetched",
    )
