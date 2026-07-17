from __future__ import annotations

from typing import Any


class RerankerSetupError(RuntimeError):
    pass


class BgeCrossEncoderReranker:
    """Lazy local-only adapter for the multilingual BGE v2-m3 cross-encoder."""

    def __init__(
        self,
        model_id: str = "BAAI/bge-reranker-v2-m3",
        *,
        revision: str | None = None,
        max_length: int = 8192,
    ) -> None:
        self._model_id = model_id
        self._revision = revision
        self._max_length = max_length
        self._model: Any | None = None

    @property
    def model_id(self) -> str:
        return self._model_id if self._revision is None else f"{self._model_id}@{self._revision}"

    def score(self, query: str, documents: list[str], *, batch_size: int = 8) -> list[float]:
        if batch_size <= 0:
            raise ValueError("Reranker batch size must be positive.")
        if not documents:
            return []
        model = self._load()
        scores = model.predict(
            [(query, document) for document in documents],
            batch_size=batch_size,
            show_progress_bar=False,
        )
        return [float(score) for score in scores]

    def _load(self) -> Any:
        if self._model is not None:
            return self._model
        try:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(
                self._model_id,
                revision=self._revision,
                max_length=self._max_length,
                local_files_only=True,
            )
        except Exception as error:
            raise RerankerSetupError(
                f"Reranker {self.model_id!r} is unavailable locally. Download it during explicit setup "
                "or use the light profile without reranking."
            ) from error
        return self._model
