from typing import Protocol


class LlmError(Exception):
    """Raised when an LLM provider cannot generate a usable response."""


class LlmClient(Protocol):
    def generate_text(self, prompt: str) -> str:
        """Generate text from a prompt."""
        ...
