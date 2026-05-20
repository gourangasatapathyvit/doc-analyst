"""Chat endpoint — SSE streaming from LangGraph supervisor."""

from __future__ import annotations

import json

import structlog
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage

from app.services.graph_service import get_supervisor_graph
from contracts.requests import ChatRequest

logger = structlog.get_logger()

router = APIRouter()


@router.post("/api/chat")
async def chat(request: ChatRequest):
    """Send a message and receive a streaming SSE response."""
    return StreamingResponse(
        stream_agent_response(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def stream_agent_response(request: ChatRequest):
    """Stream LangGraph events as SSE."""
    graph = get_supervisor_graph(request.session_id, request.file_ids)
    config = {"configurable": {"thread_id": request.session_id}}

    logger.info(
        "chat_started",
        message_preview=request.message[:100],
        file_count=len(request.file_ids),
    )

    current_agent = None

    try:
        async for event in graph.astream_events(
            {"messages": [HumanMessage(content=request.message)]},
            config=config,
            version="v2",
        ):
            kind = event.get("event", "")
            name = event.get("name", "")

            # Agent handoff — detect when a new agent starts
            if kind == "on_chain_start" and name in (
                "pdf_agent",
                "research_agent",
                "analyzer_agent",
            ):
                if current_agent != name:
                    if current_agent:
                        yield _sse("agent_end", {"agent": current_agent})
                    current_agent = name
                    yield _sse("agent_start", {"agent": name})
                    logger.info("agent_handoff", agent=name)

            # Streaming tokens
            elif kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk", None)
                if chunk and hasattr(chunk, "content") and chunk.content:
                    yield _sse(
                        "token",
                        {
                            "content": chunk.content,
                            "agent": current_agent or "supervisor",
                        },
                    )

        if current_agent:
            yield _sse("agent_end", {"agent": current_agent})

    except Exception as e:
        logger.error("chat_error", error=str(e))
        yield _sse("error", {"message": str(e)})

    yield _sse("done", {})
    logger.info("chat_completed")


def _sse(event_type: str, data: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
