"""Langfuse tracing — v4 uses langfuse.langchain.CallbackHandler.

Pass the handler via config={"callbacks": [handler]} to LangGraph.
Auto-captures all LLM calls, tool calls, and agent handoffs.
"""

from __future__ import annotations

from typing import Any

import structlog

from app.config import settings

logger = structlog.get_logger()

# Module-level imports with graceful fallback
try:
    from langfuse import get_client as _get_langfuse_client
except ImportError:
    _get_langfuse_client = None

try:
    from langfuse.langchain import CallbackHandler as _LangfuseCallbackHandler
except ImportError:
    _LangfuseCallbackHandler = None


def get_langfuse_handler() -> Any:
    """Create a Langfuse LangChain callback handler.

    Returns None if Langfuse is not configured or not installed.
    Each call creates a new handler = new trace.
    """
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        return None

    if _LangfuseCallbackHandler is None:
        return None

    try:
        handler = _LangfuseCallbackHandler()
        return handler
    except Exception as e:
        logger.warning("langfuse_handler_failed", error=str(e))
        return None


def init_langfuse() -> None:
    """Verify Langfuse connection at startup."""
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        logger.info("langfuse_disabled", hint="No LANGFUSE keys in .env")
        return

    if _get_langfuse_client is None:
        logger.warning("langfuse_init_failed", error="langfuse package not installed")
        return

    try:
        lf = _get_langfuse_client()
        ok = lf.auth_check()
        logger.info("langfuse_initialized", auth_ok=ok, host=settings.langfuse_host)
    except Exception as e:
        logger.warning("langfuse_init_failed", error=str(e))


def flush_langfuse() -> None:
    """Flush pending traces."""
    if _get_langfuse_client is None:
        return

    try:
        lf = _get_langfuse_client()
        lf.flush()
    except Exception:
        pass
