"""LLM Context Window Manager — auto-detects model context limits via litellm.

Usage:
    from core.llm_context_manager import LLMContextManager

    ctx_mgr = LLMContextManager()
    usable = ctx_mgr.get_usable_tokens("o4-mini", fill_percentage=0.5)
"""
from __future__ import annotations

from typing import Optional

import litellm
import structlog

from core.patterns import singleton

logger = structlog.get_logger()


def _default_fill_pct() -> float:
    """Get the default fill percentage from config, falling back to 0.5."""
    try:
        from core.config import get_config

        return get_config().llm_fill_percentage
    except RuntimeError:
        return 0.5


@singleton
class LLMContextManager:
    """Singleton manager for LLM context window detection and token budget computation."""

    _DEFAULT_MAX_INPUT = 128_000
    _DEFAULT_MAX_OUTPUT = 16_384
    _OUTPUT_SAFETY_MARGIN = 0.8
    _OUTPUT_RESERVED_PCT = 0.10

    def __init__(self) -> None:
        self._cache: dict[str, dict] = {}

    def _lookup(self, deployment_name: str) -> dict:
        if deployment_name in self._cache:
            return self._cache[deployment_name]

        for model_key in [f"azure/{deployment_name}", deployment_name]:
            try:
                info = litellm.get_model_info(model_key)
                result = {
                    "max_input_tokens": info.get("max_input_tokens", self._DEFAULT_MAX_INPUT),
                    "max_output_tokens": info.get("max_output_tokens", self._DEFAULT_MAX_OUTPUT),
                    "model_key": model_key,
                }
                self._cache[deployment_name] = result
                logger.info(
                    "llm_context_detected",
                    deployment=deployment_name,
                    max_input=result["max_input_tokens"],
                    max_output=result["max_output_tokens"],
                )
                return result
            except Exception:
                continue

        logger.warning(
            "llm_context_fallback",
            deployment=deployment_name,
            max_input=self._DEFAULT_MAX_INPUT,
        )
        result = {
            "max_input_tokens": self._DEFAULT_MAX_INPUT,
            "max_output_tokens": self._DEFAULT_MAX_OUTPUT,
            "model_key": deployment_name,
        }
        self._cache[deployment_name] = result
        return result

    def get_max_input_tokens(self, deployment_name: str) -> int:
        return self._lookup(deployment_name)["max_input_tokens"]

    def get_max_output_tokens(self, deployment_name: str) -> int:
        return self._lookup(deployment_name)["max_output_tokens"]

    def get_usable_tokens(
        self, deployment_name: str, fill_percentage: Optional[float] = None
    ) -> int:
        pct = fill_percentage if fill_percentage is not None else _default_fill_pct()
        return int(self.get_max_input_tokens(deployment_name) * pct)

    def get_usable_output_tokens(
        self,
        deployment_name: str,
        safety_margin: Optional[float] = None,
        reserved_pct: Optional[float] = None,
    ) -> int:
        margin = safety_margin if safety_margin is not None else self._OUTPUT_SAFETY_MARGIN
        res_pct = reserved_pct if reserved_pct is not None else self._OUTPUT_RESERVED_PCT
        max_output = self.get_max_output_tokens(deployment_name)
        reserved = int(max_output * res_pct)
        return max(0, int(max_output * margin) - reserved)

    def clear_cache(self) -> None:
        self._cache.clear()
