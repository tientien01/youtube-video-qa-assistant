import json
import re
from typing import cast

from app.api.contracts.generation import GenerationMetadata
from app.api.contracts.quiz import (
    GeneratedQuizQuestionType,
    QuizDifficulty,
    QuizMode,
    QuizQuestion,
    QuizQuestionType,
    QuizResponse,
    QuizSource,
)
from app.application.legacy.llm.base import LlmClient
from app.application.legacy.llm.context_budget import (
    COMPACT_DIRECT_CONTEXT_CHARS,
    compact_transcript_chunks,
    is_token_limit_failure,
)
from app.application.legacy.llm.generation import generate_optional_llm_result
from app.application.legacy.llm.prompt_builder import build_quiz_prompt
from app.application.legacy.learning.generated_output_store import generated_output_store
from app.application.legacy.learning.quiz_attempt_store import quiz_attempt_store
from app.application.legacy.rag.local_store import VideoNotIndexedError, rag_store
from app.application.legacy.rag.models import TranscriptChunk


QUIZ_OUTPUT_TYPE = "quiz"


def generate_quiz(
    *,
    video_id: str,
    question_count: int = 5,
    difficulty: QuizDifficulty = "medium",
    question_type: QuizQuestionType = "mixed",
    mode: QuizMode = "practice",
    force: bool = False,
    source_chunk_ids: list[str] | None = None,
    llm_client: LlmClient | None = None,
) -> QuizResponse:
    chunks = rag_store.get_video_chunks(video_id)
    if not chunks:
        raise VideoNotIndexedError("Video has not been indexed yet.")

    selected_source_chunk_ids = source_chunk_ids or []
    quiz_mode = mode
    cache_mode = _build_cache_mode(
        question_count=question_count,
        difficulty=difficulty,
        question_type=question_type,
        mode=quiz_mode,
        source_chunk_ids=selected_source_chunk_ids,
    )
    cached_output = generated_output_store.get_output(
        video_id=video_id,
        output_type=QUIZ_OUTPUT_TYPE,
        mode=cache_mode,
    )
    chunk_by_id = {chunk.chunk_id: chunk for chunk in chunks}

    if cached_output is not None and not force:
        questions = [
            _question_from_payload(question_payload, chunk_by_id)
            for question_payload in json.loads(cached_output.content)
            if question_payload["source_chunk_id"] in chunk_by_id
        ]
        attempt = quiz_attempt_store.add_attempt(
            video_id=video_id,
            mode=quiz_mode,
            difficulty=difficulty,
            question_type=question_type,
            question_count=len(questions),
            source_chunk_ids=[question.source.chunk_id for question in questions],
        )
        return QuizResponse(
            video_id=video_id,
            difficulty=difficulty,
            question_type=question_type,
            mode=quiz_mode,
            attempt_id=attempt.attempt_id,
            questions=questions,
            sources=_unique_sources([question.source for question in questions]),
            cached=True,
            generation=GenerationMetadata(
                generation_mode="cached",
                provider=cached_output.provider,
                fallback_reason=cached_output.fallback_reason,
            ),
        )

    source_chunks = _select_source_chunks(
        chunks=chunks,
        question_count=question_count,
        source_chunk_ids=selected_source_chunk_ids,
    )
    questions, generation = _generate_llm_quiz(
        chunks=source_chunks,
        question_count=question_count,
        difficulty=difficulty,
        question_type=question_type,
        mode=quiz_mode,
        llm_client=llm_client,
    )
    if not questions:
        questions = _build_fallback_questions(
            chunks=chunks,
            source_chunks=source_chunks,
            question_count=question_count,
            difficulty=difficulty,
            question_type=question_type,
            mode=quiz_mode,
        )

    generated_output_store.upsert_output(
        video_id=video_id,
        output_type=QUIZ_OUTPUT_TYPE,
        mode=cache_mode,
        content=json.dumps(
            [_question_to_payload(question) for question in questions],
            ensure_ascii=False,
        ),
        source_chunk_ids=[question.source.chunk_id for question in questions],
        generation_mode=generation.generation_mode,
        provider=generation.provider,
        fallback_reason=generation.fallback_reason,
    )
    attempt = quiz_attempt_store.add_attempt(
        video_id=video_id,
        mode=quiz_mode,
        difficulty=difficulty,
        question_type=question_type,
        question_count=len(questions),
        source_chunk_ids=[question.source.chunk_id for question in questions],
    )

    return QuizResponse(
        video_id=video_id,
        difficulty=difficulty,
        question_type=question_type,
        mode=quiz_mode,
        attempt_id=attempt.attempt_id,
        questions=questions,
        sources=_unique_sources([question.source for question in questions]),
        cached=False,
        generation=generation,
    )


def _build_cache_mode(
    *,
    question_count: int,
    difficulty: QuizDifficulty,
    question_type: QuizQuestionType,
    mode: QuizMode,
    source_chunk_ids: list[str],
) -> str:
    source_key = ""
    if source_chunk_ids:
        source_key = ":" + ",".join(sorted(source_chunk_ids[:8]))

    return f"{mode}:{question_type}:{difficulty}:{question_count}{source_key}"


def _select_source_chunks(
    *,
    chunks: list[TranscriptChunk],
    question_count: int,
    source_chunk_ids: list[str],
) -> list[TranscriptChunk]:
    if source_chunk_ids:
        chunks_by_id = {chunk.chunk_id: chunk for chunk in chunks}
        selected_chunks = [chunks_by_id[chunk_id] for chunk_id in source_chunk_ids if chunk_id in chunks_by_id]
        if selected_chunks:
            return selected_chunks[:question_count]

    if len(chunks) <= question_count:
        return chunks

    step = (len(chunks) - 1) / max(question_count - 1, 1)
    indexes = sorted({round(index * step) for index in range(question_count)})
    return [chunks[index] for index in indexes]


def _generate_llm_quiz(
    *,
    chunks: list[TranscriptChunk],
    question_count: int,
    difficulty: QuizDifficulty,
    question_type: QuizQuestionType,
    mode: QuizMode,
    llm_client: LlmClient | None,
) -> tuple[list[QuizQuestion], GenerationMetadata]:
    compacted_chunks = compact_transcript_chunks(
        chunks,
        max_total_chars=6500,
        max_chunk_chars=700,
    )
    prompt = build_quiz_prompt(
        chunks=compacted_chunks,
        question_count=question_count,
        difficulty=difficulty,
        question_type=question_type,
        mode=mode,
    )
    llm_result = generate_optional_llm_result(
        prompt,
        llm_client=llm_client,
        fallback_log_message="LLM quiz generation failed, using fallback quiz",
    )
    if llm_result.text is None:
        if is_token_limit_failure(llm_result.fallback_reason):
            compacted_chunks = compact_transcript_chunks(
                chunks,
                max_total_chars=COMPACT_DIRECT_CONTEXT_CHARS,
                max_chunk_chars=350,
            )
            llm_result = generate_optional_llm_result(
                build_quiz_prompt(
                    chunks=compacted_chunks,
                    question_count=question_count,
                    difficulty=difficulty,
                    question_type=question_type,
                    mode=mode,
                ),
                llm_client=llm_client,
                fallback_log_message="LLM quiz retry failed, using fallback quiz",
            )

    if llm_result.text is None:
        return [], GenerationMetadata(
            generation_mode="fallback",
            provider=llm_result.provider,
            fallback_reason=llm_result.fallback_reason,
        )

    try:
        questions = _questions_from_llm_payload(
            llm_result.text,
            chunks_by_id={chunk.chunk_id: chunk for chunk in chunks},
            question_type=question_type,
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        return [], GenerationMetadata(
            generation_mode="fallback",
            provider=llm_result.provider,
            fallback_reason=f"LLM quiz JSON could not be parsed: {error}",
        )

    return questions[:question_count], GenerationMetadata(
        generation_mode="llm",
        provider=llm_result.provider,
        fallback_reason=None,
    )


def _questions_from_llm_payload(
    text: str,
    *,
    chunks_by_id: dict[str, TranscriptChunk],
    question_type: QuizQuestionType,
) -> list[QuizQuestion]:
    payload = json.loads(_extract_json_object(text))
    raw_questions = payload.get("questions")
    if not isinstance(raw_questions, list):
        raise ValueError("Missing questions list.")

    questions = []
    for index, raw_question in enumerate(raw_questions, start=1):
        source_chunk_id = str(raw_question["source_chunk_id"])
        if source_chunk_id not in chunks_by_id:
            continue

        resolved_question_type = _coerce_generated_question_type(
            str(raw_question["question_type"]),
            requested_type=question_type,
        )
        options = list(raw_question.get("options") or [])
        if resolved_question_type == "true_false":
            options = ["Đúng", "Sai"]
        if resolved_question_type == "short_answer":
            options = []
        if resolved_question_type == "multiple_choice" and len(options) != 4:
            continue

        correct_answer = str(raw_question["correct_answer"])
        if options and correct_answer not in options:
            continue

        chunk = chunks_by_id[source_chunk_id]
        questions.append(
            QuizQuestion(
                question_id=f"{source_chunk_id}-llm-q{index}",
                question_type=resolved_question_type,
                question=str(raw_question["question"]),
                options=options,
                correct_answer=correct_answer,
                explanation=str(raw_question["explanation"]),
                source=_chunk_to_source(chunk),
            )
        )

    return questions


def _extract_json_object(text: str) -> str:
    stripped_text = text.strip()
    if stripped_text.startswith("```"):
        stripped_text = re.sub(r"^```(?:json)?", "", stripped_text).strip()
        stripped_text = re.sub(r"```$", "", stripped_text).strip()

    start = stripped_text.find("{")
    end = stripped_text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found.")

    return stripped_text[start : end + 1]


def _coerce_generated_question_type(
    generated_type: str,
    *,
    requested_type: QuizQuestionType,
) -> GeneratedQuizQuestionType:
    if requested_type in {"multiple_choice", "true_false", "short_answer"}:
        return cast(GeneratedQuizQuestionType, requested_type)

    if generated_type in {"multiple_choice", "true_false", "short_answer"}:
        return cast(GeneratedQuizQuestionType, generated_type)

    return "multiple_choice"


def _build_fallback_questions(
    *,
    chunks: list[TranscriptChunk],
    source_chunks: list[TranscriptChunk],
    question_count: int,
    difficulty: QuizDifficulty,
    question_type: QuizQuestionType,
    mode: QuizMode,
) -> list[QuizQuestion]:
    return [
        _build_question(
            chunk=chunk,
            chunks=chunks,
            index=index,
            question_type=_resolve_question_type(question_type, index, mode=mode),
            difficulty=difficulty,
        )
        for index, chunk in enumerate(source_chunks[:question_count], start=1)
    ]


def _resolve_question_type(
    question_type: QuizQuestionType,
    index: int,
    mode: QuizMode = "practice",
) -> GeneratedQuizQuestionType:
    if question_type != "mixed":
        return question_type

    if mode == "concept_check":
        return "short_answer" if index % 3 == 0 else "multiple_choice"

    if mode == "exam":
        return "multiple_choice" if index % 3 else "short_answer"

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
    source_note = _shorten_text(chunk.text, max_length=220)
    return (
        f'{difficulty_note} Đáp án dựa trên ý trong transcript: "{source_note}" '
        f"Nguồn nằm trong đoạn {_format_timestamp(chunk.start_seconds)}-{_format_timestamp(chunk.end_seconds)}."
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


def _response_mode_from_cache_mode(cache_mode: str) -> QuizMode:
    mode = cache_mode.split(":", maxsplit=1)[0]
    if mode in {"practice", "exam", "concept_check"}:
        return cast(QuizMode, mode)

    return "practice"


def _question_from_payload(
    payload: dict[str, object],
    chunk_by_id: dict[str, TranscriptChunk],
) -> QuizQuestion:
    chunk = chunk_by_id[str(payload["source_chunk_id"])]
    question_type = str(payload["question_type"])
    if question_type not in {"multiple_choice", "true_false", "short_answer"}:
        raise ValueError(f"Unsupported cached question type: {question_type}")
    raw_options = payload["options"]
    if not isinstance(raw_options, list):
        raise ValueError("Cached quiz options must be a list.")
    return QuizQuestion(
        question_id=str(payload["question_id"]),
        question_type=cast(GeneratedQuizQuestionType, question_type),
        question=str(payload["question"]),
        options=[str(option) for option in raw_options],
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
