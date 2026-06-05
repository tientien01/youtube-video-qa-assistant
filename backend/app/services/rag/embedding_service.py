import hashlib
import math

from app.services.rag.text_processing import clean_text, tokenize


EMBEDDING_DIMENSIONS = 256


class HashingEmbeddingService:
    def __init__(self, dimensions: int = EMBEDDING_DIMENSIONS) -> None:
        self._dimensions = dimensions

    def embed_text(self, text: str) -> list[float]:
        vector = [0.0] * self._dimensions
        normalized_text = clean_text(text.lower())

        for token in tokenize(normalized_text):
            _add_feature(vector, f"tok:{token}", 1.0)
            for ngram in _character_ngrams(token):
                _add_feature(vector, f"ngram:{ngram}", 0.35)

        return _normalize(vector)


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        return 0.0

    return round(sum(left_item * right_item for left_item, right_item in zip(left, right)), 6)


def _character_ngrams(token: str, size: int = 3) -> list[str]:
    if len(token) <= size:
        return [token]

    return [token[index:index + size] for index in range(len(token) - size + 1)]


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


embedding_service = HashingEmbeddingService()
