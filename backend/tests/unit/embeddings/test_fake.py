from app.infrastructure.embeddings import DeterministicFakeEmbedding


def test_fake_embedding_is_deterministic_normalized_and_batched() -> None:
    embedding = DeterministicFakeEmbedding(dimension=16)

    first = embedding.embed_documents(["xin chào", "hello world", "xin chào"], batch_size=2)
    second = embedding.embed_documents(["xin chào", "hello world", "xin chào"], batch_size=1)

    assert first == second
    assert first[0] == first[2]
    assert len(first[0]) == 16
    assert embedding.health_check()


def test_query_and_document_interfaces_are_separate() -> None:
    embedding = DeterministicFakeEmbedding(dimension=8)

    assert embedding.embed_query("retrieval") == embedding.embed_documents(["retrieval"])[0]
