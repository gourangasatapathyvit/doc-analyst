"""Chat endpoint — SSE streaming from LangGraph supervisor."""

from __future__ import annotations

import json
import re

import structlog
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage

from app.services.graph_service import get_supervisor_graph
from app.services.langfuse_service import get_langfuse_handler, flush_langfuse
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

    langfuse_handler = get_langfuse_handler()
    config = {
        "configurable": {"thread_id": request.session_id},
        "callbacks": [langfuse_handler] if langfuse_handler else [],
    }

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

            # Agent handoff
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

            # Tool call start
            elif kind == "on_tool_start":
                tool_input = event.get("data", {}).get("input", {})
                clean_input = _clean_tool_input(name, tool_input)
                yield _sse("tool_start", {
                    "tool": name,
                    "agent": current_agent or "supervisor",
                    "input": clean_input,
                })

            # Tool call end
            elif kind == "on_tool_end":
                tool_output = event.get("data", {}).get("output", "")
                clean_output = _clean_tool_output(name, tool_output)
                yield _sse("tool_end", {
                    "tool": name,
                    "agent": current_agent or "supervisor",
                    "output": clean_output,
                })

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
    flush_langfuse()
    logger.info("chat_completed")


def _sse(event_type: str, data: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


def _clean_tool_input(tool_name: str, raw_input) -> str:
    if tool_name.startswith("transfer_to_"):
        target = tool_name.replace("transfer_to_", "")
        return f"Routing to {target}"

    if isinstance(raw_input, dict):
        clean = {k: v for k, v in raw_input.items() if v}
        if not clean:
            return ""
        return json.dumps(clean)

    return _truncate(str(raw_input), 300)


def _clean_tool_output(tool_name: str, raw_output) -> str:
    if tool_name.startswith("transfer_to_"):
        target = tool_name.replace("transfer_to_", "").replace("_", " ")
        return f"Transferred to {target}"

    if hasattr(raw_output, "content"):
        output_str = str(raw_output.content)
    else:
        output_str = str(raw_output)

    if output_str.startswith("Command("):
        goto_match = re.search(r"goto='(\w+)'", output_str)
        if goto_match:
            return f"Transferred to {goto_match.group(1).replace('_', ' ')}"
        return "Agent handoff completed"

    return _truncate(output_str, 500)


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."
