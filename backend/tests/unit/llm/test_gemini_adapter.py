import httpx

from app.application.llm.contracts import GenerationRequest, LlmMessage
from app.infrastructure.llm import GeminiLlmProvider


def test_gemini_uses_same_contract_and_keeps_payload_inside_adapter() -> None:
    captured: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(__import__("json").loads(request.content))
        return httpx.Response(
            200,
            json={
                "candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": '{"answer":"ok"}'}]}}],
                "usageMetadata": {"promptTokenCount": 5, "candidatesTokenCount": 3, "totalTokenCount": 8},
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="https://gemini.test")
    provider = GeminiLlmProvider(api_key="test-key", model="gemini-test", client=client)
    request = GenerationRequest(
        messages=(LlmMessage("user", "Answer."),),
        response_schema={"type": "object"},
    )

    result = provider.generate(request)

    assert captured[0]["generationConfig"]["responseMimeType"] == "application/json"
    assert result.provider == "gemini"
    assert result.model == "gemini-test"
    assert result.usage.total_tokens == 8
