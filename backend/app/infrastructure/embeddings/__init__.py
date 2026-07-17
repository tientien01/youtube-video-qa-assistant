"""Local embedding provider adapters."""

from app.infrastructure.embeddings.fake import DeterministicFakeEmbedding
from app.infrastructure.embeddings.ollama import OllamaEmbedding

__all__ = ["DeterministicFakeEmbedding", "OllamaEmbedding"]
