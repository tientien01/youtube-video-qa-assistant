from app.services.rag.models import RetrievedChunk


def generate_answer(question: str, retrieved_chunks: list[RetrievedChunk]) -> str:
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
