import httpx
import pytest

from app.application.llm.contracts import (
    GenerationOptions,
    GenerationRequest,
    LlmContextOverflowError,
    LlmMessage,
    LlmTimeoutError,
)
from app.infrastructure.llm import OllamaLlmProvider


def _request() -> GenerationRequest:
    return GenerationRequest(
        messages=(LlmMessage("user", "Return grounded JSON."),),
        system_instruction="Use evidence only.",
        options=GenerationOptions(max_output_tokens=100, context_window=4_096),
        response_schema={"type": "object", "properties": {"answer": {"type": "string"}}},
    )


def test_ollama_structured_payload_usage_and_health() -> None:
    payloads: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "qwen3:4b"}]})
        payloads.append(__import__("json").loads(request.content))
        return httpx.Response(
            200,
            json={
                "model": "qwen3:4b",
                "message": {"content": '{"answer":"grounded"}'},
                "done_reason": "stop",
                "prompt_eval_count": 11,
                "eval_count": 7,
                "total_duration": 2_000_000,
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://ollama.test")
    provider = OllamaLlmProvider(client=client)

    assert provider.health_check()
    result = provider.generate(_request())

    assert payloads[0]["stream"] is False
    assert payloads[0]["keep_alive"] == "30m"
    assert payloads[0]["format"]["type"] == "object"
    assert payloads[0]["options"]["num_ctx"] == 4_096
    assert result.usage.total_tokens == 18
    assert result.duration_ms == 2


@pytest.mark.parametrize(
    ("handler", "error_type"),
    [
        (
            lambda request: (_ for _ in ()).throw(httpx.ReadTimeout("slow", request=request)),
            LlmTimeoutError,
        ),
        (
            lambda request: httpx.Response(400, json={"error": "context length exceeded"}),
            LlmContextOverflowError,
        ),
    ],
)
def test_ollama_maps_timeout_and_context_errors(handler, error_type) -> None:
    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://ollama.test")

    with pytest.raises(error_type):
        OllamaLlmProvider(client=client).generate(_request())
