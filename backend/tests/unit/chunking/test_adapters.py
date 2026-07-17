import pytest

from app.infrastructure.chunking import sentence_segmenters
from app.infrastructure.chunking.sentence_segmenters import (
    RegexSentenceSegmenter,
    SentenceSegmenterSetupError,
    StanzaSentenceSegmenter,
)


def test_regex_fallback_returns_exact_character_spans() -> None:
    text = "Hello world. Xin chào Việt Nam!"

    spans = RegexSentenceSegmenter().segment(text, "vi")

    assert [text[item.start_char : item.end_char] for item in spans] == ["Hello world.", "Xin chào Việt Nam!"]


def test_stanza_unsupported_language_has_actionable_error() -> None:
    with pytest.raises(SentenceSegmenterSetupError, match="supports only vi/en"):
        StanzaSentenceSegmenter().segment("Bonjour.", "fr")


def test_stanza_unavailability_can_use_configured_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    def unavailable(language: str):
        raise SentenceSegmenterSetupError(f"missing {language}")

    monkeypatch.setattr(sentence_segmenters, "_stanza_pipeline", unavailable)

    spans = StanzaSentenceSegmenter(fallback=RegexSentenceSegmenter()).segment("Hello. Xin chào!", "vi")

    assert [span.text for span in spans] == ["Hello.", "Xin chào!"]
