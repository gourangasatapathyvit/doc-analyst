"""Analysis tools — instructor-backed structured outputs.

The analyzer_agent is LLM-only (no external tools), but these tools
are available for future agents that need structured analysis output.
"""

from __future__ import annotations

from typing import Any

import instructor
import litellm
import structlog
from langchain_core.tools import tool
from pydantic import BaseModel

from core.config import get_config

logger = structlog.get_logger()


class ComparisonResult(BaseModel):
    """Structured comparison output."""

    summary: str
    similarities: list[str]
    differences: list[str]
    verdict: str


_instructor_client: Any = None


def _get_instructor_client() -> Any:
    global _instructor_client
    if _instructor_client is None:
        _instructor_client = instructor.from_litellm(litellm.acompletion)
    return _instructor_client


@tool
async def compare_topics(topic_a: str, topic_b: str, context: str = "") -> str:
    """Compare two topics using structured analysis. Returns a formatted comparison."""
    client = _get_instructor_client()
    config = get_config()

    model = f"azure/{config.azure_openai_deployment_name}"

    try:
        result = await client.create(
            model=model,
            response_model=ComparisonResult,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Compare the following two topics:\n\n"
                        f"Topic A: {topic_a}\n\n"
                        f"Topic B: {topic_b}\n\n"
                        f"Additional context: {context}"
                    ),
                }
            ],
            api_key=config.azure_openai_api_key,
            api_base=config.azure_openai_endpoint,
            api_version=config.azure_openai_api_version,
        )

        output = f"## Comparison\n\n{result.summary}\n\n"
        output += "### Similarities\n" + "\n".join(f"- {s}" for s in result.similarities)
        output += "\n\n### Differences\n" + "\n".join(f"- {d}" for d in result.differences)
        output += f"\n\n### Verdict\n{result.verdict}"

        logger.info("compare_topics", topic_a=topic_a[:50], topic_b=topic_b[:50])
        return output

    except Exception as e:
        logger.error("compare_topics_failed", error=str(e))
        return f"Comparison failed: {e}"
