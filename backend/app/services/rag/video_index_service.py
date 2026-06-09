import logging

from app.schemas.chat import ChatAskResponse, ChatSource
from app.schemas.video import VideoDeleteResponse, VideoIngestResponse, VideoMetadataResponse
from app.services.extraction.transcript_service import fetch_transcript
from app.services.extraction.video_url_service import extract_youtube_video_id
from app.services.learning.generated_output_store import generated_output_store
from app.services.rag.generation_service import generate_answer
from app.services.rag.local_store import VideoNotIndexedError, rag_store
from app.services.rag.metadata_store import VideoMetadata, metadata_store
from app.services.rag.retrieval_service import RetrievalMode, retrieve_chunks
from app.services.rag.text_processing import chunk_transcript
from app.services.rag.vector_store import vector_store


logger = logging.getLogger(__name__)


def ingest_video_content(url: str) -> VideoIngestResponse:
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
            duration_seconds=metadata.duration_seconds,
            transcript_language=metadata.transcript_language,
            chunk_count=metadata.chunk_count,
            status="cached",
        )

    transcript_segments, language_code = fetch_transcript(video_id)
    chunks = chunk_transcript(video_id=video_id, segments=transcript_segments)
    rag_store.upsert_video(video_id, chunks)
    vector_store.upsert_video(video_id, chunks)

    duration_seconds = int(max(segment.end_seconds for segment in transcript_segments))
    metadata = metadata_store.upsert_video(
        video_id=video_id,
        title=f"YouTube video {video_id}",
        url=f"https://www.youtube.com/watch?v={video_id}",
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
        duration_seconds=metadata.duration_seconds,
        transcript_language=metadata.transcript_language,
        chunk_count=metadata.chunk_count,
        status="ready",
    )


def list_ingested_videos() -> list[VideoMetadataResponse]:
    return [
        _metadata_to_response(metadata)
        for metadata in metadata_store.list_videos()
    ]


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
    if not deleted_chunks and not deleted_vectors and not deleted_metadata and not deleted_outputs:
        raise VideoNotIndexedError("Video has not been indexed yet.")

    logger.info("Deleted video_id=%s from local library", video_id)
    return VideoDeleteResponse(video_id=video_id, deleted=True)


def ask_video_question(
    video_id: str,
    question: str,
    retrieval_mode: RetrievalMode = "hybrid",
) -> ChatAskResponse:
    logger.info(
        "Retrieving context for video_id=%s question_length=%s mode=%s",
        video_id,
        len(question),
        retrieval_mode,
    )
    retrieved_chunks = retrieve_chunks(
        video_id=video_id,
        question=question,
        mode=retrieval_mode,
        top_k=4,
    )
    answer = generate_answer(question=question, retrieved_chunks=retrieved_chunks)
    logger.info(
        "Generated answer for video_id=%s source_count=%s",
        video_id,
        len(retrieved_chunks),
    )

    return ChatAskResponse(
        answer=answer,
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
    )


def _metadata_to_response(metadata: VideoMetadata) -> VideoMetadataResponse:
    return VideoMetadataResponse(
        video_id=metadata.video_id,
        title=metadata.title,
        url=metadata.url,
        duration_seconds=metadata.duration_seconds,
        transcript_language=metadata.transcript_language,
        chunk_count=metadata.chunk_count,
        created_at=metadata.created_at,
        updated_at=metadata.updated_at,
    )
