from fastapi import APIRouter
from backend.router.upload import router as upload_router
from backend.router.chat import router as chat_router

router = APIRouter()
router.include_router(upload_router, tags=["upload"])
router.include_router(chat_router, tags=["chat"])
