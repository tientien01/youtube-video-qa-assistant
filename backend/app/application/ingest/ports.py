from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, Self

from app.application.ports.repositories import IngestJobRepository, VideoRepository
from app.domain.entities import IngestStage


@dataclass(frozen=True, slots=True)
class ProcessVideoRequest:
    video_id: str
    canonical_url: str


@dataclass(frozen=True, slots=True)
class ProcessedVideo:
    title: str
    channel_title: str | None = None
    thumbnail_url: str | None = None
    duration_ms: int | None = None


class IngestFailure(RuntimeError):
    def __init__(self, code: str, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class IngestProcessor(Protocol):
    name: str

    def process(
        self,
        request: ProcessVideoRequest,
        *,
        report_stage: Callable[[IngestStage], None],
        is_cancelled: Callable[[], bool],
    ) -> ProcessedVideo: ...


class IngestUnitOfWork(Protocol):
    videos: VideoRepository
    jobs: IngestJobRepository

    def __enter__(self) -> Self: ...

    def __exit__(self, exc_type, exc_value, traceback) -> None: ...

    def commit(self) -> None: ...


type IngestUnitOfWorkFactory = Callable[[], IngestUnitOfWork]


class IngestJobRunner(Protocol):
    def submit(self, job_id: str, video_id: str) -> None: ...
