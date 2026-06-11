import logging

from fastapi import APIRouter, HTTPException, status

from app.schemas.video import (
    VideoDeleteResponse,
    VideoIngestRequest,
    VideoIngestResponse,
    VideoMetadataResponse,
    VideoRebuildIndexResponse,
)
from app.services.extraction.transcript_service import TranscriptNotFoundError
from app.services.rag.local_store import VideoNotIndexedError
from app.services.rag.video_index_service import (
    delete_ingested_video,
    get_ingested_video,
    ingest_video_content,
    list_ingested_videos,
    rebuild_video_index,
)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/videos", tags=["video"])


@router.get("", response_model=list[VideoMetadataResponse])
def list_videos() -> list[VideoMetadataResponse]:
    return list_ingested_videos()


@router.post(
    "/ingest",
    response_model=VideoIngestResponse,
    status_code=status.HTTP_200_OK,
)
def ingest_video(request: VideoIngestRequest) -> VideoIngestResponse:
    try:
        return ingest_video_content(request.url)
    except ValueError as error:
        logger.warning("Rejected video ingest request: %s", error)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    except TranscriptNotFoundError as error:
        logger.warning("Transcript unavailable during ingest: %s", error)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error


@router.get("/{video_id}", response_model=VideoMetadataResponse)
def get_video(video_id: str) -> VideoMetadataResponse:
    try:
        return get_ingested_video(video_id)
    except VideoNotIndexedError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.delete("/{video_id}", response_model=VideoDeleteResponse)
def delete_video(video_id: str) -> VideoDeleteResponse:
    try:
        return delete_ingested_video(video_id)
    except VideoNotIndexedError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post("/{video_id}/rebuild-index", response_model=VideoRebuildIndexResponse)
def rebuild_index(video_id: str) -> VideoRebuildIndexResponse:
    try:
        return rebuild_video_index(video_id)
    except VideoNotIndexedError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
