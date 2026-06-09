import json

from app.schemas.quiz import (
    GeneratedQuizQuestionType,
    QuizDifficulty,
    QuizQuestion,
    QuizQuestionType,
    QuizResponse,
    QuizSource,
)
from app.services.learning.generated_output_store import generated_output_store
from app.services.rag.local_store import VideoNotIndexedError, rag_store
from app.services.rag.models import TranscriptChunk


QUIZ_OUTPUT_TYPE = "quiz"


def generate_quiz(
    *,
    video_id: str,
    question_count: int = 5,
    difficulty: QuizDifficulty = "medium",
    question_type: QuizQuestionType = "mixed",
) -> QuizResponse:
    chunks = rag_store.get_video_chunks(video_id)
    if not chunks:
        raise VideoNotIndexedError("Video has not been indexed yet.")

    mode = _build_cache_mode(
        question_count=question_count,
        difficulty=difficulty,
        question_type=question_type,
    )
    cached_output = generated_output_store.get_output(
        video_id=video_id,
        output_type=QUIZ_OUTPUT_TYPE,
        mode=mode,
    )
    chunk_by_id = {chunk.chunk_id: chunk for chunk in chunks}

    if cached_output is not None:
        questions = [
            _question_from_payload(question_payload, chunk_by_id)
            for question_payload in json.loads(cached_output.content)
            if question_payload["source_chunk_id"] in chunk_by_id
        ]
        return QuizResponse(
            video_id=video_id,
            difficulty=difficulty,
            question_type=question_type,
            questions=questions,
            sources=_unique_sources([question.source for question in questions]),
            cached=True,
        )

    source_chunks = _select_source_chunks(chunks, question_count)
    questions = [
        _build_question(
            chunk=chunk,
            chunks=chunks,
            index=index,
            question_type=_resolve_question_type(question_type, index),
            difficulty=difficulty,
        )
        for index, chunk in enumerate(source_chunks, start=1)
    ]
    generated_output_store.upsert_output(
        video_id=video_id,
        output_type=QUIZ_OUTPUT_TYPE,
        mode=mode,
        content=json.dumps(
            [_question_to_payload(question) for question in questions],
            ensure_ascii=False,
        ),
        source_chunk_ids=[question.source.chunk_id for question in questions],
    )

    return QuizResponse(
        video_id=video_id,
        difficulty=difficulty,
        question_type=question_type,
        questions=questions,
        sources=_unique_sources([question.source for question in questions]),
        cached=False,
    )


def _build_cache_mode(
    *,
    question_count: int,
    difficulty: QuizDifficulty,
    question_type: QuizQuestionType,
) -> str:
    return f"{question_type}:{difficulty}:{question_count}"


def _select_source_chunks(chunks: list[TranscriptChunk], question_count: int) -> list[TranscriptChunk]:
    selected_chunks: list[TranscriptChunk] = []
    for index in range(question_count):
        selected_chunks.append(chunks[index % len(chunks)])

    return selected_chunks


def _resolve_question_type(
    question_type: QuizQuestionType,
    index: int,
) -> GeneratedQuizQuestionType:
    if question_type != "mixed":
        return question_type

    return "multiple_choice" if index % 2 else "true_false"


def _build_question(
    *,
    chunk: TranscriptChunk,
    chunks: list[TranscriptChunk],
    index: int,
    question_type: GeneratedQuizQuestionType,
    difficulty: QuizDifficulty,
) -> QuizQuestion:
    source = _chunk_to_source(chunk)
    answer = _shorten_text(chunk.text, max_length=180)

    if question_type == "true_false":
        return QuizQuestion(
            question_id=f"{chunk.chunk_id}-q{index}",
            question_type="true_false",
            question=f"Đúng hay sai: đoạn transcript tại {_format_timestamp(chunk.start_seconds)} có nhắc đến ý sau?",
            options=["Đúng", "Sai"],
            correct_answer="Đúng",
            explanation=_build_explanation(chunk, difficulty),
            source=source,
        )

    if question_type == "short_answer":
        return QuizQuestion(
            question_id=f"{chunk.chunk_id}-q{index}",
            question_type="short_answer",
            question=f"Nêu ý chính của đoạn transcript tại {_format_timestamp(chunk.start_seconds)}.",
            options=[],
            correct_answer=answer,
            explanation=_build_explanation(chunk, difficulty),
            source=source,
        )

    options = _build_multiple_choice_options(chunk=chunk, chunks=chunks, index=index)
    return QuizQuestion(
        question_id=f"{chunk.chunk_id}-q{index}",
        question_type="multiple_choice",
        question=f"Đâu là ý chính của đoạn transcript tại {_format_timestamp(chunk.start_seconds)}?",
        options=options,
        correct_answer=answer,
        explanation=_build_explanation(chunk, difficulty),
        source=source,
    )


def _build_multiple_choice_options(
    *,
    chunk: TranscriptChunk,
    chunks: list[TranscriptChunk],
    index: int,
) -> list[str]:
    correct_answer = _shorten_text(chunk.text, max_length=180)
    options = [correct_answer]
    for other_chunk in chunks:
        if other_chunk.chunk_id == chunk.chunk_id:
            continue
        option = _shorten_text(other_chunk.text, max_length=180)
        if option not in options:
            options.append(option)
        if len(options) == 4:
            break

    fallback_options = [
        "Đoạn này giới thiệu một chủ đề không xuất hiện trong transcript.",
        "Đoạn này chỉ chứa thông tin kỹ thuật của hệ thống.",
        "Đoạn này không có nội dung học tập cần ghi nhớ.",
    ]
    for option in fallback_options:
        if len(options) == 4:
            break
        if option not in options:
            options.append(option)

    rotation = index % len(options)
    options = options[rotation:] + options[:rotation]
    return options


def _build_explanation(chunk: TranscriptChunk, difficulty: QuizDifficulty) -> str:
    difficulty_note = {
        "easy": "Câu hỏi tập trung vào nhận diện ý chính trực tiếp trong transcript.",
        "medium": "Câu hỏi yêu cầu đối chiếu ý chính với đoạn transcript nguồn.",
        "hard": "Câu hỏi yêu cầu hiểu ý chính và xem lại nguồn để tránh nhầm với đoạn khác.",
    }[difficulty]
    return (
        f"{difficulty_note} Nguồn nằm trong đoạn "
        f"{_format_timestamp(chunk.start_seconds)}-{_format_timestamp(chunk.end_seconds)}."
    )


def _question_to_payload(question: QuizQuestion) -> dict[str, object]:
    return {
        "question_id": question.question_id,
        "question_type": question.question_type,
        "question": question.question,
        "options": question.options,
        "correct_answer": question.correct_answer,
        "explanation": question.explanation,
        "source_chunk_id": question.source.chunk_id,
    }


def _question_from_payload(
    payload: dict[str, object],
    chunk_by_id: dict[str, TranscriptChunk],
) -> QuizQuestion:
    chunk = chunk_by_id[str(payload["source_chunk_id"])]
    return QuizQuestion(
        question_id=str(payload["question_id"]),
        question_type=payload["question_type"],
        question=str(payload["question"]),
        options=list(payload["options"]),
        correct_answer=str(payload["correct_answer"]),
        explanation=str(payload["explanation"]),
        source=_chunk_to_source(chunk),
    )


def _unique_sources(sources: list[QuizSource]) -> list[QuizSource]:
    unique_by_chunk_id: dict[str, QuizSource] = {}
    for source in sources:
        unique_by_chunk_id.setdefault(source.chunk_id, source)

    return list(unique_by_chunk_id.values())


def _chunk_to_source(chunk: TranscriptChunk) -> QuizSource:
    return QuizSource(
        chunk_id=chunk.chunk_id,
        text=chunk.text,
        start_seconds=chunk.start_seconds,
        end_seconds=chunk.end_seconds,
    )


def _shorten_text(text: str, max_length: int) -> str:
    normalized_text = " ".join(text.split())
    if len(normalized_text) <= max_length:
        return normalized_text

    return f"{normalized_text[: max_length - 3].rstrip()}..."


def _format_timestamp(seconds: float) -> str:
    total_seconds = max(int(seconds), 0)
    minutes = total_seconds // 60
    remaining_seconds = total_seconds % 60
    return f"{minutes:02d}:{remaining_seconds:02d}"
