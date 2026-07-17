from dataclasses import dataclass
from collections.abc import Callable
from typing import Protocol, Self

from app.application.ports.repositories import IndexRepository, TranscriptRepository


@dataclass(frozen=True, slots=True)
class VectorRecord:
    chunk_id: str
    video_id: str
    index_version_id: str
    vector: list[float]


@dataclass(frozen=True, slots=True)
class VectorMatch:
    chunk_id: str
    score: float


class VectorIndex(Protocol):
    def health_check(self) -> bool: ...

    def create(self, index_version_id: str, dimension: int) -> None: ...

    def upsert(self, index_version_id: str, records: list[VectorRecord]) -> None: ...

    def query(
        self,
        index_version_id: str,
        video_id: str,
        vector: list[float],
        *,
        limit: int,
    ) -> list[VectorMatch]: ...

    def delete(self, index_version_id: str) -> bool: ...


class IndexUnitOfWork(Protocol):
    transcripts: TranscriptRepository
    indexes: IndexRepository

    def __enter__(self) -> Self: ...

    def __exit__(self, exc_type, exc_value, traceback) -> None: ...

    def commit(self) -> None: ...


type IndexUnitOfWorkFactory = Callable[[], IndexUnitOfWork]
