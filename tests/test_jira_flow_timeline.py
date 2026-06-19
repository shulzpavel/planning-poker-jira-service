from datetime import datetime, timezone

from app.utils.jira_changelog import compute_issue_flow_timeline


def test_compute_issue_flow_timeline_aggregates_status_durations():
    now = datetime(2026, 6, 19, 12, 0, tzinfo=timezone.utc)
    histories = [
        {
            "created": "2026-06-01T10:00:00.000+0000",
            "items": [{"field": "status", "fromString": "К выполнению", "toString": "В работе"}],
        },
        {
            "created": "2026-06-10T10:00:00.000+0000",
            "items": [
                {"field": "assignee", "fromString": "Dev A", "toString": "QA B"},
                {"field": "status", "fromString": "В работе", "toString": "Тестирование"},
            ],
        },
    ]
    timeline = compute_issue_flow_timeline(
        histories,
        current_status="Тестирование",
        current_assignee="QA B",
        created_at="2026-06-01T08:00:00.000+0000",
        ended_at=now,
    )
    assert timeline["status_durations"]["В работе"] >= 8.9
    assert timeline["status_durations"]["Тестирование"] >= 8.9
    assert timeline["status_bucket_durations"]["dev"] >= 8.9
    assert timeline["status_bucket_durations"]["test"] >= 8.9
    assert timeline["current_status_assignee"] == "QA B"
