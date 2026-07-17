from __future__ import annotations

import json
import re
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.application.llm.contracts import (
    GenerationOptions,
    GenerationRequest,
    GenerationResult,
    LlmInvalidOutputError,
    LlmMessage,
    LlmProvider,
)


class AnswerCitation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_id: str = Field(min_length=1)
    claim: str = Field(min_length=1)


class GroundedAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str = Field(min_length=1)
    citations: list[AnswerCitation]
    answer_language: str = Field(min_length=2, max_length=35)
    insufficient_evidence: bool


@dataclass(frozen=True, slots=True)
class GenerationContext:
    chunk_id: str
    text: str
    start_ms: int
    end_ms: int

    def __post_init__(self) -> None:
        if not self.chunk_id or not self.text.strip():
            raise ValueError("Generation context requires a chunk ID and text.")
        if self.start_ms < 0 or self.end_ms <= self.start_ms:
            raise ValueError("Generation context timestamps are invalid.")


@dataclass(frozen=True, slots=True)
class GroundedAnswerResult:
    answer: GroundedAnswer
    generation: GenerationResult
    repaired: bool


class GroundedAnswerService:
    def __init__(self, provider: LlmProvider, *, max_repair_attempts: int = 1) -> None:
        if max_repair_attempts not in {0, 1}:
            raise ValueError("Grounded answer repair policy is bounded to zero or one attempt.")
        self._provider = provider
        self._max_repairs = max_repair_attempts

    def health_check(self) -> bool:
        return self._provider.health_check()

    def answer(
        self,
        *,
        question: str,
        context: list[GenerationContext],
        answer_language: str | None = None,
        options: GenerationOptions | None = None,
    ) -> GroundedAnswerResult:
        if not question.strip():
            raise ValueError("Question cannot be empty.")
        language = answer_language or detect_answer_language(question)
        allowed_ids = {item.chunk_id for item in context}
        request = _answer_request(question, context, language, options or GenerationOptions())
        result = self._provider.generate(request)
        try:
            answer = _validate_answer(result.text, allowed_ids, language)
        except LlmInvalidOutputError as first_error:
            if self._max_repairs == 0:
                raise
            repair = self._provider.generate(
                _repair_request(
                    invalid_output=result.text,
                    error_message=str(first_error),
                    allowed_ids=allowed_ids,
                    language=language,
                    options=options or GenerationOptions(),
                )
            )
            answer = _validate_answer(repair.text, allowed_ids, language)
            return GroundedAnswerResult(answer=answer, generation=repair, repaired=True)
        return GroundedAnswerResult(answer=answer, generation=result, repaired=False)


def detect_answer_language(question: str, *, fallback: str = "en") -> str:
    normalized = question.casefold()
    if re.search(r"[ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]", normalized):
        return "vi"
    vietnamese_markers = {"không", "gì", "tại", "sao", "hãy", "video", "này", "trong"}
    if vietnamese_markers.intersection(re.findall(r"[^\W_]+", normalized)):
        return "vi"
    return fallback


def _answer_request(
    question: str,
    context: list[GenerationContext],
    language: str,
    options: GenerationOptions,
) -> GenerationRequest:
    evidence = (
        "\n".join(f"[{item.chunk_id}] {item.start_ms}-{item.end_ms}ms: {item.text}" for item in context)
        or "(no evidence supplied)"
    )
    prompt = (
        f"Question: {question.strip()}\n"
        f"Required answer language: {language}\n"
        "Use only the evidence below. Cite only bracketed chunk IDs. "
        "If evidence is insufficient, set insufficient_evidence=true and abstain.\n\n"
        f"Evidence:\n{evidence}"
    )
    return GenerationRequest(
        system_instruction=(
            "You are a grounded video learning assistant. Return only JSON matching the supplied schema. "
            "Keep source quotations in their original language."
        ),
        messages=(LlmMessage("user", prompt),),
        options=options,
        response_schema=GroundedAnswer.model_json_schema(),
    )


def _repair_request(
    *,
    invalid_output: str,
    error_message: str,
    allowed_ids: set[str],
    language: str,
    options: GenerationOptions,
) -> GenerationRequest:
    prompt = (
        "Repair the JSON output. Return only corrected JSON. "
        f"Validation error: {error_message}. Allowed citation IDs: {sorted(allowed_ids)}. "
        f"Required answer_language: {language}.\nInvalid output:\n{invalid_output}"
    )
    return GenerationRequest(
        system_instruction="Repair structured grounded output without adding unsupported claims.",
        messages=(LlmMessage("user", prompt),),
        options=options,
        response_schema=GroundedAnswer.model_json_schema(),
    )


def _validate_answer(text: str, allowed_ids: set[str], expected_language: str) -> GroundedAnswer:
    try:
        answer = GroundedAnswer.model_validate_json(text)
    except (ValidationError, json.JSONDecodeError) as error:
        raise LlmInvalidOutputError("Grounded answer is not valid structured JSON.") from error
    unknown = sorted({citation.chunk_id for citation in answer.citations} - allowed_ids)
    if unknown:
        raise LlmInvalidOutputError(f"Grounded answer contains unknown citation IDs: {unknown}.")
    if answer.answer_language.casefold() != expected_language.casefold():
        raise LlmInvalidOutputError(
            f"Grounded answer language {answer.answer_language!r} does not match {expected_language!r}."
        )
    if answer.insufficient_evidence and answer.citations:
        raise LlmInvalidOutputError("Insufficient-evidence answers cannot include citations.")
    return answer
