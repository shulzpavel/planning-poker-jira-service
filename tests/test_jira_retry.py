import random
from datetime import datetime, timezone

import pytest

from app.adapters.jira_retry import (
    parse_retry_after,
    retry_after_from_headers,
    retry_delay_seconds,
)


def test_parse_retry_after_seconds():
    assert parse_retry_after("12") == 12.0
    assert parse_retry_after(" 0 ") == 0.0


def test_parse_retry_after_http_date():
    now = datetime(2026, 6, 19, 10, 0, 0, tzinfo=timezone.utc).timestamp()
    header = "Fri, 19 Jun 2026 10:00:30 GMT"
    assert parse_retry_after(header, now=now) == pytest.approx(30.0, abs=0.5)


def test_parse_retry_after_invalid():
    assert parse_retry_after("") is None
    assert parse_retry_after("not-a-date") is None


def test_retry_delay_honors_retry_after():
    assert retry_delay_seconds(1, retry_after_seconds=15.0) == 15.0
    assert retry_delay_seconds(3, retry_after_seconds=120.0, max_delay=60.0) == 60.0


def test_retry_delay_uses_exponential_jitter_without_retry_after():
    rng = random.Random(0)
    first = retry_delay_seconds(1, rng=rng)
    second = retry_delay_seconds(2, rng=rng)
    assert 0.0 <= first <= 0.5
    assert 0.0 <= second <= 1.0


def test_retry_after_from_headers_case_insensitive_key():
    assert retry_after_from_headers({"Retry-After": "4"}) == 4.0
    assert retry_after_from_headers({"retry-after": "2"}) == 2.0
