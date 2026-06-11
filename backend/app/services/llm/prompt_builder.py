from app.schemas.notes import StudyNotesMode
from app.schemas.summary import SummaryMode
from app.services.rag.models import RetrievedChunk, TranscriptChunk


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


def build_summary_prompt(mode: SummaryMode, chunks: list[TranscriptChunk]) -> str:
    context = "\n".join(
        _format_chunk_context_line(index=index, chunk=chunk)
        for index, chunk in enumerate(chunks, start=1)
    )
    mode_instruction = {
        "short": (
            "Tạo đúng 5-7 gạch đầu dòng. "
            "Mỗi gạch đầu dòng là một câu hoàn chỉnh, súc tích, không bị bỏ dở."
        ),
        "detailed": (
            "Tạo summary chi tiết theo các ý chính, có cấu trúc rõ ràng. "
            "Mỗi ý phải là câu hoàn chỉnh và chỉ dùng thông tin trong transcript."
        ),
        "timeline": (
            "Tạo summary theo timeline, giữ thứ tự nội dung trong video. "
            "Mỗi dòng phải có timestamp từ transcript context và một câu hoàn chỉnh."
        ),
    }[mode]

    return f"""Bạn là trợ lý học tập tóm tắt video YouTube.
Chỉ sử dụng transcript context được cung cấp.
Không bịa thêm thông tin ngoài transcript.
Trả lời bằng tiếng Việt.
{mode_instruction}
Không tự tạo timestamp mới nếu transcript context không có mốc tương ứng.
Không viết lời mở đầu như "Dưới đây là...".
Không kết thúc bằng câu hoặc gạch đầu dòng đang dang dở.

Transcript context:
{context}

Summary:"""


def build_study_notes_prompt(
    chunks: list[TranscriptChunk],
    *,
    mode: StudyNotesMode = "concise",
    learning_goal: str | None = None,
) -> str:
    context = "\n".join(
        _format_chunk_context_line(index=index, chunk=chunk)
        for index, chunk in enumerate(chunks, start=1)
    )
    mode_instruction = {
        "concise": "Tạo notes ngắn, tập trung vào ý chính nhất.",
        "detailed": "Tạo notes chi tiết hơn nhưng vẫn tránh chép lại transcript dài.",
        "timeline": "Tạo notes theo trình tự thời gian, mỗi mục chính nên có timestamp.",
        "exam_review": "Tạo notes để ôn thi: ưu tiên định nghĩa, ý chính, câu dễ hỏi và điểm cần nhớ.",
        "beginner": "Tạo notes cho người mới học: giải thích đơn giản, tránh thuật ngữ khó nếu không cần.",
    }[mode]
    goal_instruction = (
        f"\nMục tiêu học của người dùng: {learning_goal.strip()}"
        if learning_goal and learning_goal.strip()
        else ""
    )

    return f"""Bạn là trợ lý học tập tạo study notes từ video YouTube.
Chỉ sử dụng transcript context được cung cấp.
Không bịa thêm thông tin ngoài transcript.
Trả lời bằng tiếng Việt.
{mode_instruction}{goal_instruction}
Tạo ghi chú học tập có cấu trúc sau:
- Mục tiêu bài học: 2 gạch đầu dòng.
- Khái niệm chính: 4-6 gạch đầu dòng.
- Giải thích dễ hiểu: 1 đoạn ngắn, tối đa 5 câu.
- Ví dụ hoặc chi tiết đáng chú ý trong transcript: 3 gạch đầu dòng.
- Timestamp nên xem lại: 3-5 dòng, dùng timestamp có trong transcript context.
Không viết quá dài. Không lặp lại nguyên văn transcript dài. Không tự tạo timestamp mới.
Mỗi gạch đầu dòng phải là câu hoàn chỉnh, không bị bỏ dở.

Transcript context:
{context}

Study notes:"""


def _format_context_line(index: int, item: RetrievedChunk) -> str:
    return (
        f"[{index}] "
        f"timestamp={_format_timestamp(item.chunk.start_seconds)}-"
        f"{_format_timestamp(item.chunk.end_seconds)} "
        f"score={item.score:.6f} "
        f"text={item.chunk.text}"
    )


def _format_chunk_context_line(index: int, chunk: TranscriptChunk) -> str:
    return (
        f"[{index}] "
        f"timestamp={_format_timestamp(chunk.start_seconds)}-"
        f"{_format_timestamp(chunk.end_seconds)} "
        f"text={chunk.text}"
    )


def _format_timestamp(seconds: float) -> str:
    total_seconds = max(int(seconds), 0)
    minutes = total_seconds // 60
    remaining_seconds = total_seconds % 60
    return f"{minutes:02d}:{remaining_seconds:02d}"
