"""Shared configuration protocol for the doc-analyst monorepo.

Packages depend on this protocol. The API app provides the concrete implementation
via `core.config.set_config()` at startup. This avoids packages importing from apps/.

Usage in packages:
    from core.config import get_config
    config = get_config()
    config.azure_openai_endpoint  # type-safe access

Usage in apps/api (at startup):
    from core.config import set_config
    set_config(settings)  # settings is the concrete Settings instance
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class AppConfig(Protocol):
    """Configuration protocol that all packages can depend on."""

    # Azure OpenAI
    azure_openai_api_key: str
    azure_openai_endpoint: str
    azure_openai_deployment_name: str
    azure_openai_api_version: str

    # Embeddings
    embedding_endpoint: str
    embedding_api_key: str
    embedding_dimensions: int

    # Tavily
    tavily_api_key: str

    # Chunking
    chunk_size: int
    chunk_overlap: int

    # Retry / Circuit Breaker
    retry_max_attempts: int
    retry_initial_wait: float
    retry_max_wait: float
    retry_jitter: float
    cb_fail_max: int
    cb_reset_timeout: int

    # LLM
    llm_fill_percentage: float

    # Langfuse
    langfuse_public_key: str
    langfuse_secret_key: str
    langfuse_host: str


_config: AppConfig | None = None


def set_config(config: AppConfig) -> None:
    """Set the global config. Called once at app startup."""
    global _config
    _config = config


def get_config() -> AppConfig:
    """Get the global config. Raises if not initialized."""
    if _config is None:
        raise RuntimeError(
            "Config not initialized. Call core.config.set_config(settings) at startup."
        )
    return _config
