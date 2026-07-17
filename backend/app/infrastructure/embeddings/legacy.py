"""Deprecated embedding adapters retained for the pre-canonical RAG compatibility path."""

import hashlib
import math
import re
from typing import Protocol

from app.core.config import get_settings


EMBEDDING_DIMENSIONS = 256
_WHITESPACE = re.compile(r"\s+")
_TOKENS = re.compile(r"[^\W_]+", re.UNICODE)


class EmbeddingService(Protocol):
    def embed_text(self, text: str) -> list[float]: ...

    def embed_texts(self, texts: list[str]) -> list[list[float]]: ...


class HashingEmbeddingService:
    def __init__(self, dimensions: int = EMBEDDING_DIMENSIONS) -> None:
        self._dimensions = dimensions

    def embed_text(self, text: str) -> list[float]:
        vector = [0.0] * self._dimensions
        normalized_text = _WHITESPACE.sub(" ", text.lower()).strip()
        for token in _TOKENS.findall(normalized_text):
            _add_feature(vector, f"tok:{token}", 1.0)
            for ngram in _character_ngrams(token):
                _add_feature(vector, f"ngram:{ngram}", 0.35)
        return _normalize(vector)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_text(text) for text in texts]


class SentenceTransformerEmbeddingService:
    def __init__(self, model_name: str) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as error:
            raise RuntimeError(
                "sentence-transformers is required when EMBEDDING_PROVIDER=sentence_transformers."
            ) from error
        self._model_name = model_name
        self._model = SentenceTransformer(model_name)

    def embed_text(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        embeddings = self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return [[round(float(value), 6) for value in embedding] for embedding in embeddings]


class OllamaEmbeddingService:
    def __init__(self, model_name: str, base_url: str) -> None:
        from app.infrastructure.embeddings.ollama import OllamaEmbeddingAdapter

        self._adapter = OllamaEmbeddingAdapter(model=model_name, base_url=base_url)

    def embed_text(self, text: str) -> list[float]:
        return self._adapter.embed_query(text)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return self._adapter.embed_documents(texts)


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        return 0.0
    return round(sum(left_item * right_item for left_item, right_item in zip(left, right)), 6)


def build_embedding_service(provider: str | None = None, model_name: str | None = None) -> EmbeddingService:
    settings = get_settings()
    selected_provider = (provider or settings.embedding_provider).lower()
    if selected_provider == "hashing":
        return HashingEmbeddingService()
    if selected_provider in {"sentence_transformers", "sentence-transformers"}:
        return SentenceTransformerEmbeddingService(model_name or settings.embedding_model_name)
    if selected_provider == "ollama":
        return OllamaEmbeddingService(model_name or settings.embedding_model_name, settings.ollama_base_url)
    raise ValueError(f"Unsupported embedding provider: {selected_provider}")


def _character_ngrams(token: str, size: int = 3) -> list[str]:
    if len(token) <= size:
        return [token]
    return [token[index : index + size] for index in range(len(token) - size + 1)]


def _add_feature(vector: list[float], feature: str, weight: float) -> None:
    digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
    raw_value = int.from_bytes(digest, byteorder="big", signed=False)
    index = raw_value % len(vector)
    sign = 1.0 if (raw_value >> 1) % 2 == 0 else -1.0
    vector[index] += sign * weight


def _normalize(vector: list[float]) -> list[float]:
    magnitude = math.sqrt(sum(value * value for value in vector))
    if magnitude == 0:
        return vector
    return [round(value / magnitude, 6) for value in vector]


embedding_service = build_embedding_service()
