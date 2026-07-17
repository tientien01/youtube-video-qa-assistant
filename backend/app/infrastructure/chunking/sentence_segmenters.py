from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from app.application.chunking.ports import SentenceSpan


_SENTENCE_END = re.compile(r".+?(?:[.!?。！？]+(?=\s|$)|$)", re.DOTALL)
_SUPPORTED_LANGUAGES = frozenset({"vi", "en"})


class SentenceSegmenterSetupError(RuntimeError):
    """Raised when explicit local Stanza setup has not been completed."""


class RegexSentenceSegmenter:
    """Deterministic configured fallback; source segments remain the safety boundary."""

    def segment(self, text: str, language_code: str) -> tuple[SentenceSpan, ...]:
        del language_code
        spans: list[SentenceSpan] = []
        for match in _SENTENCE_END.finditer(text):
            start, end = match.span()
            while start < end and text[start].isspace():
                start += 1
            while end > start and text[end - 1].isspace():
                end -= 1
            if start < end:
                spans.append(SentenceSpan(text[start:end], start, end))
        return tuple(spans)


class StanzaSentenceSegmenter:
    """Cached Stanza adapter that never downloads models during an ingest call."""

    def __init__(self, *, fallback: RegexSentenceSegmenter | None = None) -> None:
        self._fallback = fallback

    def segment(self, text: str, language_code: str) -> tuple[SentenceSpan, ...]:
        language = language_code.casefold().split("-", maxsplit=1)[0]
        if language not in _SUPPORTED_LANGUAGES:
            raise SentenceSegmenterSetupError(
                f"Stanza sentence segmentation supports only vi/en, received {language_code!r}."
            )
        try:
            pipeline = _stanza_pipeline(language)
            document = pipeline(text)
            spans = tuple(
                SentenceSpan(sentence.text, int(sentence.tokens[0].start_char), int(sentence.tokens[-1].end_char))
                for sentence in document.sentences
                if sentence.tokens
            )
        except Exception as error:
            if self._fallback is not None:
                return self._fallback.segment(text, language)
            raise SentenceSegmenterSetupError(
                "Stanza and its local language model are required for sentence segmentation. "
                "Install the chunking dependency and run `python -m stanza.download vi` and "
                "`python -m stanza.download en` during setup, or configure RegexSentenceSegmenter fallback."
            ) from error
        return spans


@lru_cache(maxsize=2)
def _stanza_pipeline(language: str) -> Any:
    try:
        import stanza
    except ImportError as error:
        raise SentenceSegmenterSetupError("The optional `stanza` package is not installed.") from error
    return stanza.Pipeline(
        lang=language,
        processors="tokenize",
        download_method=stanza.DownloadMethod.NONE,
        use_gpu=False,
        verbose=False,
    )
