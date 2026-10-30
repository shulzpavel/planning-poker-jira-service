"""Complete Jira history input for intake analytics; no partial-success snapshots."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable
from urllib.parse import quote

from app.utils.jira_changelog import compute_issue_flow_timeline, _parse_changelog_timestamp

Request = Callable[..., Awaitable[dict[str, Any] | None]]

async def _search(call: Request, jql: str, field: str, limit: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    token: str | None = None
    seen: set[str] = set()
    fields = ["summary", "status", "created", "updated", "assignee"] + ([field] if field else [])
    while True:
        body: dict[str, Any] = {"jql": jql, "maxResults": min(100, limit - len(rows)), "fields": fields}
        if token:
            body["nextPageToken"] = token
        result = await call("POST", "search/jql", body, api_versions=["3"])
        if not isinstance(result, dict) or not isinstance(result.get("issues"), list):
            raise RuntimeError("intake_search_failed")
        page = result["issues"]
        if any(not isinstance(x, dict) or not x.get("key") or not isinstance(x.get("fields"), dict) for x in page):
            raise RuntimeError("intake_search_invalid")
        rows.extend(page)
        if len(rows) > limit:
            raise RuntimeError("intake_issue_limit")
        token = result.get("nextPageToken")
        if not token:
            if result.get("isLast") is False or (result.get("isLast") is not True and result.get("total") != len(rows)):
                raise RuntimeError("intake_search_incomplete")
            break
        if len(rows) >= limit:
            raise RuntimeError("intake_issue_limit")
        if not page or token in seen:
            raise RuntimeError("intake_search_incomplete")
        seen.add(token)
    if len({x["key"] for x in rows}) != len(rows):
        raise RuntimeError("intake_search_duplicate")
    return rows

async def _history(call: Request, key: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for _ in range(1000):
        data = await call("GET", f"issue/{quote(key, safe='')}/changelog?startAt={len(rows)}&maxResults=100", api_versions=["3"])
        if not isinstance(data, dict) or not isinstance(data.get("values"), list):
            raise RuntimeError("intake_history_failed")
        page = data["values"]
        total = data.get("total")
        if not isinstance(total, int) or any(not isinstance(x, dict) for x in page):
            raise RuntimeError("intake_history_invalid")
        for item in page:
            if not item.get("id") or _parse_changelog_timestamp(item.get("created")) is None or not isinstance(item.get("items"), list):
                raise RuntimeError("intake_history_invalid")
            for change in item["items"]:
                if not isinstance(change, dict):
                    raise RuntimeError("intake_history_invalid")
                if str(change.get("field", "")).casefold() in {"status", "статус"} and (not change.get("toString") or (change.get("from") is not None and not change.get("fromString"))):
                    raise RuntimeError("intake_history_status_incomplete")
        known = {x["id"] for x in rows}
        if any(x["id"] in known for x in page) or len({x["id"] for x in page}) != len(page):
            raise RuntimeError("intake_history_duplicate")
        rows.extend(page)
        if len(rows) == total:
            return rows
        if not page or len(rows) > total:
            raise RuntimeError("intake_history_incomplete")
    raise RuntimeError("intake_history_limit")

def _normalize(raw: dict[str, Any], histories: list[dict[str, Any]], field: str, base: str, now: datetime) -> dict[str, Any]:
    fields = raw["fields"]
    status_data = fields.get("status")
    status = str(status_data.get("name") or "") if isinstance(status_data, dict) else ""
    created = fields.get("created")
    if not status or not isinstance(created, str) or not created:
        raise RuntimeError("intake_issue_metadata_missing")
    try:
        if datetime.fromisoformat(created.replace("Z", "+00:00")) > now:
            raise RuntimeError("intake_created_in_future")
    except (ValueError, TypeError) as exc:
        raise RuntimeError("intake_issue_timestamp_invalid") from exc
    created_at = _parse_changelog_timestamp(created)
    for entry in histories:
        changed = _parse_changelog_timestamp(entry.get("created"))
        if changed is None or created_at is None or changed < created_at or changed > now:
            raise RuntimeError("intake_history_timestamp_invalid")
    status_events = [(entry["created"], change) for entry in histories for change in entry["items"] if str(change.get("field", "")).casefold() in {"status", "статус"}]
    if status_events:
        _, latest = max(status_events, key=lambda x: _parse_changelog_timestamp(x[0]))
        current_id, last_id = status_data.get("id"), latest.get("to")
        mismatched = str(current_id) != str(last_id) if current_id is not None and last_id is not None else latest.get("toString") != status
        if mismatched:
            raise RuntimeError("intake_status_changed_during_refresh")
    assignee = str((fields.get("assignee") or {}).get("displayName") or "")
    source = fields.get(field) if field else None
    if isinstance(source, dict):
        source = source.get("value") or source.get("name")
    timeline = compute_issue_flow_timeline(histories, current_status=status, current_assignee=assignee, created_at=created, ended_at=now)
    return {"key": raw["key"], "summary": str(fields.get("summary") or raw["key"]), "status": status,
            "assignee": assignee or None, "source": str(source).strip() if source else None,
            "url": f"{base.rstrip('/')}/browse/{quote(raw['key'], safe='')}", "updated": fields.get("updated"),
            "history_complete": True, "segments": timeline["status_segments"]}

async def fetch_intake_source(call: Request, *, jql: str, source_field: str, max_issues: int, base_url: str, now: datetime | None = None) -> dict[str, Any]:
    rows = await _search(call, jql, source_field, max_issues)
    semaphore = asyncio.Semaphore(4)
    async def load(row: dict[str, Any]) -> list[dict[str, Any]]:
        async with semaphore:
            return await _history(call, row["key"])
    histories = await asyncio.gather(*(load(row) for row in rows))
    at = now or datetime.now(timezone.utc)
    issues = [_normalize(row, history, source_field, base_url, at) for row, history in zip(rows, histories)]
    return {"fetched_at": at.isoformat(), "jira_url": base_url.rstrip("/"), "issues": issues}
