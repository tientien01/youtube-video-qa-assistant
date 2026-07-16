from typing import Protocol

from app.domain.entities import (
    Chunk,
    ChunkSegmentLink,
    IndexVersion,
    IngestAttempt,
    IngestJob,
    Transcript,
    TranscriptSegment,
    Video,
)


class VideoRepository(Protocol):
    def add(self, video: Video) -> Video: ...

    def get(self, video_id: str) -> Video | None: ...

    def get_by_youtube_id(self, youtube_video_id: str) -> Video | None: ...

    def list_recent(self, limit: int = 50) -> list[Video]: ...


class IngestJobRepository(Protocol):
    def add(self, job: IngestJob) -> IngestJob: ...

    def get(self, job_id: str) -> IngestJob | None: ...

    def add_attempt(self, attempt: IngestAttempt) -> IngestAttempt: ...


class TranscriptRepository(Protocol):
    def add(self, transcript: Transcript) -> Transcript: ...

    def get(self, transcript_id: str) -> Transcript | None: ...

    def add_segments(self, segments: list[TranscriptSegment]) -> list[TranscriptSegment]: ...

    def list_segments(self, transcript_id: str) -> list[TranscriptSegment]: ...


class IndexRepository(Protocol):
    def add_version(self, index_version: IndexVersion) -> IndexVersion: ...

    def get_version(self, index_version_id: str) -> IndexVersion | None: ...

    def add_chunks(self, chunks: list[Chunk]) -> list[Chunk]: ...

    def add_segment_links(self, links: list[ChunkSegmentLink]) -> list[ChunkSegmentLink]: ...
