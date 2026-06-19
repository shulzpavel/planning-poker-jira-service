"""Health check endpoints for Jira Service."""

import os
from typing import Optional

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel

router = APIRouter()
health_router = router  # backward compatibility


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


@router.get("/", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic liveness."""
    return HealthResponse(status="healthy", service="jira-service", version="1.0.0")


def _env_present(name: str) -> bool:
    return bool(os.getenv(name, "").strip())


def _demo_fallback_enabled() -> bool:
    return os.getenv("JIRA_DEMO_FALLBACK", "false").strip().lower() in {"1", "true", "yes", "on"}


def _readiness_payload(*, status: str, error: Optional[str] = None) -> dict:
    payload = {
        "status": status,
        "jira_configured": _env_present("JIRA_URL")
        and _env_present("JIRA_USERNAME")
        and _env_present("JIRA_API_TOKEN"),
        "demo_fallback_enabled": _demo_fallback_enabled(),
        "story_points_field": os.getenv("STORY_POINTS_FIELD", "").strip() or None,
    }
    if error:
        payload["error"] = error
    return payload


@router.get("/ready")
async def readiness_check(request: Request, response: Response) -> dict:
    """Readiness without leaking Jira credentials or opening new HTTP clients."""
    jira_configured = _env_present("JIRA_URL") and _env_present("JIRA_USERNAME") and _env_present(
        "JIRA_API_TOKEN"
    )
    demo_fallback = _demo_fallback_enabled()
    expected_ready = jira_configured or demo_fallback

    client = getattr(request.app.state, "jira_client", None)
    if client is None:
        response.status_code = 503
        return _readiness_payload(status="not_ready", error="jira_client not initialized")

    if not client.is_ready():
        response.status_code = 503
        return _readiness_payload(status="not_ready", error="jira_client session closed")

    status = "ready" if expected_ready else "not_ready"
    if status != "ready":
        response.status_code = 503
    return _readiness_payload(status=status)


@router.get("/live")
async def liveness_check() -> dict:
    """Liveness endpoint."""
    return {"status": "alive"}
