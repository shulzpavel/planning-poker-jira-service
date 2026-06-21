"""Metrics endpoints."""

from fastapi import APIRouter, Request

router = APIRouter()
metrics_router = router  # alias for main.py


@router.get("/", response_model=dict)
async def get_metrics(request: Request) -> dict:
    """Expose in-process Jira client cache stats."""
    client = getattr(request.app.state, "jira_client", None)
    if client is None or not hasattr(client, "cache_metrics"):
        return {
            "cache_size": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "inflight_requests": 0,
            "ready": False,
        }
    payload = client.cache_metrics()
    payload["ready"] = client.is_ready()
    return payload
