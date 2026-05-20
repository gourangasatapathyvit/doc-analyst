"""Agent registry endpoint — returns all registered agents and their tools."""

from __future__ import annotations

from fastapi import APIRouter

from agents.registry import AgentRegistry

router = APIRouter()


@router.get("/api/agents")
async def list_agents():
    """Return all registered agents with their tools and descriptions."""
    registry = AgentRegistry()
    result = []

    for name, entry in registry._agents.items():
        agent = entry["agent"]
        tools_info = []

        try:
            for node_name, node in agent.nodes.items():
                # Tools node has .bound.tools_by_name
                bound = getattr(node, "bound", None)
                tools_by_name = getattr(bound, "tools_by_name", None)
                if tools_by_name:
                    for tool_name, tool in tools_by_name.items():
                        tools_info.append({
                            "name": tool_name,
                            "description": getattr(tool, "description", ""),
                        })
        except Exception:
            pass

        result.append({
            "name": name,
            "description": entry["description"],
            "tools": tools_info,
        })

    return {"agents": result}
