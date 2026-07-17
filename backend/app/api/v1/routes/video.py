import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.contracts.transcript import TranscriptSegmentResponse, VideoTranscriptResponse
from app.application.ingest.transcript import TranscriptAcquisitionError, TranscriptFailureCode
from app.api.contracts.video import (
    VideoDeleteResponse,
    VideoIngestRequest,
    VideoIngestResponse,
    VideoMetadataResponse,
    VideoRebuildIndexResponse,
)
from app.application.legacy.rag.local_store import VideoNotIndexedError
from app.application.legacy.rag.video_index_service import (
    delete_ingested_video,
    get_ingested_video,
    ingest_video_content,
    list_ingested_videos,
    rebuild_video_index,
)
from app.api.dependencies import get_video_transcript_application
from app.application.video import TranscriptNotFound, VideoTranscriptApplication


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
    except TranscriptAcquisitionError as error:
        logger.warning("Transcript acquisition failed during ingest: code=%s", error.code.value)
        response_status = (
            status.HTTP_404_NOT_FOUND
            if error.code in {TranscriptFailureCode.NOT_FOUND, TranscriptFailureCode.VIDEO_UNAVAILABLE}
            else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        raise HTTPException(
            status_code=response_status,
            detail=str(error),
        ) from error


@router.get("/{video_id}", response_model=VideoMetadataResponse)
def get_video(video_id: str) -> VideoMetadataResponse:
    try:
        return get_ingested_video(video_id)
    except VideoNotIndexedError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/{video_id}/transcript", response_model=VideoTranscriptResponse)
def get_video_transcript(
    video_id: str,
    application: VideoTranscriptApplication = Depends(get_video_transcript_application),
) -> VideoTranscriptResponse:
    try:
        transcript = application.get(video_id)
    except TranscriptNotFound as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    return VideoTranscriptResponse(
        video_id=transcript.video_id,
        language_code=transcript.language_code,
        segments=[
            TranscriptSegmentResponse(
                segment_id=segment.id,
                original_text=segment.original_text,
                start_seconds=segment.start_ms / 1000,
                end_seconds=segment.end_ms / 1000,
            )
            for segment in transcript.segments
        ],
    )


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
