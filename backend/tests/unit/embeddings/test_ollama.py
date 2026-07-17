import httpx

from app.infrastructure.embeddings import OllamaEmbedding


def test_ollama_batches_documents_and_applies_separate_instructions() -> None:
    requests: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = __import__("json").loads(request.content)
        requests.append(payload)
        inputs = payload["input"]
        return httpx.Response(200, json={"embeddings": [[float(len(text)), 1.0] for text in inputs]})

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://ollama.test")
    embedding = OllamaEmbedding(
        client=client,
        query_instruction="query: ",
        document_instruction="document: ",
    )

    documents = embedding.embed_documents(["one", "two", "three"], batch_size=2)
    query = embedding.embed_query("one")

    assert len(documents) == 3
    assert query == [10.0, 1.0]
    assert requests[0]["input"] == ["document: one", "document: two"]
    assert requests[-1]["input"] == ["query: one"]
    assert all(request["truncate"] is False for request in requests)
