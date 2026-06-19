"""Tests for readiness probes using lifespan singletons."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Optional
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from services.jira_service.client import JiraServiceClient
from services.jira_service.health import health_router


def _app_with_client(client: Optional[JiraServiceClient]) -> FastAPI:
    @asynccontextmanager
    async def _noop_lifespan(app: FastAPI):
        app.state.jira_client = client
        yield

    app = FastAPI(lifespan=_noop_lifespan)
    app.include_router(health_router, prefix="/health")
    return app


def test_jira_client_is_ready_when_session_not_created() -> None:
    client = JiraServiceClient()
    assert client.is_ready() is True


def test_jira_client_is_not_ready_when_session_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    client = JiraServiceClient()
    closed_session = MagicMock()
    closed_session.closed = True
    client._client._session = closed_session
    assert client.is_ready() is False


def test_readiness_uses_app_state_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JIRA_URL", "https://example.atlassian.net")
    monkeypatch.setenv("JIRA_USERNAME", "bot@example.com")
    monkeypatch.setenv("JIRA_API_TOKEN", "token")
    monkeypatch.setenv("STORY_POINTS_FIELD", "customfield_10022")
    monkeypatch.setenv("JIRA_DEMO_FALLBACK", "false")

    client = JiraServiceClient()
    app = _app_with_client(client)
    with TestClient(app) as test_client:
        response = test_client.get("/health/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["jira_configured"] is True
    assert body["story_points_field"] == "customfield_10022"


def test_readiness_reports_missing_singleton(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JIRA_DEMO_FALLBACK", "true")
    app = _app_with_client(None)
    with TestClient(app) as test_client:
        response = test_client.get("/health/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready"
    assert "jira_client not initialized" in body["error"]


def test_readiness_does_not_close_singleton_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JIRA_DEMO_FALLBACK", "true")

    client = JiraServiceClient()
    close_mock = MagicMock()
    monkeypatch.setattr(client, "close", close_mock)

    app = _app_with_client(client)
    with TestClient(app) as test_client:
        response = test_client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    close_mock.assert_not_called()
