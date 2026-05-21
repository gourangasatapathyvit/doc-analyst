"""PostgreSQL checkpointer setup for LangGraph."""

from __future__ import annotations

from typing import Any

import structlog
from langgraph.checkpoint.memory import MemorySaver

from app.config import settings

logger = structlog.get_logger()

_checkpointer: Any = None


async def init_checkpointer() -> None:
    """Initialize the checkpointer. Called once during app lifespan startup."""
    global _checkpointer

    if settings.use_postgres_checkpointer:
        try:
            from psycopg_pool import AsyncConnectionPool

            pool = AsyncConnectionPool(
                conninfo=settings.pg_connection_string,
                open=False,
                timeout=10,
            )
            await pool.open(wait=True, timeout=10)

            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

            _checkpointer = AsyncPostgresSaver(pool)
            await _checkpointer.setup()
            logger.info("checkpointer_initialized", backend="postgres", host=settings.db_host)
            return

        except Exception as e:
            logger.warning(
                "checkpointer_postgres_failed",
                error=str(e),
                hint="Falling back to in-memory checkpointer",
            )

    _checkpointer = MemorySaver()
    logger.info("checkpointer_initialized", backend="memory")


def get_checkpointer() -> Any:
    """Get the initialized checkpointer instance."""
    if _checkpointer is None:
        return MemorySaver()
    return _checkpointer
