"""Application settings — single source of truth for all configuration.

Satisfies the `core.config.AppConfig` protocol so all packages
can access config without importing from apps/.
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Concrete settings implementation. Satisfies core.config.AppConfig protocol."""

    # ── Azure OpenAI (LLM) ─────────────────────────────────────
    azure_openai_api_key: str = os.environ.get("AZURE_OPENAI_API_KEY", "")
    azure_openai_endpoint: str = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
    azure_openai_deployment_name: str = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "o4-mini")
    azure_openai_api_version: str = os.environ.get(
        "AZURE_OPENAI_API_VERSION", "2024-12-01-preview"
    )

    # ── Embeddings ─────────────────────────────────────────────
    embedding_endpoint: str = os.environ.get("EMBEDDING_ENDPOINT", "")
    embedding_api_key: str = os.environ.get("EMBEDDING_API_KEY", "")
    embedding_dimensions: int = int(os.environ.get("EMBEDDING_DIMENSIONS", "3072"))
    embedding_deployment: str = os.environ.get("EMBEDDING_DEPLOYMENT", "text-embedding-3-large")
    embedding_api_version: str = os.environ.get("EMBEDDING_API_VERSION", "2024-02-01")

    # ── Tavily ─────────────────────────────────────────────────
    tavily_api_key: str = os.environ.get("TAVILY_API_KEY", "")

    # ── PostgreSQL ─────────────────────────────────────────────
    db_host: str = os.environ.get("DB_HOST", "localhost")
    db_port: str = os.environ.get("DB_PORT", "5432")
    db_username: str = os.environ.get("DB_USERNAME", "admin")
    db_password: str = os.environ.get("DB_PASSWORD", "admin@123")
    langgraph_checkpoint_db: str = os.environ.get("LANGGRAPH_CHECKPOINT_DB", "langgraph_db")
    use_postgres_checkpointer: bool = (
        os.environ.get("USE_POSTGRES_CHECKPOINTER", "false").lower() == "true"
    )

    # ── Server ─────────────────────────────────────────────────
    uvicorn_host: str = os.environ.get("UVICORN_HOST", "localhost")
    uvicorn_port: int = int(os.environ.get("UVICORN_PORT", "8080"))
    cors_allowed_origins: list[str] = os.environ.get(
        "CORS_ALLOWED_ORIGINS", "http://localhost:3000"
    ).split(",")

    # ── File management ────────────────────────────────────────
    upload_dir: Path = Path(os.environ.get("UPLOAD_DIR", "./uploads"))
    lancedb_dir: Path = Path(os.environ.get("LANCEDB_DIR", "./lancedb_data"))
    max_upload_size_mb: int = int(os.environ.get("MAX_UPLOAD_SIZE_MB", "50"))
    chunk_size: int = int(os.environ.get("CHUNK_SIZE", "500"))
    chunk_overlap: int = int(os.environ.get("CHUNK_OVERLAP", "50"))

    # ── Retry / Circuit Breaker ────────────────────────────────
    retry_max_attempts: int = int(os.environ.get("RETRY_MAX_ATTEMPTS", "5"))
    retry_initial_wait: float = float(os.environ.get("RETRY_INITIAL_WAIT", "3.0"))
    retry_max_wait: float = float(os.environ.get("RETRY_MAX_WAIT", "30.0"))
    retry_jitter: float = float(os.environ.get("RETRY_JITTER", "5.0"))
    cb_fail_max: int = int(os.environ.get("CB_FAIL_MAX", "20"))
    cb_reset_timeout: int = int(os.environ.get("CB_RESET_TIMEOUT", "60"))

    # ── LLM ────────────────────────────────────────────────────
    llm_fill_percentage: float = float(os.environ.get("LLM_FILL_PERCENTAGE", "0.5"))

    # ── Langfuse ───────────────────────────────────────────────
    langfuse_public_key: str = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
    langfuse_secret_key: str = os.environ.get("LANGFUSE_SECRET_KEY", "")
    langfuse_host: str = os.environ.get("LANGFUSE_HOST", "http://localhost:3001")

    # ── Logging ────────────────────────────────────────────────
    log_level: str = os.environ.get("LOG_LEVEL", "info")
    env: str = os.environ.get("ENV", "dev")

    @property
    def pg_connection_string(self) -> str:
        password = quote_plus(self.db_password)
        return (
            f"postgresql://{self.db_username}:{password}"
            f"@{self.db_host}:{self.db_port}/{self.langgraph_checkpoint_db}"
        )

    @property
    def embedding_deployment_name(self) -> str:
        """Extract deployment name from EMBEDDING_ENDPOINT URL or use EMBEDDING_DEPLOYMENT."""
        if "/deployments/" in self.embedding_endpoint:
            return self.embedding_endpoint.split("/deployments/")[-1].rstrip("/")
        return self.embedding_deployment


settings = Settings()
