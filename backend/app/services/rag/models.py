from dataclasses import dataclass


@dataclass(frozen=True)
class TranscriptChunk:
    chunk_id: str
    video_id: str
    text: str
    start_seconds: float
    end_seconds: float


@dataclass(frozen=True)
class RetrievedChunk:
    chunk: TranscriptChunk
    score: float
