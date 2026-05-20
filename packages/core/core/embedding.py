"""Embedding Strategy pattern — swap providers without changing VectorService.

Usage:
    from core.embedding import AzureOpenAIEmbedding

    embedder = AzureOpenAIEmbedding()
    vectors = await embedder.embed(["hello world", "another text"])
"""
from __future__ import annotations

import os
from typing import Protocol

import litellm
import structlog

from core.retry import azure_ai_breaker, retryable

logger = structlog.get_logger()


class EmbeddingStrategy(Protocol):
    """Protocol for embedding providers."""

    async def embed(self, texts: list[str]) -> list[list[float]]: ...

    @property
    def dimensions(self) -> int: ...


class AzureOpenAIEmbedding:
    """Azure OpenAI text-embedding-3-large via litellm."""

    def __init__(self):
        self._model = "azure/text-embedding-3-large"
        self._api_key = os.environ.get("EMBEDDING_API_KEY", "")
        self._api_base = os.environ.get("EMBEDDING_ENDPOINT", "")
        self._dims = int(os.environ.get("EMBEDDING_DIMENSIONS", "3072"))

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
