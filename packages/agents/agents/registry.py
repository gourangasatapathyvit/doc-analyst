"""Agent Registry — pluggable system for registering agents.

Usage:
    from agents.registry import AgentRegistry

    registry = AgentRegistry()
    registry.register(my_agent, "Does X and Y")
    agents = registry.get_agents()
"""

from __future__ import annotations

from typing import Any

import structlog

from core.patterns import singleton

logger = structlog.get_logger()


@singleton
class AgentRegistry:
    """Register and manage agents for the supervisor."""

    def __init__(self):
        self._agents: dict[str, dict[str, Any]] = {}

    def register(self, agent: Any, description: str) -> None:
        name = getattr(agent, "name", None) or str(agent)
        self._agents[name] = {"agent": agent, "description": description}
        logger.info("agent_registered", name=name, description=description)

    def unregister(self, name: str) -> None:
        if name in self._agents:
            del self._agents[name]
            logger.info("agent_unregistered", name=name)

    def get_agents(self) -> list[Any]:
        return [entry["agent"] for entry in self._agents.values()]

    def get_descriptions(self) -> str:
        lines = []
        for name, entry in self._agents.items():
            lines.append(f"- {name}: {entry['description']}")
        return "\n".join(lines)

    @property
    def agent_count(self) -> int:
        return len(self._agents)
