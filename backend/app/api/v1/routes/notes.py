from fastapi import APIRouter, HTTPException, status

from app.schemas.notes import StudyNotesResponse
from app.services.learning.notes_service import generate_study_notes
from app.services.rag.local_store import VideoNotIndexedError


router = APIRouter(prefix="/videos", tags=["notes"])


@router.post(
    "/{video_id}/study-notes",
    response_model=StudyNotesResponse,
    status_code=status.HTTP_200_OK,
)
def create_study_notes(video_id: str) -> StudyNotesResponse:
    try:
        return generate_study_notes(video_id=video_id)
    except VideoNotIndexedError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
