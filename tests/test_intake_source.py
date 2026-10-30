from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from app.adapters.intake_history import fetch_intake_source

NOW = datetime(2026, 10, 30, tzinfo=timezone.utc)
ISSUE = {"key": "TEST-1", "fields": {"summary": "Request", "created": "2026-10-01T00:00:00Z", "status": {"name": "Research"}, "assignee": {"displayName": "Owner"}, "customfield_123": {"value": "SEO"}}}

@pytest.mark.asyncio
async def test_full_history_and_configured_source_field_are_normalized():
    call = AsyncMock(side_effect=[{"issues": [ISSUE], "isLast": True}, {"values": [{"id": "1", "created": "2026-10-10T00:00:00Z", "items": [{"field": "status", "fromString": "Inbox", "toString": "Research"}]}], "total": 1}])
    result = await fetch_intake_source(call, jql="project = TEST", source_field="customfield_123", max_issues=10, base_url="https://jira.example", now=NOW)
    assert result["issues"][0]["source"] == "SEO"
    assert result["issues"][0]["segments"][0]["status"] == "Inbox"
    assert result["issues"][0]["history_complete"] is True
    assert result["issues"][0]["url"] == "https://jira.example/browse/TEST-1"

@pytest.mark.asyncio
async def test_failed_history_page_is_not_treated_as_complete_history():
    call = AsyncMock(side_effect=[{"issues": [ISSUE], "isLast": True}, {"values": [{"id": "1"}], "total": 2}, None])
    with pytest.raises(RuntimeError):
        await fetch_intake_source(call, jql="project = TEST", source_field="", max_issues=10, base_url="https://jira.example", now=NOW)

@pytest.mark.asyncio
async def test_limit_does_not_silently_truncate_the_project():
    call = AsyncMock(return_value={"issues": [ISSUE], "isLast": False, "nextPageToken": "more"})
    with pytest.raises(RuntimeError, match="limit"):
        await fetch_intake_source(call, jql="project = TEST", source_field="", max_issues=1, base_url="https://jira.example", now=NOW)

@pytest.mark.asyncio
async def test_failed_search_is_not_a_zero_demand_snapshot():
    with pytest.raises(RuntimeError):
        await fetch_intake_source(AsyncMock(return_value=None), jql="project = TEST", source_field="", max_issues=10, base_url="https://jira.example", now=NOW)

@pytest.mark.asyncio
async def test_unproven_last_search_page_is_rejected():
    with pytest.raises(RuntimeError, match="incomplete"):
        await fetch_intake_source(AsyncMock(return_value={"issues": []}), jql="project = TEST", source_field="", max_issues=10, base_url="https://jira.example", now=NOW)

@pytest.mark.asyncio
async def test_status_changed_between_search_and_history_does_not_create_a_fake_return():
    changed = {**ISSUE, "fields": {**ISSUE["fields"], "status": {"name": "Inbox", "id": "1"}}}
    call = AsyncMock(side_effect=[{"issues": [changed], "isLast": True}, {"values": [{"id": "1", "created": "2026-10-10T00:00:00Z", "items": [{"field": "status", "fromString": "Inbox", "toString": "Research", "from": "1", "to": "2"}]}], "total": 1}])
    with pytest.raises(RuntimeError, match="changed_during_refresh"):
        await fetch_intake_source(call, jql="project = TEST", source_field="", max_issues=10, base_url="https://jira.example", now=NOW)
