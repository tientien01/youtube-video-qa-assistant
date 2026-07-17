"""Compatibility imports for the legacy RAG path.

New code must depend on ``app.application.embeddings`` and infrastructure
adapters directly.
"""

from app.infrastructure.embeddings.legacy import (
    EMBEDDING_DIMENSIONS,
    EmbeddingService,
    HashingEmbeddingService,
    SentenceTransformerEmbeddingService,
    build_embedding_service,
    cosine_similarity,
    embedding_service,
)

__all__ = [
    "EMBEDDING_DIMENSIONS",
    "EmbeddingService",
    "HashingEmbeddingService",
    "SentenceTransformerEmbeddingService",
    "build_embedding_service",
    "cosine_similarity",
    "embedding_service",
]
