from fastapi import APIRouter

from app.api.api_v1.endpoints import session, chat, download

# Create main API router
api_router = APIRouter()

# Include specific endpoint routers
api_router.include_router(session.router, prefix="/session", tags=["session"])
api_router.include_router(chat.router, prefix="/session", tags=["chat"])
api_router.include_router(download.router, prefix="/session", tags=["download"])
