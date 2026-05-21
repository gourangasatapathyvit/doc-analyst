"""Langfuse tracing — creates callback handlers for LangGraph."""

from __future__ import annotations

import structlog

from app.config import settings

logger = structlog.get_logger()

_langfuse_available = False

try:
    from langfuse.callback import CallbackHandler as LangfuseCallbackHandler

    _langfuse_available = True
except ImportError:
    logger.info("langfuse_not_installed", hint="pip install langfuse for LLM tracing")


def get_langfuse_handler(
    session_id: str = "",
    user_id: str = "",
    trace_name: str = "chat",
) -> object | None:
    """Create a Langfuse callback handler for a single chat request.

    Returns None if Langfuse is not configured or not installed.
    Each call creates a new handler = new trace in Langfuse.
    """
    if not _langfuse_available:
        return None

    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        return None

    try:
        handler = LangfuseCallbackHandler(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
            session_id=session_id,
            user_id=user_id,
            trace_name=trace_name,
        )
        return handler
    except Exception as e:
        logger.warning("langfuse_handler_failed", error=str(e))
        return None
