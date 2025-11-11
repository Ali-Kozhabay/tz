from fastapi import APIRouter

from app.api.routes import auth, chat, courses, invites, storage

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(courses.router)
api_router.include_router(invites.router)
api_router.include_router(storage.router)
api_router.include_router(chat.router)
