"""Analyzer Agent — synthesis and reasoning specialist.

Has no external tools — uses pure LLM reasoning over conversation context.
"""

from agents.factory import AgentFactory

ANALYZER_AGENT_PROMPT = """You are an analysis specialist. Synthesize information from \
the conversation to provide clear comparisons, explanations, and summaries.

Instructions:
- When explaining technical terms, use simple language
- Structure your responses with clear headings and bullet points
- Always reference the source of information (which agent provided it)
- If you need more information, say what's missing
"""


def create_analyzer_agent():
    return AgentFactory.create(
        name="analyzer_agent",
        tools=[],
        prompt=ANALYZER_AGENT_PROMPT,
    )
