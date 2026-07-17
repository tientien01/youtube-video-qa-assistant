import json
from pathlib import Path

import pytest

from app.application.legacy.rag.generation_service import generate_answer_with_metadata
from app.application.legacy.rag.models import RetrievedChunk, TranscriptChunk
from app.application.llm.grounded_answer import detect_answer_language


BACKEND_ROOT = Path(__file__).resolve().parents[3]


class _LanguageAwareLlm:
    def __init__(self) -> None:
        self.prompt = ""

    def generate_text(self, prompt: str) -> str:
        self.prompt = prompt
        return "Câu trả lời có căn cứ." if "Answer in Vietnamese." in prompt else "A grounded answer."


@pytest.mark.parametrize(
    ("question", "source_text", "explicit_language", "expected_language"),
    [
        ("Ôn tập ngắt quãng là gì?", "Nguồn tiếng Việt nguyên bản.", None, "vi"),
        ("What does retrieval do?", "Original English source.", None, "en"),
        ("Vì sao RRF hữu ích?", "Original English evidence about RRF.", "en", "en"),
        ("Why is active recall useful?", "Bằng chứng tiếng Việt về truy hồi.", "vi", "vi"),
    ],
    ids=["vi-to-vi", "en-to-en", "vi-to-en", "en-to-vi"],
)
def test_answer_language_policy_preserves_original_evidence(
    question: str,
    source_text: str,
    explicit_language: str | None,
    expected_language: str,
) -> None:
    source = TranscriptChunk("chunk-1", "video-1", source_text, 12.25, 19.75)
    retrieved = RetrievedChunk(source, 0.95)
    llm = _LanguageAwareLlm()

    result = generate_answer_with_metadata(
        question,
        [retrieved],
        llm_client=llm,
        answer_language=explicit_language,
    )

    assert result.answer_language == expected_language
    assert f"Answer in {'Vietnamese' if expected_language == 'vi' else 'English'}." in llm.prompt
    assert source.text == source_text
    assert (source.start_seconds, source.end_seconds) == (12.25, 19.75)
    assert source_text in llm.prompt


def test_uncertain_detection_uses_session_then_product_fallback() -> None:
    assert detect_answer_language("12345 ?", fallback="vi") == "vi"
    assert detect_answer_language("12345 ?") == "en"


def test_approved_retrieval_report_covers_all_language_directions_at_gate() -> None:
    dataset = json.loads((BACKEND_ROOT / "evaluation/datasets/local-v1-v1.json").read_text(encoding="utf-8"))
    report = json.loads((BACKEND_ROOT / "evaluation/reports/local-v1.json").read_text(encoding="utf-8"))
    directions = {
        (question["question_language"], question["source_language"])
        for question in dataset["questions"]
        if not question["unanswerable"]
    }

    assert {("vi", "vi"), ("en", "en"), ("vi", "en"), ("en", "vi")} <= directions
    assert all(question["review"]["status"] == "reviewed" for question in dataset["questions"])
    recommendation = report["recommendation"]
    assert recommendation["variant_id"] == "fixed_word|BAAI/bge-m3|rrf"
    assert recommendation["quality"]["recall_at_k"] == 1.0
    assert recommendation["quality"]["hit_rate_at_k"] == 1.0
