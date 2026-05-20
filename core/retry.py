"""Simple retry/backoff helper used across model clients."""

import time
import random
import logging
from typing import Any, Callable, Optional


def retry_call(
    fn: Callable,
    max_retries: int = 5,
    base_delay: float = 5.0,
    retry_on_exception: Optional[Callable[[Exception], bool]] = None,
    on_retry: Optional[Callable[[int, Exception, float], None]] = None,
) -> Any:
    """Call `fn()` with exponential backoff.

    - `retry_on_exception(exc)` returns True to retry, False to re-raise immediately.
    - `on_retry(attempt, exc, delay)` is called before sleeping.
    """
    last_exc = None
    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            should_retry = True
            if retry_on_exception is not None:
                try:
                    should_retry = bool(retry_on_exception(exc))
                except Exception:
                    should_retry = False

            if not should_retry or attempt >= max_retries - 1:
                raise

            delay = base_delay * (2 ** attempt)
            delay += random.uniform(0, delay * 0.1)
            logging.warning(
                "Retry attempt %d after exception %s; sleeping %.2fs",
                attempt + 1,
                type(exc).__name__,
                delay,
            )
            if on_retry:
                try:
                    on_retry(attempt + 1, exc, delay)
                except Exception:
                    pass
            time.sleep(delay)

    # If somehow loop exits, raise last exception
    if last_exc:
        raise last_exc
