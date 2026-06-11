from app.schemas.notes import StudyNotesLength, StudyNotesMode
from app.schemas.quiz import QuizDifficulty, QuizMode, QuizQuestionType
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


def build_summary_section_prompt(
    *,
    mode: SummaryMode,
    chunks: list[TranscriptChunk],
    section_index: int,
    section_count: int,
) -> str:
    context = "\n".join(
        _format_chunk_context_line(index=index, chunk=chunk)
        for index, chunk in enumerate(chunks, start=1)
    )
    if mode == "timeline":
        output_instruction = "Create 3-5 timeline bullets. Each bullet must start with a timestamp from the context."
    elif mode == "detailed":
        output_instruction = "Create 4-6 concise bullets covering the important ideas and examples in this section."
    else:
        output_instruction = "Create 2-4 concise bullets covering only the main takeaways in this section."

    return f"""You summarize one section of a YouTube transcript.
Use only the provided transcript context. Do not invent facts or timestamps.
Answer in Vietnamese.
This is section {section_index}/{section_count}.
{output_instruction}
Keep the result compact because it will be merged with other section summaries.

Transcript context:
{context}

Section summary:"""


def build_summary_merge_prompt(mode: SummaryMode, section_summaries: list[str]) -> str:
    context = "\n\n".join(
        f"Section {index}:\n{summary.strip()}"
        for index, summary in enumerate(section_summaries, start=1)
    )
    mode_instruction = {
        "short": "Create exactly 5-7 concise bullets.",
        "detailed": "Create a structured detailed summary grouped by main ideas.",
        "timeline": "Create a timeline summary in chronological order. Keep timestamps from section summaries.",
    }[mode]

    return f"""You merge section summaries from a YouTube transcript.
Use only the section summaries below. Do not add outside information.
Answer in Vietnamese.
{mode_instruction}
Avoid repeating the same idea. Keep every sentence complete.

Section summaries:
{context}

Final summary:"""


def build_study_notes_prompt(
    chunks: list[TranscriptChunk],
    *,
    mode: StudyNotesMode = "concise",
    length: StudyNotesLength = "medium",
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
        "flashcards": "Tạo flashcards theo dạng Hỏi/Đáp, mỗi thẻ có timestamp nguồn.",
        "concept_map": "Tạo concept map dạng text: chủ đề chính -> nhánh -> ý liên quan, có timestamp nguồn.",
    }[mode]
    length_instruction = {
        "short": "Độ dài ngắn: tối đa 4 mục chính.",
        "medium": "Độ dài vừa: 5-7 mục chính.",
        "long": "Độ dài dài: 8-12 mục chính nhưng vẫn không chép transcript dài.",
    }[length]
    goal_instruction = (
        f"\nMục tiêu học của người dùng: {learning_goal.strip()}"
        if learning_goal and learning_goal.strip()
        else ""
    )

    return f"""Bạn là trợ lý học tập tạo study notes từ video YouTube.
Chỉ sử dụng transcript context được cung cấp.
Không bịa thêm thông tin ngoài transcript.
Trả lời bằng tiếng Việt.
{mode_instruction}
{length_instruction}{goal_instruction}
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


def build_study_notes_section_prompt(
    *,
    chunks: list[TranscriptChunk],
    mode: StudyNotesMode,
    length: StudyNotesLength,
    learning_goal: str | None,
    section_index: int,
    section_count: int,
) -> str:
    context = "\n".join(
        _format_chunk_context_line(index=index, chunk=chunk)
        for index, chunk in enumerate(chunks, start=1)
    )
    goal_instruction = (
        f"\nLearning goal: {learning_goal.strip()}"
        if learning_goal and learning_goal.strip()
        else ""
    )

    return f"""You create compact study notes for one section of a YouTube transcript.
Use only the provided transcript context. Do not invent facts or timestamps.
Answer in Vietnamese.
This is section {section_index}/{section_count}.
Mode: {mode}. Length target for the final notes: {length}.{goal_instruction}
Create 3-5 complete bullets. Each bullet should include a source timestamp when useful.
Keep the output compact because it will be merged with other section notes.

Transcript context:
{context}

Section notes:"""


def build_study_notes_merge_prompt(
    *,
    section_notes: list[str],
    mode: StudyNotesMode,
    length: StudyNotesLength,
    learning_goal: str | None,
) -> str:
    context = "\n\n".join(
        f"Section {index}:\n{notes.strip()}"
        for index, notes in enumerate(section_notes, start=1)
    )
    goal_instruction = (
        f"\nMục tiêu học của người dùng: {learning_goal.strip()}"
        if learning_goal and learning_goal.strip()
        else ""
    )

    return f"""Bạn là trợ lý học tập tạo study notes từ các section notes của video YouTube.
Chỉ sử dụng nội dung bên dưới. Không bịa thêm thông tin ngoài transcript.
Trả lời bằng tiếng Việt.
Mode: {mode}. Độ dài: {length}.{goal_instruction}
Tạo ghi chú học tập có cấu trúc sau:
- Mục tiêu bài học: 2 gạch đầu dòng.
- Khái niệm chính: số lượng phù hợp với độ dài đã chọn, mỗi bullet nên có timestamp [mm:ss] nếu có.
- Giải thích dễ hiểu: 1 đoạn ngắn.
- Ví dụ hoặc chi tiết đáng chú ý trong transcript: 3-5 gạch đầu dòng.
- Timestamp nên xem lại: 3-6 dòng.
Không chép lại section notes quá dài. Không tự tạo timestamp mới.

Section notes:
{context}

Study notes:"""


def build_quiz_prompt(
    *,
    chunks: list[TranscriptChunk],
    question_count: int,
    difficulty: QuizDifficulty,
    question_type: QuizQuestionType,
    mode: QuizMode,
) -> str:
    context = "\n".join(
        _format_chunk_context_line(index=index, chunk=chunk)
        for index, chunk in enumerate(chunks, start=1)
    )

    return f"""Bạn là trợ lý học tập tạo quiz từ transcript video YouTube.
Chỉ dùng transcript context được cung cấp.
Không bịa thêm ngoài transcript.
Trả lời bằng JSON hợp lệ, không markdown, không giải thích ngoài JSON.
Tạo {question_count} câu hỏi.
Độ khó: {difficulty}.
Loại câu hỏi: {question_type}.
Chế độ quiz: {mode}.
Mỗi câu phải grounded vào một source_chunk_id có trong transcript context.
Explanation phải giải thích vì sao đáp án đúng dựa trên transcript, không chỉ nói timestamp.
Nếu là multiple_choice, tạo đúng 4 options và chỉ một correct_answer.
Nếu là true_false, options phải là ["Đúng", "Sai"].
Nếu là short_answer, options là [].

JSON schema:
{{
  "questions": [
    {{
      "question_type": "multiple_choice|true_false|short_answer",
      "question": "...",
      "options": ["..."],
      "correct_answer": "...",
      "explanation": "...",
      "source_chunk_id": "..."
    }}
  ]
}}

Transcript context:
{context}

JSON:"""


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
