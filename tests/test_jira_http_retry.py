"""Tests for Jira HTTP retry/backoff behaviour."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.adapters.jira_http import JiraHttpClient


class _FakeResponse:
    def __init__(self, status: int, *, headers: dict[str, str] | None = None, payload: dict | None = None):
        self.status = status
        self.headers = headers or {}
        self.content_length = 0 if status == 204 else None
        self._payload = payload or {"ok": True}

    async def json(self):
        return self._payload

    async def text(self):
        return ""

    def raise_for_status(self):
        if self.status >= 400:
            request_info = SimpleNamespace(real_url="https://jira.example/rest/api/3/ping")
            raise __import__("aiohttp").ClientResponseError(
                request_info=request_info,
                history=(),
                status=self.status,
                message="error",
                headers=self.headers,
            )


class _RequestContext:
    def __init__(self, response: _FakeResponse):
        self._response = response

    async def __aenter__(self) -> _FakeResponse:
        return self._response

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


def _request_cm(response: _FakeResponse) -> _RequestContext:
    return _RequestContext(response)


def _client(**kwargs) -> JiraHttpClient:
    return JiraHttpClient(
        base_url="https://jira.example",
        username="u",
        api_token="t",
        story_points_field="customfield_10016",
        retry_attempts=3,
        **kwargs,
    )


@pytest.mark.asyncio
async def test_make_request_retries_429_with_retry_after(monkeypatch):
    client = _client()
    responses = [
        _FakeResponse(429, headers={"Retry-After": "3"}),
        _FakeResponse(200, payload={"issues": []}),
    ]
    sleeps: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    session = SimpleNamespace(
        closed=False,
        request=lambda *args, **kwargs: _request_cm(responses.pop(0)),
    )
    monkeypatch.setattr(client, "_get_session", AsyncMock(return_value=session))
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    result = await client._make_request("GET", "search")

    assert result == {"issues": []}
    assert sleeps == [3.0]


@pytest.mark.asyncio
async def test_make_request_limits_in_flight_requests(monkeypatch):
    client = _client()
    client._request_semaphore = asyncio.Semaphore(1)
    in_flight = 0
    max_in_flight = 0

    class _TrackedContext(_RequestContext):
        async def __aenter__(self) -> _FakeResponse:
            nonlocal in_flight, max_in_flight
            in_flight += 1
            max_in_flight = max(max_in_flight, in_flight)
            await asyncio.sleep(0.01)
            return await super().__aenter__()

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            nonlocal in_flight
            try:
                return await super().__aexit__(exc_type, exc, tb)
            finally:
                in_flight -= 1

    def fake_request(*args, **kwargs):
        return _TrackedContext(_FakeResponse(200, payload={"ok": True}))

    session = SimpleNamespace(closed=False, request=fake_request)
    monkeypatch.setattr(client, "_get_session", AsyncMock(return_value=session))

    await asyncio.gather(
        client._make_request("GET", "a"),
        client._make_request("GET", "b"),
    )

    assert max_in_flight == 1
