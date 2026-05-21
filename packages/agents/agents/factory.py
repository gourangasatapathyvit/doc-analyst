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

from typing import Any

from langchain_openai import AzureChatOpenAI
from langgraph.prebuilt import create_react_agent

from core.config import get_config


def _make_llm(model: str, temperature: float = 0) -> AzureChatOpenAI:
    """Create an AzureChatOpenAI instance with consistent config."""
    config = get_config()

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
        kwargs["temperature"] = temperature

    return AzureChatOpenAI(**kwargs)


class AgentFactory:
    """Creates agents with consistent model and config."""

    @staticmethod
    def create(
        name: str,
        tools: list[Any],
        prompt: str,
        model: str | None = None,
        temperature: float = 0,
    ) -> Any:
        if model is None:
            config = get_config()
            model = config.azure_openai_deployment_name

        llm = _make_llm(model, temperature)

        return create_react_agent(
            model=llm,
            tools=tools,
            name=name,
            prompt=prompt,
        )
