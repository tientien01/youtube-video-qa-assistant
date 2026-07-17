"""Compatibility imports for legacy JSON/Chroma retrieval."""

from app.infrastructure.vector.legacy import (
    ChromaVectorStore,
    LocalVectorStore,
    VectorRecord,
    build_vector_store,
    vector_store,
)

__all__ = [
    "ChromaVectorStore",
    "LocalVectorStore",
    "VectorRecord",
    "build_vector_store",
    "vector_store",
]
