from fastapi import APIRouter, HTTPException, status

from app.api.contracts.notes import StudyNotesRequest, StudyNotesResponse
from app.application.legacy.learning.notes_service import generate_study_notes
from app.application.legacy.rag.local_store import VideoNotIndexedError


router = APIRouter(prefix="/videos", tags=["notes"])


@router.post(
    "/{video_id}/study-notes",
    response_model=StudyNotesResponse,
    status_code=status.HTTP_200_OK,
)
def create_study_notes(video_id: str, request: StudyNotesRequest | None = None) -> StudyNotesResponse:
    resolved_request = request or StudyNotesRequest()
    try:
        return generate_study_notes(
            video_id=video_id,
            mode=resolved_request.mode,
            length=resolved_request.length,
            learning_goal=resolved_request.learning_goal,
            force=resolved_request.force,
        )
    except VideoNotIndexedError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
