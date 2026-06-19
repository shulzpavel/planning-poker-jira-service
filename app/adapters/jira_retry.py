"""Retry/backoff helpers for Jira HTTP requests."""

from __future__ import annotations

import random
import time
from email.utils import parsedate_to_datetime
from typing import Mapping, Optional

TRANSIENT_HTTP_STATUSES = frozenset({429, 500, 502, 503, 504})

DEFAULT_RETRY_BASE_DELAY_SEC = 0.5
DEFAULT_RETRY_MAX_DELAY_SEC = 60.0
DEFAULT_MAX_CONCURRENT_REQUESTS = 6


def parse_retry_after(
    value: Optional[str],
    *,
    now: Optional[float] = None,
) -> Optional[float]:
    """Parse Retry-After as delay-seconds or HTTP-date."""
    if not value:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    try:
        return max(0.0, float(cleaned))
    except ValueError:
        pass
    try:
        parsed = parsedate_to_datetime(cleaned)
        if parsed.tzinfo is None:
            from datetime import timezone

            parsed = parsed.replace(tzinfo=timezone.utc)
        current = now if now is not None else time.time()
        return max(0.0, parsed.timestamp() - current)
    except (TypeError, ValueError, OverflowError):
        return None


def retry_delay_seconds(
    attempt: int,
    *,
    retry_after_seconds: Optional[float] = None,
    base_delay: float = DEFAULT_RETRY_BASE_DELAY_SEC,
    max_delay: float = DEFAULT_RETRY_MAX_DELAY_SEC,
    rng: Optional[random.Random] = None,
) -> float:
    """Exponential backoff with full jitter; honor Retry-After when provided."""
    if retry_after_seconds is not None:
        return min(max_delay, max(0.0, retry_after_seconds))

    # attempt is 1-based (first retry after initial failure).
    exponent = max(0, attempt - 1)
    ceiling = min(max_delay, base_delay * (2**exponent))
    roll = (rng or random).random()
    return ceiling * roll


def retry_after_from_headers(headers: Mapping[str, str]) -> Optional[float]:
    for key in ("Retry-After", "retry-after"):
        if key in headers:
            return parse_retry_after(headers.get(key))
    return None
