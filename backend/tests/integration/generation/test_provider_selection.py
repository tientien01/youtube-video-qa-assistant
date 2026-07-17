import httpx
import pytest

from app.application.llm.contracts import GenerationRequest, LlmMessage, LlmUnavailableError
from app.infrastructure.llm import OllamaLlmProvider
from app.infrastructure.llm.factory import LlmConfigurationError, LlmProviderConfig, create_llm_provider


def test_provider_selection_is_explicit_and_never_falls_back_to_paid_provider() -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"models": []})),
        base_url="http://local.test",
    )

    provider = create_llm_provider(
        LlmProviderConfig(provider="ollama", model="qwen3:8b", gemini_api_key="paid-key-present"),
        client=client,
    )

    assert provider.name == "ollama"
    assert provider.model == "qwen3:8b"
    with pytest.raises(LlmConfigurationError, match="API_KEY is missing"):
        create_llm_provider(LlmProviderConfig(provider="gemini", model="gemini-2.5-flash"))


def test_ollama_unavailable_is_generation_only_and_explicit() -> None:
    retrieval_state = {"healthy": True}

    def unavailable(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    client = httpx.Client(transport=httpx.MockTransport(unavailable), base_url="http://ollama.test")
    provider = OllamaLlmProvider(client=client)

    assert not provider.health_check()
    with pytest.raises(LlmUnavailableError, match="unavailable"):
        provider.generate(GenerationRequest(messages=(LlmMessage("user", "Answer."),)))
    assert retrieval_state["healthy"]
