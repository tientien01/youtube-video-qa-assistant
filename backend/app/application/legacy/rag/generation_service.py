from dataclasses import dataclass

from app.api.contracts.generation import GenerationMetadata
from app.application.legacy.llm.base import LlmClient
from app.application.legacy.llm.context_budget import (
    COMPACT_DIRECT_CONTEXT_CHARS,
    compact_retrieved_chunks,
    is_token_limit_failure,
)
from app.application.legacy.llm.generation import generate_optional_llm_result
from app.application.legacy.llm.prompt_builder import build_grounded_answer_prompt
from app.application.legacy.rag.models import RetrievedChunk
from app.application.llm.grounded_answer import detect_answer_language


@dataclass(frozen=True)
class AnswerGenerationResult:
    answer: str
    answer_language: str
    generation: GenerationMetadata


def generate_answer(
    question: str,
    retrieved_chunks: list[RetrievedChunk],
    llm_client: LlmClient | None = None,
) -> str:
    return generate_answer_with_metadata(
        question=question,
        retrieved_chunks=retrieved_chunks,
        llm_client=llm_client,
    ).answer


def generate_answer_with_metadata(
    question: str,
    retrieved_chunks: list[RetrievedChunk],
    llm_client: LlmClient | None = None,
    answer_language: str | None = None,
) -> AnswerGenerationResult:
    language = answer_language or detect_answer_language(question)
    if not retrieved_chunks:
        return AnswerGenerationResult(
            answer=_fallback_answer(question, retrieved_chunks, language),
            answer_language=language,
            generation=GenerationMetadata(
                generation_mode="fallback",
                provider="fallback",
                fallback_reason="No retrieved transcript context.",
            ),
        )

    compacted_chunks = compact_retrieved_chunks(retrieved_chunks)
    prompt = build_grounded_answer_prompt(
        question=question,
        retrieved_chunks=compacted_chunks,
        answer_language=language,
    )
    llm_result = generate_optional_llm_result(
        prompt,
        llm_client=llm_client,
        fallback_log_message="LLM answer generation failed, using fallback answer",
    )
    if llm_result.text is None and is_token_limit_failure(llm_result.fallback_reason):
        compacted_chunks = compact_retrieved_chunks(
            retrieved_chunks,
            max_total_chars=COMPACT_DIRECT_CONTEXT_CHARS,
            max_chunk_chars=450,
        )
        llm_result = generate_optional_llm_result(
            build_grounded_answer_prompt(
                question=question,
                retrieved_chunks=compacted_chunks,
                answer_language=language,
            ),
            llm_client=llm_client,
            fallback_log_message="LLM answer retry failed, using fallback answer",
        )

    if llm_result.text is not None:
        return AnswerGenerationResult(
            answer=llm_result.text,
            answer_language=language,
            generation=GenerationMetadata(
                generation_mode="llm",
                provider=llm_result.provider,
                fallback_reason=None,
            ),
        )

    return AnswerGenerationResult(
        answer=_fallback_answer(question, retrieved_chunks, language),
        answer_language=language,
        generation=GenerationMetadata(
            generation_mode="fallback",
            provider=llm_result.provider,
            fallback_reason=llm_result.fallback_reason,
        ),
    )


def _fallback_answer(
    question: str,
    retrieved_chunks: list[RetrievedChunk],
    answer_language: str,
) -> str:
    if not retrieved_chunks:
        if answer_language == "vi":
            return "Chưa tìm thấy bằng chứng transcript đủ liên quan để trả lời câu hỏi này."
        return "There is not enough relevant transcript evidence to answer this question."

    context_lines = [
        f"- [{_format_timestamp(item.chunk.start_seconds)}] {item.chunk.text}" for item in retrieved_chunks[:3]
    ]
    introduction = (
        "Dựa trên bằng chứng transcript liên quan nhất:"
        if answer_language == "vi"
        else "Based on the most relevant transcript evidence:"
    )
    question_label = "Câu hỏi" if answer_language == "vi" else "Question"
    return introduction + "\n" + "\n".join(context_lines) + f"\n\n{question_label}: {question.strip()}"


def _format_timestamp(seconds: float) -> str:
    total_seconds = max(int(seconds), 0)
    minutes = total_seconds // 60
    remaining_seconds = total_seconds % 60
    return f"{minutes:02d}:{remaining_seconds:02d}"
