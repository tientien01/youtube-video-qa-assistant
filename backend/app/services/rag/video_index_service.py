from app.schemas.chat import ChatAskResponse, ChatSource
from app.schemas.video import VideoIngestResponse
from app.services.extraction.transcript_service import fetch_transcript
from app.services.extraction.video_url_service import extract_youtube_video_id
from app.services.rag.generation_service import generate_answer
from app.services.rag.local_store import rag_store
from app.services.rag.text_processing import chunk_transcript


def ingest_video_content(url: str) -> VideoIngestResponse:
    video_id = extract_youtube_video_id(url)
    transcript_segments, language_code = fetch_transcript(video_id)
    chunks = chunk_transcript(video_id=video_id, segments=transcript_segments)
    rag_store.upsert_video(video_id, chunks)

    duration_seconds = int(max(segment.end_seconds for segment in transcript_segments))

    return VideoIngestResponse(
        video_id=video_id,
        title=f"YouTube video {video_id}",
        url=f"https://www.youtube.com/watch?v={video_id}",
        duration_seconds=duration_seconds,
        transcript_language=language_code,
        chunk_count=len(chunks),
        status="ready",
    )


def ask_video_question(video_id: str, question: str) -> ChatAskResponse:
    retrieved_chunks = rag_store.retrieve(video_id=video_id, question=question, top_k=4)
    answer = generate_answer(question=question, retrieved_chunks=retrieved_chunks)

    return ChatAskResponse(
        answer=answer,
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
