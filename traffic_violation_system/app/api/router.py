from fastapi import APIRouter

from app.api.routes import auth, cameras, health, system

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(cameras.router, prefix="/cameras", tags=["cameras"])
api_router.include_router(system.router, prefix="/system", tags=["system"])
