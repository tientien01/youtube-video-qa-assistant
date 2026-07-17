from dataclasses import dataclass

from app.application.chunking.ports import SentenceSpan


@dataclass(frozen=True)
class WhitespaceTokenCounter:
    model_id: str = "test/whitespace-v1"

    def count(self, text: str) -> int:
        return len(text.split())


class PunctuationSegmenter:
    def segment(self, text: str, language_code: str) -> tuple[SentenceSpan, ...]:
        del language_code
        spans: list[SentenceSpan] = []
        start = 0
        for index, character in enumerate(text):
            if character in ".!?。！？":
                end = index + 1
                spans.append(SentenceSpan(text[start:end].strip(), start, end))
                start = end
                while start < len(text) and text[start].isspace():
                    start += 1
        if start < len(text):
            spans.append(SentenceSpan(text[start:].strip(), start, len(text)))
        return tuple(spans)
