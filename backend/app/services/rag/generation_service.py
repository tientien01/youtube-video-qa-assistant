from dataclasses import dataclass

from app.schemas.generation import GenerationMetadata
from app.services.llm.base import LlmClient
from app.services.llm.generation import generate_optional_llm_result
from app.services.llm.prompt_builder import build_grounded_answer_prompt
from app.services.rag.models import RetrievedChunk


@dataclass(frozen=True)
class AnswerGenerationResult:
    answer: str
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
) -> AnswerGenerationResult:
    if not retrieved_chunks:
        return AnswerGenerationResult(
            answer=_fallback_answer(question=question, retrieved_chunks=retrieved_chunks),
            generation=GenerationMetadata(
                generation_mode="fallback",
                provider="fallback",
                fallback_reason="No retrieved transcript context.",
            ),
        )

    prompt = build_grounded_answer_prompt(
        question=question,
        retrieved_chunks=retrieved_chunks,
    )
    llm_result = generate_optional_llm_result(
        prompt,
        llm_client=llm_client,
        fallback_log_message="LLM answer generation failed, using fallback answer",
    )
    if llm_result.text is not None:
        return AnswerGenerationResult(
            answer=llm_result.text,
            generation=GenerationMetadata(
                generation_mode="llm",
                provider=llm_result.provider,
                fallback_reason=None,
            ),
        )

    return AnswerGenerationResult(
        answer=_fallback_answer(question=question, retrieved_chunks=retrieved_chunks),
        generation=GenerationMetadata(
            generation_mode="fallback",
            provider=llm_result.provider,
            fallback_reason=llm_result.fallback_reason,
        ),
    )


def _fallback_answer(question: str, retrieved_chunks: list[RetrievedChunk]) -> str:
    if not retrieved_chunks:
        return (
            "Mình chưa tìm thấy đoạn transcript đủ liên quan để trả lời câu hỏi này. "
            "Bạn có thể hỏi cụ thể hơn hoặc kiểm tra lại video đã được ingest chưa."
        )

    context_lines = [
        f"- [{_format_timestamp(item.chunk.start_seconds)}] {item.chunk.text}"
        for item in retrieved_chunks[:3]
    ]

    return (
        "Dựa trên các đoạn transcript liên quan nhất, câu trả lời có thể rút ra như sau:\n"
        + "\n".join(context_lines)
        + f"\n\nCâu hỏi gốc: {question.strip()}"
    )


def _format_timestamp(seconds: float) -> str:
    total_seconds = max(int(seconds), 0)
    minutes = total_seconds // 60
    remaining_seconds = total_seconds % 60
    return f"{minutes:02d}:{remaining_seconds:02d}"
