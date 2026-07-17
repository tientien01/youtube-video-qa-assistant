import pytest

from app.application.llm.contracts import LlmInvalidOutputError, LlmTimeoutError
from app.application.llm.grounded_answer import GenerationContext, GroundedAnswerService
from app.infrastructure.llm import FakeLlmProvider


def _context() -> list[GenerationContext]:
    return [GenerationContext("chunk-1", "The evidence is grounded.", 0, 1_000)]


def _answer(*, chunk_id: str = "chunk-1", language: str = "en") -> dict[str, object]:
    return {
        "answer": "A grounded answer.",
        "citations": [{"chunk_id": chunk_id, "claim": "The evidence is grounded."}],
        "answer_language": language,
        "insufficient_evidence": False,
    }


def test_fake_provider_drives_application_and_reports_metadata() -> None:
    provider = FakeLlmProvider([_answer()], model="fake-bilingual-v1")

    result = GroundedAnswerService(provider).answer(question="What is grounded?", context=_context())

    assert result.answer.citations[0].chunk_id == "chunk-1"
    assert result.generation.provider == "fake"
    assert result.generation.model == "fake-bilingual-v1"
    assert result.generation.usage.total_tokens == 15
    assert provider.requests[0].response_schema is not None


def test_invalid_json_is_repaired_once() -> None:
    provider = FakeLlmProvider(["not-json", _answer()])

    result = GroundedAnswerService(provider).answer(question="What?", context=_context())

    assert result.repaired
    assert len(provider.requests) == 2
    assert "Repair the JSON output" in provider.requests[1].messages[0].content


def test_unknown_citation_cannot_pass_after_bounded_repair() -> None:
    provider = FakeLlmProvider([_answer(chunk_id="unknown"), _answer(chunk_id="still-unknown")])

    with pytest.raises(LlmInvalidOutputError, match="unknown citation IDs"):
        GroundedAnswerService(provider).answer(question="What?", context=_context())

    assert len(provider.requests) == 2


def test_explicit_language_overrides_detection_and_vietnamese_is_detected() -> None:
    detected = GroundedAnswerService(FakeLlmProvider([_answer(language="vi")])).answer(
        question="Video này nói gì?",
        context=_context(),
    )
    overridden = GroundedAnswerService(FakeLlmProvider([_answer(language="en")])).answer(
        question="Video này nói gì?",
        context=_context(),
        answer_language="en",
    )

    assert detected.answer.answer_language == "vi"
    assert overridden.answer.answer_language == "en"


def test_typed_provider_errors_propagate_without_fallback() -> None:
    provider = FakeLlmProvider([LlmTimeoutError("fixture timeout")])

    with pytest.raises(LlmTimeoutError, match="fixture timeout"):
        GroundedAnswerService(provider).answer(question="What?", context=_context())
