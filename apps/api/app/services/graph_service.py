"""Graph Service — builds the supervisor graph and wires up tools."""

from __future__ import annotations

import structlog

from agents.pdf_agent import create_pdf_agent
from agents.registry import AgentRegistry
from agents.research_agent import create_research_agent
from agents.analyzer_agent import create_analyzer_agent
from agents.supervisor import build_supervisor
from tools.pdf_tools import configure as configure_pdf_tools, set_session_id

from app.services.checkpoint import get_checkpointer
from app.services.file_service import FileRepository
from app.services.parse_service import ParseService
from app.services.vector_service import VectorService

logger = structlog.get_logger()


def init_agents():
    """Initialize all agents, wire up tool dependencies. Called once at startup."""
    # Wire up pdf_tools with service singletons
    configure_pdf_tools(
        vector_service=VectorService(),
        parse_service=ParseService(),
        file_service=FileRepository(),
    )

    registry = AgentRegistry()

    pdf_agent = create_pdf_agent()
    registry.register(pdf_agent, "Document retrieval via RAG (search, page extraction)")

    research_agent = create_research_agent()
    registry.register(research_agent, "Web research via Tavily search")

    analyzer_agent = create_analyzer_agent()
    registry.register(analyzer_agent, "Synthesis, comparison, and explanation")

    logger.info("agents_initialized", count=registry.agent_count)


def get_supervisor_graph(session_id: str, file_ids: list[str] | None = None):
    """Build and compile the supervisor graph for a request."""
    # Set session context so pdf_tools know which LanceDB table to query
    set_session_id(session_id)

    registry = AgentRegistry()
    agents = registry.get_agents()

    file_context = (
        f"{len(file_ids)} file(s) uploaded" if file_ids else "No files uploaded"
    )

    workflow = build_supervisor(
        agents=agents,
        file_context=file_context,
        agent_descriptions=registry.get_descriptions(),
    )

    checkpointer = get_checkpointer()
    compiled = workflow.compile(checkpointer=checkpointer)

    return compiled
