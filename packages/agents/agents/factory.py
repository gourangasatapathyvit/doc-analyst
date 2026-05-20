"""Agent Factory — standardized agent creation with consistent config.

Usage:
    from agents.factory import AgentFactory

    agent = AgentFactory.create(
        name="pdf_agent",
        tools=[search_document, get_page],
        prompt="You are a document retrieval specialist...",
    )
"""

from __future__ import annotations

import os

from langchain_openai import AzureChatOpenAI
from langgraph.prebuilt import create_react_agent


def _make_llm(model: str, temperature: float = 0) -> AzureChatOpenAI:
    """Create an AzureChatOpenAI instance with consistent config."""
    # o-series models (o3, o4-mini) don't support temperature parameter
    is_o_series = model.startswith("o") and model[1:2].isdigit()

    kwargs = dict(
        azure_deployment=model,
        azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT", ""),
        api_key=os.environ.get("AZURE_OPENAI_API_KEY", ""),
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
        model_name=model,
        streaming=True,
    )
    if not is_o_series:
        kwargs["temperature"] = temperature

    return AzureChatOpenAI(**kwargs)


class AgentFactory:
    """Creates agents with consistent model and config."""

    @staticmethod
    def create(
        name: str,
        tools: list,
        prompt: str,
        model: str | None = None,
        temperature: float = 0,
    ):
        if model is None:
            model = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "o4-mini")

        llm = _make_llm(model, temperature)

        return create_react_agent(
            model=llm,
            tools=tools,
            name=name,
            prompt=prompt,
        )
