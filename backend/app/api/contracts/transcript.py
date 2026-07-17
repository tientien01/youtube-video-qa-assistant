from pydantic import BaseModel, Field


class TranscriptSegment(BaseModel):
    text: str = Field(..., min_length=1, description="The text content of the transcript segment.")
    start_seconds: float = Field(..., ge=0, description="The start time of the transcript segment in seconds.")
    end_seconds: float = Field(..., ge=0, description="The end time of the transcript segment in seconds.")


class TranscriptSegmentResponse(BaseModel):
    segment_id: str
    original_text: str
    start_seconds: float
    end_seconds: float


class VideoTranscriptResponse(BaseModel):
    video_id: str
    language_code: str
    segments: list[TranscriptSegmentResponse]
