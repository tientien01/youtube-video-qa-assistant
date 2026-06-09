import logging

from app.services.llm.base import LlmClient, LlmError
from app.services.llm.config import load_llm_settings
from app.services.llm.gemini_client import GeminiClient
from app.services.llm.prompt_builder import build_grounded_answer_prompt
from app.services.rag.models import RetrievedChunk


logger = logging.getLogger(__name__)


def generate_answer(
    question: str,
    retrieved_chunks: list[RetrievedChunk],
    llm_client: LlmClient | None = None,
) -> str:
    if not retrieved_chunks:
        return _fallback_answer(question=question, retrieved_chunks=retrieved_chunks)

    client = llm_client or _build_configured_llm_client()
    if client is None:
        return _fallback_answer(question=question, retrieved_chunks=retrieved_chunks)

    prompt = build_grounded_answer_prompt(
        question=question,
        retrieved_chunks=retrieved_chunks,
    )
    try:
        generated_text = client.generate_text(prompt).strip()
    except LlmError as error:
        logger.warning("LLM generation failed, using fallback answer: %s", error)
        return _fallback_answer(question=question, retrieved_chunks=retrieved_chunks)

    if not generated_text:
        logger.warning("LLM generation returned empty text, using fallback answer")
        return _fallback_answer(question=question, retrieved_chunks=retrieved_chunks)

    return generated_text


def _build_configured_llm_client() -> LlmClient | None:
    settings = load_llm_settings()
    if settings.is_gemini_enabled and settings.gemini_api_key is not None:
        return GeminiClient(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            timeout_seconds=settings.timeout_seconds,
        )

    if settings.provider not in {"fallback", "none"}:
        logger.warning(
            "LLM provider '%s' is not configured, using fallback answer",
            settings.provider,
        )

    return None


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
