from fastapi import APIRouter
from app.api.v1.endpoints import auth, documents, chat, admin, generate, folders, analytics, versions

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(generate.router, prefix="/generate", tags=["generate"])
api_router.include_router(folders.router, prefix="/folders", tags=["folders"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(versions.router, prefix="/documents", tags=["versions"])
