from __future__ import annotations

import json
from collections import deque

from app.application.llm.contracts import (
    GenerationRequest,
    GenerationResult,
    GenerationUsage,
    LlmCapabilities,
)


class FakeLlmProvider:
    """Deterministic provider for application and integration tests."""

    def __init__(
        self,
        responses: list[str | dict[str, object] | Exception],
        *,
        model: str = "fake-model-v1",
        healthy: bool = True,
    ) -> None:
        self._responses = deque(responses)
        self._model = model
        self._healthy = healthy
        self.requests: list[GenerationRequest] = []

    @property
    def name(self) -> str:
        return "fake"

    @property
    def model(self) -> str:
        return self._model

    @property
    def capabilities(self) -> LlmCapabilities:
        return LlmCapabilities(streaming=False, structured_output=True, usage_metadata=True)

    def health_check(self) -> bool:
        return self._healthy

    def generate(self, request: GenerationRequest) -> GenerationResult:
        self.requests.append(request)
        if not self._responses:
            raise RuntimeError("Fake LLM response queue is empty.")
        response = self._responses.popleft()
        if isinstance(response, Exception):
            raise response
        text = json.dumps(response, ensure_ascii=False) if isinstance(response, dict) else response
        return GenerationResult(
            text=text,
            provider=self.name,
            model=self.model,
            finish_reason="stop",
            usage=GenerationUsage(input_tokens=10, output_tokens=5, total_tokens=15),
            duration_ms=1,
        )
