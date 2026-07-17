from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal, Protocol


class LlmErrorCode(StrEnum):
    UNAVAILABLE = "unavailable"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    INVALID_OUTPUT = "invalid_output"
    CONTEXT_OVERFLOW = "context_overflow"


class LlmError(RuntimeError):
    code: LlmErrorCode

    def __init__(self, message: str) -> None:
        super().__init__(message)


class LlmUnavailableError(LlmError):
    code = LlmErrorCode.UNAVAILABLE


class LlmTimeoutError(LlmError):
    code = LlmErrorCode.TIMEOUT


class LlmRateLimitError(LlmError):
    code = LlmErrorCode.RATE_LIMIT


class LlmInvalidOutputError(LlmError):
    code = LlmErrorCode.INVALID_OUTPUT


class LlmContextOverflowError(LlmError):
    code = LlmErrorCode.CONTEXT_OVERFLOW


@dataclass(frozen=True, slots=True)
class LlmCapabilities:
    streaming: bool
    structured_output: bool
    usage_metadata: bool


@dataclass(frozen=True, slots=True)
class LlmMessage:
    role: Literal["user", "assistant"]
    content: str

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise ValueError("LLM message content cannot be empty.")


@dataclass(frozen=True, slots=True)
class GenerationOptions:
    temperature: float = 0.0
    max_output_tokens: int = 2048
    timeout_seconds: float = 60.0
    context_window: int | None = None

    def __post_init__(self) -> None:
        if not 0 <= self.temperature <= 2:
            raise ValueError("Temperature must be between 0 and 2.")
        if self.max_output_tokens <= 0 or self.timeout_seconds <= 0:
            raise ValueError("Generation token and timeout limits must be positive.")
        if self.context_window is not None and self.context_window <= 0:
            raise ValueError("Context window must be positive when configured.")


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    messages: tuple[LlmMessage, ...]
    system_instruction: str | None = None
    options: GenerationOptions = field(default_factory=GenerationOptions)
    response_schema: dict[str, object] | None = None

    def __post_init__(self) -> None:
        if not self.messages:
            raise ValueError("Generation request requires at least one message.")


@dataclass(frozen=True, slots=True)
class GenerationUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class GenerationResult:
    text: str
    provider: str
    model: str
    finish_reason: str | None = None
    usage: GenerationUsage = field(default_factory=GenerationUsage)
    duration_ms: int | None = None

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise LlmInvalidOutputError("LLM provider returned empty output.")


class LlmProvider(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def model(self) -> str: ...

    @property
    def capabilities(self) -> LlmCapabilities: ...

    def health_check(self) -> bool: ...

    def generate(self, request: GenerationRequest) -> GenerationResult: ...
