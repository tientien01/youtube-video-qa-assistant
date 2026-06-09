from time import perf_counter

from fastapi import APIRouter, HTTPException, status

from app.schemas.debug import RetrievalDebugChunk, RetrievalDebugRequest, RetrievalDebugResponse
from app.services.rag.local_store import VideoNotIndexedError
from app.services.rag.retrieval_service import retrieve_chunks


router = APIRouter(prefix="/debug", tags=["debug"])


@router.post(
    "/retrieve",
    response_model=RetrievalDebugResponse,
    status_code=status.HTTP_200_OK,
)
def debug_retrieve(request: RetrievalDebugRequest) -> RetrievalDebugResponse:
    question = request.question.strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty.",
        )

    started_at = perf_counter()
    try:
        retrieved_chunks = retrieve_chunks(
            video_id=request.video_id.strip(),
            question=question,
            mode=request.retrieval_mode,
            top_k=request.top_k,
        )
    except VideoNotIndexedError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

    latency_ms = round((perf_counter() - started_at) * 1000, 3)
    return RetrievalDebugResponse(
        video_id=request.video_id.strip(),
        question=question,
        retrieval_mode=request.retrieval_mode,
        top_k=request.top_k,
        latency_ms=latency_ms,
        chunks=[
            RetrievalDebugChunk(
                chunk_id=item.chunk.chunk_id,
                text=item.chunk.text,
                start_seconds=item.chunk.start_seconds,
                end_seconds=item.chunk.end_seconds,
                score=item.score,
            )
            for item in retrieved_chunks
        ],
    )
