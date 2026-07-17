"""Provider-independent embedding contracts."""

from app.application.embeddings.ports import EmbeddingIdentity, EmbeddingProvider

__all__ = ["EmbeddingIdentity", "EmbeddingProvider"]
