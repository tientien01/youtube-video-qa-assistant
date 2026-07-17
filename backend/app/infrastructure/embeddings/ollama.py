from __future__ import annotations

from collections.abc import Iterator

import httpx

from app.application.embeddings import EmbeddingIdentity


class OllamaEmbeddingError(RuntimeError):
    """Stable infrastructure error for an unavailable or invalid Ollama response."""


class OllamaEmbedding:
    def __init__(
        self,
        *,
        base_url: str = "http://127.0.0.1:11434",
        model: str = "qwen3-embedding:0.6b",
        timeout_seconds: float = 60.0,
        client: httpx.Client | None = None,
        query_instruction: str = "",
        document_instruction: str = "",
    ) -> None:
        self._client = client or httpx.Client(base_url=base_url, timeout=timeout_seconds)
        self._identity = EmbeddingIdentity(
            provider="ollama",
            model=model,
            normalized=True,
            query_instruction=query_instruction,
            document_instruction=document_instruction,
        )

    @property
    def identity(self) -> EmbeddingIdentity:
        return self._identity

    def embed_documents(self, texts: list[str], *, batch_size: int = 32) -> list[list[float]]:
        if batch_size <= 0:
            raise ValueError("Embedding batch size must be positive.")
        vectors: list[list[float]] = []
        prepared = [f"{self.identity.document_instruction}{text}" for text in texts]
        for batch in _batches(prepared, batch_size):
            vectors.extend(self._embed(batch))
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self._embed([f"{self.identity.query_instruction}{text}"])[0]

    def health_check(self) -> bool:
        try:
            response = self._client.get("/api/tags")
            response.raise_for_status()
        except httpx.HTTPError:
            return False
        return True

    def _embed(self, texts: list[str]) -> list[list[float]]:
        try:
            response = self._client.post(
                "/api/embed",
                json={"model": self.identity.model, "input": texts, "truncate": False},
            )
            response.raise_for_status()
            payload = response.json()
            vectors = [[float(value) for value in vector] for vector in payload["embeddings"]]
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as error:
            raise OllamaEmbeddingError(
                f"Ollama embedding model {self.identity.model!r} is unavailable or returned invalid vectors."
            ) from error
        if len(vectors) != len(texts) or not vectors or any(not vector for vector in vectors):
            raise OllamaEmbeddingError("Ollama returned an unexpected embedding batch shape.")
        return vectors


def _batches(values: list[str], size: int) -> Iterator[list[str]]:
    for start in range(0, len(values), size):
        yield values[start : start + size]
