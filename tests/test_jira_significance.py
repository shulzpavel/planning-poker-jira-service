import pytest

from app.adapters.jira_http import JiraHttpClient, _jira_numeric_field_value


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (1, 1),
        (3.0, 3),
        ({"value": "4"}, 4),
        ("5", 5),
        (None, None),
        ("", None),
        ({"value": "n/a"}, None),
    ],
)
def test_jira_numeric_field_value(raw, expected):
    assert _jira_numeric_field_value(raw) == expected


@pytest.mark.asyncio
async def test_update_significance_puts_custom_field(monkeypatch):
    client = JiraHttpClient(
        base_url="https://jira.example.com",
        username="user@example.com",
        api_token="token",
        story_points_field="customfield_10022",
    )
    captured: list[dict] = []

    async def fake_request(method, path, payload=None, api_versions=None):
        captured.append({"method": method, "path": path, "payload": payload})
        return {"id": "1"}

    monkeypatch.setattr(client, "_make_request", fake_request)
    monkeypatch.setenv("JIRA_SIGNIFICANCE_FIELD", "customfield_14004")

    ok = await client.update_significance("FLEX-1", 2)

    assert ok is True
    assert captured == [
        {
            "method": "PUT",
            "path": "issue/FLEX-1",
            "payload": {"fields": {"customfield_14004": 2}},
        }
    ]


@pytest.mark.asyncio
async def test_clear_significance_nulls_custom_field(monkeypatch):
    client = JiraHttpClient(
        base_url="https://jira.example.com",
        username="user@example.com",
        api_token="token",
        story_points_field="customfield_10022",
    )
    captured: list[dict] = []

    async def fake_request(method, path, payload=None, api_versions=None):
        captured.append({"method": method, "path": path, "payload": payload})
        return {"id": "1"}

    monkeypatch.setattr(client, "_make_request", fake_request)
    monkeypatch.setenv("JIRA_SIGNIFICANCE_FIELD", "customfield_14004")

    ok = await client.clear_significance("FLEX-1")

    assert ok is True
    assert captured == [
        {
            "method": "PUT",
            "path": "issue/FLEX-1",
            "payload": {"fields": {"customfield_14004": None}},
        }
    ]
