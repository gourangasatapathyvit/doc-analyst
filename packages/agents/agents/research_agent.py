"""Research Agent — web research specialist via Tavily."""

from agents.factory import AgentFactory
from tools.web_tools import tavily_search

RESEARCH_AGENT_PROMPT = """You are a web research specialist. Use Tavily search to find \
relevant external information.

Instructions:
- Always cite your sources with URLs
- Provide concise summaries of findings
- If the search returns no results, say so clearly
- Use multiple searches with different queries if the first attempt doesn't find enough
"""


def create_research_agent():
    return AgentFactory.create(
        name="research_agent",
        tools=[tavily_search],
        prompt=RESEARCH_AGENT_PROMPT,
    )
