from app.adapters.jira_http import JiraHttpClient


def test_scope_issue_includes_start_date_from_custom_field():
    client = JiraHttpClient(
        base_url="https://jira.example",
        username="user",
        api_token="token",
        story_points_field="customfield_10022",
    )
    issue = client._scope_issue_from_raw(
        {
            "key": "FLEX-2571",
            "fields": {
                "summary": "Example task",
                "status": {"name": "Готово", "statusCategory": {"key": "done"}},
                "issuetype": {"name": "Story"},
                "customfield_10015": "2026-06-01",
                "customfield_10624": "2026-06-10",
            },
        }
    )
    assert issue["start_date"] == "2026-06-01"
    assert issue["due_date"] == "2026-06-10"
