from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class SentenceSpan:
    """A sentence boundary expressed against the exact input string."""

    text: str
    start_char: int
    end_char: int

    def __post_init__(self) -> None:
        if self.start_char < 0 or self.end_char <= self.start_char:
            raise ValueError("Sentence span is invalid.")


class SentenceSegmenter(Protocol):
    def segment(self, text: str, language_code: str) -> tuple[SentenceSpan, ...]: ...


class TokenCounter(Protocol):
    @property
    def model_id(self) -> str: ...

    def count(self, text: str) -> int: ...
