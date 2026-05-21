"""Supervisor — top-level orchestrator that routes to specialist agents.

Usage:
    from agents.supervisor import build_supervisor

    graph = build_supervisor(agents=[pdf_agent, research_agent, analyzer_agent])
    app = graph.compile(checkpointer=checkpointer)
"""

from __future__ import annotations

from typing import Any

from langchain_openai import AzureChatOpenAI
from langgraph_supervisor import create_supervisor

from core.config import get_config

SUPERVISOR_PROMPT = """You are a document analyst assistant that coordinates specialist agents.

Available agents:
{agent_descriptions}

Instructions:
- Route user queries to the most appropriate agent(s)
- For questions about uploaded documents, start with pdf_agent
- For questions needing external context, use research_agent
- For synthesis, comparison, or explanation, use analyzer_agent
- You may chain agents: e.g. pdf_agent → analyzer_agent
- Always provide a complete answer — don't leave partial responses

The user has uploaded these files: {file_context}
"""


def build_supervisor(
    agents: list[Any],
    file_context: str = "No files uploaded",
    agent_descriptions: str = "",
) -> Any:
    """Build the supervisor graph from a list of agents."""
    config = get_config()

    model = config.azure_openai_deployment_name

    # o-series models (o3, o4-mini) don't support temperature parameter
    is_o_series = model.startswith("o") and model[1:2].isdigit()

    kwargs: dict[str, Any] = dict(
        azure_deployment=model,
        azure_endpoint=config.azure_openai_endpoint,
        api_key=config.azure_openai_api_key,
        api_version=config.azure_openai_api_version,
        model_name=model,
        streaming=True,
    )
    if not is_o_series:
        kwargs["temperature"] = 0

    llm = AzureChatOpenAI(**kwargs)

    prompt = SUPERVISOR_PROMPT.format(
        agent_descriptions=agent_descriptions,
        file_context=file_context,
    )

    workflow = create_supervisor(
        agents=agents,
        model=llm,
        prompt=prompt,
        output_mode="full_history",
    )

    return workflow
