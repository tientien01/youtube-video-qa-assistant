from fastapi import APIRouter

from app.api.v1.routes import chat, health, video

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(video.router)
api_router.include_router(chat.router)
