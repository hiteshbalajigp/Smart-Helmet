from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config.settings import get_settings
from app.database.init_db import initialize_application_database
from app.services.pipeline_orchestrator import PipelineOrchestrator
from app.utils.logging_config import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)
settings = get_settings()
orchestrator = PipelineOrchestrator()


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_application_database()
    orchestrator.start()
    logger.info("Application startup complete.")
    yield
    orchestrator.stop()
    logger.info("Application shutdown complete.")


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": settings.app_name, "docs": "/docs"}


@app.get("/health")
def root_health_check() -> dict[str, str]:
    return {"status": "ok", "service": "traffic-violation-system"}
