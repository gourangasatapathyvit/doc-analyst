"""PDF document tools — search, page retrieval, listing.

These tools are used by pdf_agent to query the LanceDB vector index
instead of stuffing full document text into the LLM context.

Session context is set via `set_session_id()` before each chat request.
"""

from __future__ import annotations

from contextvars import ContextVar

import structlog
from langchain_core.tools import tool

logger = structlog.get_logger()

# Session context — set per-request by the API layer
_current_session_id: ContextVar[str] = ContextVar("current_session_id", default="")

# Service dependencies — injected at startup
_vector_service = None
_parse_service = None
_file_service = None


def configure(vector_service, parse_service, file_service):
    """Inject service dependencies. Called once at app startup."""
    global _vector_service, _parse_service, _file_service
    _vector_service = vector_service
    _parse_service = parse_service
    _file_service = file_service


def set_session_id(session_id: str):
    """Set the current session ID for tool calls. Called per-request."""
    _current_session_id.set(session_id)


@tool
async def search_document(query: str, top_k: int = 5) -> str:
    """Semantic search over all uploaded documents. Returns the most relevant chunks with page numbers and filenames."""
    if _vector_service is None:
        return "Error: vector service not configured. Upload a document first."

    session_id = _current_session_id.get()
    if not session_id:
        return "Error: no active session."

    results = await _vector_service.search(query, session_id=session_id, top_k=top_k)
    if not results:
        return "No relevant content found in uploaded documents."

    formatted = []
    for i, r in enumerate(results, 1):
        formatted.append(
            f"[{i}] (file: {r['filename']}, page: {r['page_number']}, "
            f"score: {r['score']:.3f})\n{r['text']}"
        )

    logger.info("pdf_search", query=query, top_k=top_k, results_count=len(results))
    return "\n\n---\n\n".join(formatted)


@tool
async def get_page(filename: str, page_number: int) -> str:
    """Get the full text of a specific page from a specific document."""
    if _parse_service is None:
        return "Error: parse service not configured."

    text = _parse_service.get_page(filename, page_number)
    if text is None:
        return f"Page {page_number} not found in {filename}."

    logger.info("pdf_get_page", filename=filename, page=page_number)
    return f"[{filename}, page {page_number}]\n\n{text}"


@tool
async def list_documents() -> str:
    """List all documents uploaded in the current session."""
    if _file_service is None:
        return "Error: file service not configured."

    files = _file_service.list_files()
    if not files:
        return "No documents uploaded yet."

    lines = []
    for f in files:
        lines.append(f"- {f['filename']} ({f['pages']} pages, {f['size_kb']:.0f} KB)")

    return "Uploaded documents:\n" + "\n".join(lines)
