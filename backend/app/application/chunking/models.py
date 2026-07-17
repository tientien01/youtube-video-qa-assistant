from dataclasses import asdict, dataclass

from app.domain.entities import Chunk, ChunkSegmentLink


CHUNKER_VERSION = "hierarchical-sentence-v1"


@dataclass(frozen=True, slots=True)
class ChunkerConfig:
    child_target_tokens: int = 320
    child_max_tokens: int = 420
    child_overlap_tokens: int = 48
    child_max_duration_seconds: int = 75
    parent_target_tokens: int = 1000
    parent_max_tokens: int = 1400
    parent_max_duration_seconds: int = 300
    timing_gap_boundary_seconds: float = 2.5
    semantic_refinement: bool = False

    def __post_init__(self) -> None:
        positive = (
            self.child_target_tokens,
            self.child_max_tokens,
            self.child_max_duration_seconds,
            self.parent_target_tokens,
            self.parent_max_tokens,
            self.parent_max_duration_seconds,
        )
        if any(value <= 0 for value in positive):
            raise ValueError("Chunk size and duration limits must be positive.")
        if self.child_target_tokens > self.child_max_tokens:
            raise ValueError("Child target cannot exceed child maximum.")
        if self.parent_target_tokens > self.parent_max_tokens:
            raise ValueError("Parent target cannot exceed parent maximum.")
        if not 0 <= self.child_overlap_tokens < self.child_max_tokens:
            raise ValueError("Child overlap must be smaller than the child maximum.")
        if self.timing_gap_boundary_seconds < 0:
            raise ValueError("Timing gap boundary cannot be negative.")
        if self.semantic_refinement:
            raise ValueError("Semantic refinement is not available in hierarchical-sentence-v1.")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class LimitException:
    chunk_id: str
    reason: str
    source_segment_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ChunkingResult:
    chunks: tuple[Chunk, ...]
    links: tuple[ChunkSegmentLink, ...]
    limit_exceptions: tuple[LimitException, ...]
    chunker_version: str = CHUNKER_VERSION

    @property
    def parent_chunks(self) -> tuple[Chunk, ...]:
        return tuple(chunk for chunk in self.chunks if chunk.parent_chunk_id is None)

    @property
    def child_chunks(self) -> tuple[Chunk, ...]:
        return tuple(chunk for chunk in self.chunks if chunk.parent_chunk_id is not None)
