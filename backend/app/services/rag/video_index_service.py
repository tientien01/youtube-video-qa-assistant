import logging
from collections.abc import Callable

from app.application.ingest.ports import IngestAttemptReport
from app.application.ingest.transcript import TranscriptAcquisition, TranscriptAcquisitionError
from app.infrastructure.ingest.transcript.runtime import acquire_transcript
from app.schemas.chat import ChatAskResponse, ChatHistoryDeleteResponse, ChatHistoryResponse, ChatSource
from app.schemas.transcript import TranscriptSegment
from app.schemas.video import VideoDeleteResponse, VideoIngestResponse, VideoMetadataResponse, VideoRebuildIndexResponse
from app.services.extraction.video_url_service import extract_youtube_video_id
from app.services.extraction.youtube_metadata_service import fetch_youtube_metadata
from app.services.learning.generated_output_store import generated_output_store
from app.services.chat_history_store import chat_history_store
from app.services.rag.generation_service import generate_answer_with_metadata
from app.services.rag.local_store import VideoNotIndexedError, rag_store
from app.services.rag.metadata_store import VideoMetadata, metadata_store
from app.services.rag.retrieval_service import RetrievalMode, retrieve_chunks
from app.services.rag.text_processing import chunk_transcript
from app.services.rag.vector_store import vector_store


logger = logging.getLogger(__name__)


def fetch_transcript(
    video_id: str,
    *,
    acquisition: TranscriptAcquisition | None = None,
    attempt_collector: Callable[[tuple[IngestAttemptReport, ...]], None] | None = None,
) -> tuple[list[TranscriptSegment], str]:
    """Bridge typed acquisition into the legacy chunking input shape."""

    if acquisition is None:
        try:
            acquisition = acquire_transcript(video_id)
        except TranscriptAcquisitionError as error:
            if attempt_collector is not None:
                attempt_collector(error.attempts)
            raise
    if attempt_collector is not None:
        attempt_collector(acquisition.attempts)
    return (
        [
            TranscriptSegment(
                text=segment.text,
                start_seconds=segment.start_ms / 1000,
                end_seconds=segment.end_ms / 1000,
            )
            for segment in acquisition.document.segments
        ],
        acquisition.document.language_code,
    )


def ingest_video_content(
    url: str,
    *,
    transcript_acquisition: TranscriptAcquisition | None = None,
    transcript_attempt_collector: Callable[[tuple[IngestAttemptReport, ...]], None] | None = None,
) -> VideoIngestResponse:
    video_id = extract_youtube_video_id(url)
    logger.info("Starting ingest for video_id=%s", video_id)

    if rag_store.has_video(video_id):
        chunk_count = rag_store.get_video_chunk_count(video_id)
        if not vector_store.has_video(video_id):
            vector_store.upsert_video(video_id, rag_store.get_video_chunks(video_id))
        metadata = metadata_store.get_video(video_id)
        if metadata is None:
            metadata = metadata_store.upsert_video(
                video_id=video_id,
                title=f"YouTube video {video_id}",
                url=f"https://www.youtube.com/watch?v={video_id}",
                channel_title=None,
                thumbnail_url=None,
                duration_seconds=None,
                transcript_language=None,
                chunk_count=chunk_count,
            )
        logger.info(
            "Using cached ingest for video_id=%s chunk_count=%s",
            video_id,
            chunk_count,
        )
        return VideoIngestResponse(
            video_id=metadata.video_id,
            title=metadata.title,
            url=metadata.url,
            channel_title=metadata.channel_title,
            thumbnail_url=metadata.thumbnail_url,
            duration_seconds=metadata.duration_seconds,
            transcript_language=metadata.transcript_language,
            chunk_count=metadata.chunk_count,
            status="cached",
        )

    transcript_segments, language_code = fetch_transcript(
        video_id,
        acquisition=transcript_acquisition,
        attempt_collector=transcript_attempt_collector,
    )
    chunks = chunk_transcript(video_id=video_id, segments=transcript_segments)
    rag_store.upsert_video(video_id, chunks)
    vector_store.upsert_video(video_id, chunks)

    video_url = f"https://www.youtube.com/watch?v={video_id}"
    youtube_metadata = fetch_youtube_metadata(video_url)
    duration_seconds = youtube_metadata.duration_seconds
    if duration_seconds is None:
        duration_seconds = int(max(segment.end_seconds for segment in transcript_segments))
    metadata = metadata_store.upsert_video(
        video_id=video_id,
        title=youtube_metadata.title or f"YouTube video {video_id}",
        url=video_url,
        channel_title=youtube_metadata.channel_title,
        thumbnail_url=youtube_metadata.thumbnail_url,
        duration_seconds=duration_seconds,
        transcript_language=language_code,
        chunk_count=len(chunks),
    )
    logger.info(
        "Completed ingest for video_id=%s chunk_count=%s language=%s",
        video_id,
        len(chunks),
        language_code,
    )

    return VideoIngestResponse(
        video_id=metadata.video_id,
        title=metadata.title,
        url=metadata.url,
        channel_title=metadata.channel_title,
        thumbnail_url=metadata.thumbnail_url,
        duration_seconds=metadata.duration_seconds,
        transcript_language=metadata.transcript_language,
        chunk_count=metadata.chunk_count,
        status="ready",
    )


def list_ingested_videos() -> list[VideoMetadataResponse]:
    return [_metadata_to_response(metadata) for metadata in metadata_store.list_videos()]


def get_ingested_video(video_id: str) -> VideoMetadataResponse:
    metadata = metadata_store.get_video(video_id)
    if metadata is None:
        raise VideoNotIndexedError("Video has not been indexed yet.")

    return _metadata_to_response(metadata)


def delete_ingested_video(video_id: str) -> VideoDeleteResponse:
    deleted_chunks = rag_store.delete_video(video_id)
    deleted_vectors = vector_store.delete_video(video_id)
    deleted_metadata = metadata_store.delete_video(video_id)
    deleted_outputs = generated_output_store.delete_video(video_id)
    deleted_chat_history = chat_history_store.delete_video(video_id)
    if (
        not deleted_chunks
        and not deleted_vectors
        and not deleted_metadata
        and not deleted_outputs
        and not deleted_chat_history
    ):
        raise VideoNotIndexedError("Video has not been indexed yet.")

    logger.info("Deleted video_id=%s from local library", video_id)
    return VideoDeleteResponse(video_id=video_id, deleted=True)


def rebuild_video_index(video_id: str) -> VideoRebuildIndexResponse:
    chunks = rag_store.get_video_chunks(video_id)
    if not chunks:
        raise VideoNotIndexedError("Video has not been indexed yet.")

    vector_store.upsert_video(video_id, chunks)
    logger.info("Rebuilt vector index for video_id=%s chunk_count=%s", video_id, len(chunks))
    return VideoRebuildIndexResponse(
        video_id=video_id,
        rebuilt=True,
        chunk_count=len(chunks),
    )


def ask_video_question(
    video_id: str,
    question: str,
    retrieval_mode: RetrievalMode = "hybrid",
    source_chunk_ids: list[str] | None = None,
) -> ChatAskResponse:
    logger.info(
        "Retrieving context for video_id=%s question_length=%s mode=%s",
        video_id,
        len(question),
        retrieval_mode,
    )
    retrieved_chunks = _retrieve_chat_context(
        video_id=video_id,
        question=question,
        retrieval_mode=retrieval_mode,
        source_chunk_ids=source_chunk_ids or [],
    )
    groundedness_warning = _groundedness_warning(retrieved_chunks)
    if groundedness_warning:
        generation_result = _build_low_confidence_generation(groundedness_warning)
    else:
        generation_result = generate_answer_with_metadata(question=question, retrieved_chunks=retrieved_chunks)
    logger.info(
        "Generated answer for video_id=%s source_count=%s",
        video_id,
        len(retrieved_chunks),
    )

    response = ChatAskResponse(
        answer=generation_result.answer,
        retrieval_mode=retrieval_mode,
        sources=[
            ChatSource(
                chunk_id=item.chunk.chunk_id,
                text=item.chunk.text,
                start_seconds=item.chunk.start_seconds,
                end_seconds=item.chunk.end_seconds,
                score=item.score,
            )
            for item in retrieved_chunks
        ],
        generation=generation_result.generation,
        groundedness_warning=groundedness_warning,
    )
    stored_message = chat_history_store.add_message(
        video_id=video_id,
        question=question,
        answer=response.answer,
        retrieval_mode=retrieval_mode,
        sources=response.sources,
        generation=response.generation,
        groundedness_warning=groundedness_warning,
    )
    return response.model_copy(update={"message_id": stored_message.message_id})


def list_video_chat_history(video_id: str) -> ChatHistoryResponse:
    if not rag_store.has_video(video_id):
        raise VideoNotIndexedError("Video has not been indexed yet.")

    return ChatHistoryResponse(
        video_id=video_id,
        messages=chat_history_store.list_messages(video_id),
    )


def delete_video_chat_history(video_id: str) -> ChatHistoryDeleteResponse:
    if not rag_store.has_video(video_id):
        raise VideoNotIndexedError("Video has not been indexed yet.")

    deleted = chat_history_store.delete_video(video_id)
    return ChatHistoryDeleteResponse(video_id=video_id, deleted=deleted)


def _metadata_to_response(metadata: VideoMetadata) -> VideoMetadataResponse:
    return VideoMetadataResponse(
        video_id=metadata.video_id,
        title=metadata.title,
        url=metadata.url,
        channel_title=metadata.channel_title,
        thumbnail_url=metadata.thumbnail_url,
        duration_seconds=metadata.duration_seconds,
        transcript_language=metadata.transcript_language,
        chunk_count=metadata.chunk_count,
        created_at=metadata.created_at,
        updated_at=metadata.updated_at,
    )


def _retrieve_chat_context(
    *,
    video_id: str,
    question: str,
    retrieval_mode: RetrievalMode,
    source_chunk_ids: list[str],
) -> list:
    if source_chunk_ids:
        chunks_by_id = {chunk.chunk_id: chunk for chunk in rag_store.get_video_chunks(video_id)}
        selected_chunks = [chunks_by_id[chunk_id] for chunk_id in source_chunk_ids if chunk_id in chunks_by_id]
        if selected_chunks:
            from app.services.rag.models import RetrievedChunk

            return [RetrievedChunk(chunk=chunk, score=1.0) for chunk in selected_chunks[:4]]

    return retrieve_chunks(
        video_id=video_id,
        question=question,
        mode=retrieval_mode,
        top_k=4,
    )


def _groundedness_warning(retrieved_chunks: list) -> str | None:
    if not retrieved_chunks:
        return "Không tìm thấy transcript context đủ liên quan để trả lời chắc chắn."

    max_score = max(item.score for item in retrieved_chunks)
    if max_score < 0.08:
        return "Độ liên quan của transcript context thấp, nên câu trả lời có thể không đủ chắc chắn."

    return None


def _build_low_confidence_generation(reason: str):
    from app.schemas.generation import GenerationMetadata
    from app.services.rag.generation_service import AnswerGenerationResult

    return AnswerGenerationResult(
        answer="Mình chưa có đủ thông tin từ transcript để trả lời chắc chắn. Bạn có thể thử hỏi cụ thể hơn hoặc chọn một timestamp/chunk liên quan.",
        generation=GenerationMetadata(
            generation_mode="fallback",
            provider="groundedness-check",
            fallback_reason=reason,
        ),
    )
