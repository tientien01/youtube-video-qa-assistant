from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Protocol

from app.domain.entities import IndexVersion


@dataclass(frozen=True, slots=True)
class EmbeddingIdentity:
    provider: str
    model: str
    revision: str | None = None
    normalized: bool = True
    query_instruction: str = ""
    document_instruction: str = ""

    def __post_init__(self) -> None:
        if not self.provider.strip() or not self.model.strip():
            raise ValueError("Embedding provider and model cannot be empty.")

    def to_config(self) -> dict[str, object]:
        return {
            "normalized": self.normalized,
            "query_instruction": self.query_instruction,
            "document_instruction": self.document_instruction,
        }

    def matches(self, index_version: IndexVersion) -> bool:
        return (
            self.provider == index_version.embedding_provider
            and self.model == index_version.embedding_model
            and self.revision == index_version.embedding_revision
            and self.to_config() == index_version.embedding_config
        )

    def fingerprint_material(self) -> dict[str, object]:
        return asdict(self)


class EmbeddingProvider(Protocol):
    @property
    def identity(self) -> EmbeddingIdentity: ...

    def embed_documents(self, texts: list[str], *, batch_size: int = 32) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...

    def health_check(self) -> bool: ...
