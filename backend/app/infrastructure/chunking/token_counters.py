from __future__ import annotations

from typing import Any


class TokenizerSetupError(RuntimeError):
    """Raised when the configured embedding tokenizer is not available locally."""


class HuggingFaceTokenCounter:
    """Counts tokens with the tokenizer belonging to the embedding model."""

    def __init__(self, model_id: str, *, revision: str | None = None) -> None:
        if not model_id.strip():
            raise ValueError("Tokenizer model ID cannot be empty.")
        self._model_id = model_id
        self._revision = revision
        self._tokenizer: Any | None = None

    @property
    def model_id(self) -> str:
        return self._model_id if self._revision is None else f"{self._model_id}@{self._revision}"

    def count(self, text: str) -> int:
        tokenizer = self._load()
        return len(tokenizer.encode(text, add_special_tokens=False))

    def _load(self) -> Any:
        if self._tokenizer is not None:
            return self._tokenizer
        try:
            from transformers import AutoTokenizer

            self._tokenizer = AutoTokenizer.from_pretrained(
                self._model_id,
                revision=self._revision,
                local_files_only=True,
            )
        except Exception as error:
            raise TokenizerSetupError(
                f"Tokenizer {self.model_id!r} is unavailable locally. Download it during explicit setup."
            ) from error
        return self._tokenizer
