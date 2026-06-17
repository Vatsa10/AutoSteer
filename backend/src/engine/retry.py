"""
Retry wrapper with exponential backoff and jitter.

Neither Kokoro nor Raah had this — built from scratch for workflow reliability.
"""

import asyncio
import logging
import random
from collections.abc import Callable, Awaitable
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    max_retries: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: bool = True


DEFAULT_RETRY = RetryConfig()


async def retry(
    fn: Callable[..., Awaitable[Any]],
    *args: Any,
    config: RetryConfig | None = None,
    **kwargs: Any,
) -> Any:
    """Call an async function with retry + exponential backoff.

    Raises the last exception after exhausting all retries.
    """
    cfg = config or DEFAULT_RETRY
    last_exc: Exception | None = None

    for attempt in range(cfg.max_retries + 1):
        try:
            return await fn(*args, **kwargs)
        except Exception as exc:
            last_exc = exc
            if attempt == cfg.max_retries:
                logger.error(
                    "retry exhausted: %s attempt(s), last error: %s",
                    cfg.max_retries,
                    exc,
                )
                raise
            delay = min(
                cfg.base_delay_seconds * (cfg.backoff_multiplier ** attempt),
                cfg.max_delay_seconds,
            )
            if cfg.jitter:
                delay = delay * (0.5 + random.random())
            logger.warning(
                "retry attempt %s/%s for %s — waiting %.1fs: %s",
                attempt + 1,
                cfg.max_retries,
                getattr(fn, "__name__", str(fn)),
                delay,
                exc,
            )
            await asyncio.sleep(delay)

    # Should be unreachable, but satisfy the type checker
    assert last_exc is not None
    raise last_exc
