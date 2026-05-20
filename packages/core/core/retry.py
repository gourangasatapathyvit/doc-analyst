"""Centralised retry + circuit-breaker for transient network errors.

Retry (tenacity):
    Layer 1 -- Exception TYPES for clean, safe matching.
    Layer 2 -- String fallback for edge cases.

Circuit breaker (pybreaker) -- one per external service:
    CLOSED  -- normal traffic
    OPEN    -- after CB_FAIL_MAX consecutive transient failures
    HALF-OPEN -- allows 1 probe call

Public API:
    retryable(...)          -- decorator for sync/async functions
    retry_call_async(...)   -- one-shot wrapper for async calls
    is_transient(exc)       -- True if exc matches either layer
    azure_ai_breaker        -- circuit breaker for Azure OpenAI
    tavily_breaker          -- circuit breaker for Tavily
    db_breaker              -- circuit breaker for PostgreSQL

Usage:
    from core.retry import retryable, azure_ai_breaker

    @retryable(label="llm_call", breaker=azure_ai_breaker)
    async def call_llm(messages): ...
"""
from __future__ import annotations

import asyncio
import os
import socket

import pybreaker
import structlog
from tenacity import (
    AsyncRetrying,
    retry,
    retry_if_exception,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Retry defaults (all overridable via .env)
# ---------------------------------------------------------------------------
DEFAULT_MAX_ATTEMPTS: int = int(os.environ.get("RETRY_MAX_ATTEMPTS", "5"))
DEFAULT_INITIAL_WAIT: float = float(os.environ.get("RETRY_INITIAL_WAIT", "3.0"))
DEFAULT_MAX_WAIT: float = float(os.environ.get("RETRY_MAX_WAIT", "30.0"))
DEFAULT_JITTER: float = float(os.environ.get("RETRY_JITTER", "5.0"))

CB_FAIL_MAX: int = int(os.environ.get("CB_FAIL_MAX", "20"))
CB_RESET_TIMEOUT: int = int(os.environ.get("CB_RESET_TIMEOUT", "60"))

# ---------------------------------------------------------------------------
# Layer 1 -- transient exception TYPES
# ---------------------------------------------------------------------------
_type_list: list[type] = [
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
    InterruptedError,
    BlockingIOError,
    socket.gaierror,
    socket.herror,
]

try:
    import httpcore as _hc

    _type_list += [_hc.ConnectError, _hc.ReadTimeout, _hc.ConnectTimeout, _hc.RemoteProtocolError]
except ImportError:
    pass

try:
    import httpx as _hx

    _type_list += [
        _hx.ConnectError,
        _hx.ReadTimeout,
        _hx.ConnectTimeout,
        _hx.RemoteProtocolError,
    ]
except ImportError:
    pass

try:
    import openai as _oai

    _type_list += [
        _oai.RateLimitError,
        _oai.APITimeoutError,
        _oai.APIConnectionError,
        _oai.InternalServerError,
    ]
except ImportError:
    pass

TRANSIENT_EXCEPTIONS: tuple[type, ...] = tuple(_type_list)

# ---------------------------------------------------------------------------
# Layer 2 -- string fallback for edge cases
# ---------------------------------------------------------------------------
_TRANSIENT_MSG_FRAGMENTS = (
    "forcibly closed",
    "winerror 10054",
    "network is unreachable",
    "connection timed out",
    "429",
    "too many requests",
    "503",
    "service unavailable",
    "server is busy",
    "temporarily unavailable",
    "retry after",
)


def _is_transient_by_message(exc: BaseException) -> bool:
    return any(f in str(exc).lower() for f in _TRANSIENT_MSG_FRAGMENTS)


def is_transient(exc: BaseException) -> bool:
    """True when exc is transient (either layer)."""
    return isinstance(exc, TRANSIENT_EXCEPTIONS) or _is_transient_by_message(exc)


TRANSIENT_RETRY_CONDITION = retry_if_exception_type(TRANSIENT_EXCEPTIONS) | retry_if_exception(
    _is_transient_by_message
)


# ---------------------------------------------------------------------------
# Circuit breakers
# ---------------------------------------------------------------------------
class _BreakerListener(pybreaker.CircuitBreakerListener):
    def state_change(self, cb, old_state, new_state):
        logger.warning(
            "circuit_breaker_state_change",
            breaker=cb.name,
            old=old_state.name,
            new=new_state.name,
        )


_listener = _BreakerListener()


def _should_exclude(exc: BaseException) -> bool:
    return not is_transient(exc)


def _make_breaker(name: str) -> pybreaker.CircuitBreaker:
    return pybreaker.CircuitBreaker(
        fail_max=CB_FAIL_MAX,
        reset_timeout=CB_RESET_TIMEOUT,
        exclude=[_should_exclude],
        listeners=[_listener],
        name=name,
    )


azure_ai_breaker = _make_breaker("azure_ai")
tavily_breaker = _make_breaker("tavily")
db_breaker = _make_breaker("db")


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
def _before_sleep(label: str):
    def _log(retry_state):
        logger.warning(
            "retry_attempt",
            label=label,
            attempt=retry_state.attempt_number,
            wait_seconds=round(retry_state.idle_for, 1),
            error=str(retry_state.outcome.exception()),
        )

    return _log


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def retryable(
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    label: str = "retry",
    breaker: pybreaker.CircuitBreaker | None = None,
):
    """Decorator for sync/async functions with retry + optional circuit breaker."""

    def decorator(fn):
        retried = retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential_jitter(
                initial=DEFAULT_INITIAL_WAIT, max=DEFAULT_MAX_WAIT, jitter=DEFAULT_JITTER
            ),
            retry=TRANSIENT_RETRY_CONDITION,
            reraise=True,
            before_sleep=_before_sleep(label),
        )(fn)
        if breaker is not None:
            return breaker(retried)
        return retried

    return decorator


async def retry_call_async(
    fn,
    *args,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    label: str = "retry",
    breaker: pybreaker.CircuitBreaker | None = None,
    **kwargs,
):
    """Retry an async callable you cannot decorate."""
    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential_jitter(
            initial=DEFAULT_INITIAL_WAIT, max=DEFAULT_MAX_WAIT, jitter=DEFAULT_JITTER
        ),
        retry=TRANSIENT_RETRY_CONDITION,
        reraise=True,
        before_sleep=_before_sleep(label),
    ):
        with attempt:
            if breaker is not None:
                return await breaker.call_async(_do_async_call(fn, *args, **kwargs))
            return await fn(*args, **kwargs)


async def _do_async_call(fn, *args, **kwargs):
    return await fn(*args, **kwargs)
