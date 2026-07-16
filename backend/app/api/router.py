from fastapi import APIRouter

from app.api.v1.routes import chat, debug, health, ingest_jobs, notes, quiz, summary, video


api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(video.router)
api_router.include_router(ingest_jobs.router)
api_router.include_router(summary.router)
api_router.include_router(notes.router)
api_router.include_router(quiz.router)
api_router.include_router(chat.router)
api_router.include_router(debug.router)
