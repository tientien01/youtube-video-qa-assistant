from __future__ import annotations

import hashlib
import math
import re

from app.application.embeddings import EmbeddingIdentity


_TOKENS = re.compile(r"[^\W_]+", re.UNICODE)


class DeterministicFakeEmbedding:
    """Stable multilingual hashing vectors for tests; never a production model."""

    def __init__(self, dimension: int = 32, *, model: str = "hashing-test-v1") -> None:
        if dimension <= 0:
            raise ValueError("Embedding dimension must be positive.")
        self._dimension = dimension
        self._identity = EmbeddingIdentity(provider="fake", model=model, revision="1")

    @property
    def identity(self) -> EmbeddingIdentity:
        return self._identity

    def embed_documents(self, texts: list[str], *, batch_size: int = 32) -> list[list[float]]:
        if batch_size <= 0:
            raise ValueError("Embedding batch size must be positive.")
        return [
            self._embed(text)
            for start in range(0, len(texts), batch_size)
            for text in texts[start : start + batch_size]
        ]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def health_check(self) -> bool:
        return True

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self._dimension
        for token in _TOKENS.findall(text.casefold()):
            digest = hashlib.blake2b(token.encode(), digest_size=8).digest()
            raw = int.from_bytes(digest, "big")
            vector[raw % self._dimension] += 1.0 if raw & 1 else -1.0
        magnitude = math.sqrt(sum(value * value for value in vector))
        return vector if magnitude == 0 else [round(value / magnitude, 8) for value in vector]
