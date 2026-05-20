"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_chat import router as chat_router
from app.api.routes_health import router as health_router
from app.api.routes_upload import router as upload_router
from app.config import settings
from app.logging_config import setup_logging
from app.middleware.request_context import RequestContextMiddleware
from app.services.checkpoint import init_checkpointer
from app.services.graph_service import init_agents


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    setup_logging(settings.env)
    await init_checkpointer()
    init_agents()
    yield


app = FastAPI(
    title="Document Analyst API",
    version="0.1.0",
    lifespan=lifespan,
)

# Middleware
app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(health_router)
app.include_router(upload_router)
app.include_router(chat_router)
