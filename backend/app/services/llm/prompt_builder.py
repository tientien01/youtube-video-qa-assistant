from app.services.rag.models import RetrievedChunk


def build_grounded_answer_prompt(question: str, retrieved_chunks: list[RetrievedChunk]) -> str:
    context = "\n".join(
        _format_context_line(index=index, item=item)
        for index, item in enumerate(retrieved_chunks, start=1)
    )

    return f"""Bạn là trợ lý học tập giúp người dùng hiểu nội dung video YouTube.
Chỉ trả lời dựa trên transcript context được cung cấp.
Nếu transcript context không đủ thông tin, hãy nói rõ: "Mình chưa có đủ thông tin từ transcript để trả lời chắc chắn."
Không bịa thêm thông tin ngoài transcript.
Trả lời bằng tiếng Việt, ngắn gọn và dễ hiểu.
Không tự tạo timestamp mới. Timestamp nguồn sẽ được hệ thống hiển thị riêng từ retrieved chunks.

Câu hỏi:
{question.strip()}

Transcript context:
{context}

Câu trả lời:"""


def _format_context_line(index: int, item: RetrievedChunk) -> str:
    return (
        f"[{index}] "
        f"timestamp={_format_timestamp(item.chunk.start_seconds)}-"
        f"{_format_timestamp(item.chunk.end_seconds)} "
        f"score={item.score:.6f} "
        f"text={item.chunk.text}"
    )


def _format_timestamp(seconds: float) -> str:
    total_seconds = max(int(seconds), 0)
    minutes = total_seconds // 60
    remaining_seconds = total_seconds % 60
    return f"{minutes:02d}:{remaining_seconds:02d}"
