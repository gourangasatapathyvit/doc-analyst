"""Web search tools — Tavily API integration."""

from __future__ import annotations

import structlog
from langchain_core.tools import tool
from tavily import AsyncTavilyClient

from core.config import get_config
from core.retry import retryable, tavily_breaker

logger = structlog.get_logger()

_client: AsyncTavilyClient | None = None


def _get_client() -> AsyncTavilyClient:
    global _client
    if _client is None:
        config = get_config()
        _client = AsyncTavilyClient(api_key=config.tavily_api_key)
    return _client


@tool
async def tavily_search(query: str, max_results: int = 5) -> str:
    """Search the web using Tavily API. Returns titles, URLs, and content snippets."""
    client = _get_client()

    @retryable(label="tavily_search", breaker=tavily_breaker)
    async def _search() -> dict:
        return await client.search(query=query, max_results=max_results)

    try:
        response = await _search()
    except Exception as e:
        logger.error("tavily_search_failed", query=query, error=str(e))
        return f"Web search failed: {e}"

    results = response.get("results", [])
    if not results:
        return f"No web results found for: {query}"

    formatted = []
    for r in results:
        formatted.append(f"**{r['title']}**\n{r['url']}\n{r.get('content', '')[:500]}")

    logger.info("tavily_search", query=query, results_count=len(results))
    return "\n\n---\n\n".join(formatted)
