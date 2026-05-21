"""Embedding Strategy pattern — swap providers without changing VectorService.

Usage:
    from core.embedding import AzureOpenAIEmbedding

    embedder = AzureOpenAIEmbedding()
    vectors = await embedder.embed(["hello world", "another text"])
"""
from __future__ import annotations

from typing import Protocol

import litellm
import structlog

from core.config import get_config
from core.retry import azure_ai_breaker, retryable

logger = structlog.get_logger()


class EmbeddingStrategy(Protocol):
    """Protocol for embedding providers."""

    async def embed(self, texts: list[str]) -> list[list[float]]: ...

    @property
    def dimensions(self) -> int: ...


class AzureOpenAIEmbedding:
    """Azure OpenAI text-embedding-3-large via litellm."""

    def __init__(self) -> None:
        config = get_config()
        self._model = "azure/text-embedding-3-large"
        self._api_key = config.embedding_api_key
        self._api_base = config.embedding_endpoint
        self._dims = config.embedding_dimensions

    @property
    def dimensions(self) -> int:
        return self._dims

    @retryable(label="embedding", breaker=azure_ai_breaker)
    async def embed(self, texts: list[str]) -> list[list[float]]:
        response = await litellm.aembedding(
            model=self._model,
            input=texts,
            api_key=self._api_key,
            api_base=self._api_base,
            dimensions=self._dims,
        )
        return [item["embedding"] for item in response.data]
