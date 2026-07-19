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
    ingest_video_content,
    rebuild_video_index,
)
from app.api.dependencies import DatabaseSchemaError, get_video_library_application, get_video_transcript_application
from app.application.video import (
    TranscriptNotFound,
    VideoLibraryApplication,
    VideoLibraryItem,
    VideoNotFound,
    VideoTranscriptApplication,
)
from app.core.errors import ApiError


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/videos", tags=["video"])


def _library_application() -> VideoLibraryApplication:
    try:
        return get_video_library_application()
    except DatabaseSchemaError as error:
        raise ApiError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="DATABASE_SCHEMA_NOT_READY",
            message=str(error),
        ) from error


@router.get("", response_model=list[VideoMetadataResponse])
def list_videos(
    application: VideoLibraryApplication = Depends(_library_application),
) -> list[VideoMetadataResponse]:
    return [_metadata_response(item) for item in application.list()]


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
def get_video(
    video_id: str,
    application: VideoLibraryApplication = Depends(_library_application),
) -> VideoMetadataResponse:
    try:
        return _metadata_response(application.get(video_id))
    except VideoNotFound as error:
        raise ApiError(status.HTTP_404_NOT_FOUND, "VIDEO_NOT_FOUND", str(error)) from error


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
def delete_video(
    video_id: str,
    application: VideoLibraryApplication = Depends(_library_application),
) -> VideoDeleteResponse:
    return VideoDeleteResponse(video_id=video_id, deleted=application.delete(video_id))


@router.post("/{video_id}/rebuild-index", response_model=VideoRebuildIndexResponse)
def rebuild_index(video_id: str) -> VideoRebuildIndexResponse:
    try:
        return rebuild_video_index(video_id)
    except VideoNotIndexedError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


def _metadata_response(item: VideoLibraryItem) -> VideoMetadataResponse:
    return VideoMetadataResponse(
        video_id=item.video_id,
        title=item.title,
        url=item.url,
        channel_title=item.channel_title,
        thumbnail_url=item.thumbnail_url,
        duration_seconds=item.duration_seconds,
        transcript_language=item.transcript_language,
        chunk_count=item.chunk_count,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )
