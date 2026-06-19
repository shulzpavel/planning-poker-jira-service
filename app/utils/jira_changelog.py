"""Parse Jira issue changelog for scope milestone dates and developer inference."""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Any, Optional

from app.utils.status_flow_buckets import classify_status_flow_bucket

_ISSUE_KEY_RE = re.compile(r"[A-Z][A-Z0-9]+-\d+")


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _norm_lower(value: Any) -> str:
    return _norm(value).lower()


def _field_value(value: Any) -> str:
    if isinstance(value, dict):
        return _norm(value.get("name") or value.get("value") or value.get("displayName"))
    return _norm(value)


def _status_to_text(item: dict[str, Any]) -> str:
    return _field_value(item.get("toString")) or _field_value(item.get("to"))


def _status_from_text(item: dict[str, Any]) -> str:
    return _field_value(item.get("fromString")) or _field_value(item.get("from"))


def _is_status_field(field: str) -> bool:
    return _norm_lower(field) in {"status", "статус"}


def _is_assignee_field(field: str) -> bool:
    return _norm_lower(field) in {"assignee", "исполнитель"}


def _is_epic_link_field(field: str) -> bool:
    lowered = _norm_lower(field)
    return (
        lowered in {"epic link", "epic", "parent", "customfield_10013", "ссылка на эпик"}
        or "epic" in lowered
        or lowered == "parent"
    )


def _matches_status_name(value: str, target: str) -> bool:
    left = _norm_lower(value)
    right = _norm_lower(target)
    if not left or not right:
        return False
    return left == right or right in left or left in right


def _matches_any_status(value: str, targets: set[str]) -> bool:
    return any(_matches_status_name(value, target) for target in targets)


def status_matches_any_target(status_name: str, targets: list[str]) -> bool:
    return _matches_any_status(status_name, {_norm_lower(name) for name in targets if _norm(name)})


def _dev_status_keywords() -> list[str]:
    raw = os.getenv(
        "JIRA_DEV_STATUS_KEYWORDS",
        "dev,development,in progress,разработ,в работе,к выполнению,ready for dev",
    )
    return [part.strip() for part in raw.split(",") if part.strip()]


def is_dev_status(status_name: str, keywords: Optional[list[str]] = None) -> bool:
    targets = {_norm_lower(name) for name in (keywords or _dev_status_keywords())}
    if not targets:
        return False
    return _matches_any_status(status_name, targets)


def _history_items(histories: list[dict[str, Any]]) -> list[tuple[str, dict[str, Any]]]:
    rows: list[tuple[str, dict[str, Any]]] = []
    for history in histories:
        created = _norm(history.get("created"))
        if not created:
            continue
        for item in history.get("items") or []:
            if isinstance(item, dict):
                rows.append((created, item))
    rows.sort(key=lambda row: row[0])
    return rows


def status_entered_at(histories: list[dict[str, Any]], status_name: str) -> Optional[str]:
    """Return when the issue last entered the given status name."""
    target = _norm_lower(status_name)
    if not target:
        return None
    matched: Optional[str] = None
    for created, item in _history_items(histories):
        if not _is_status_field(item.get("field")):
            continue
        if _matches_status_name(_status_to_text(item), status_name):
            matched = created
    return matched


def status_entered_at_for_targets(
    histories: list[dict[str, Any]],
    status_names: list[str],
    *,
    mode: str = "last",
) -> Optional[str]:
    """Return first/last transition into any of the target statuses."""
    targets = {_norm_lower(name) for name in status_names if _norm(name)}
    if not targets:
        return None
    matched: list[str] = []
    for created, item in _history_items(histories):
        if not _is_status_field(item.get("field")):
            continue
        if _matches_any_status(_status_to_text(item), targets):
            matched.append(created)
    if not matched:
        return None
    return matched[-1] if mode == "last" else matched[0]


def _extract_issue_key(value: str) -> str:
    match = _ISSUE_KEY_RE.search(value.upper())
    return match.group(0) if match else value.upper()


def epic_linked_at(histories: list[dict[str, Any]], epic_key: str) -> Optional[str]:
    """Return when the issue was first linked to the given epic key."""
    target = _extract_issue_key(epic_key)
    if not target:
        return None
    for created, item in _history_items(histories):
        if not _is_epic_link_field(item.get("field")):
            continue
        to_value = _extract_issue_key(_norm(item.get("toString") or item.get("to") or ""))
        if to_value == target or target in _norm(item.get("toString")).upper():
            return created
    return None


def _grouped_history_items(histories: list[dict[str, Any]]) -> list[tuple[str, list[dict[str, Any]]]]:
    rows: list[tuple[str, list[dict[str, Any]]]] = []
    for history in histories:
        created = _norm(history.get("created"))
        items = [item for item in (history.get("items") or []) if isinstance(item, dict)]
        if created and items:
            rows.append((created, items))
    rows.sort(key=lambda row: row[0])
    return rows


def infer_developer_from_changelog(
    histories: list[dict[str, Any]],
    *,
    current_status: str,
    current_assignee: str,
    dev_status_keywords: Optional[list[str]] = None,
) -> tuple[str, str]:
    """Infer the developer from assignee/status history during development statuses."""
    return _infer_role_assignee_from_changelog(
        histories,
        current_status=current_status,
        current_assignee=current_assignee,
        status_keywords=dev_status_keywords or _dev_status_keywords(),
        source_name="changelog",
        current_source="current",
        fallback_source="fallback",
    )


def _test_status_keywords() -> list[str]:
    raw = os.getenv(
        "JIRA_TEST_STATUS_KEYWORDS",
        "test,testing,тест,qa,к тест,to test,in test,тестирование,к релизу",
    )
    return [part.strip() for part in raw.split(",") if part.strip()]


_QA_ASSIGNEE_STATUS_NAMES = frozenset(
    {
        "тестирование",
        "к релизу",
        "готово",
        "done",
        "released",
        "resolved",
        "closed",
    }
)


def qa_assignee_from_current_status_allowed(status_name: str) -> bool:
    """Whether the current assignee can be treated as QA for workload reporting."""
    normalized = _norm_lower(status_name)
    if normalized in _QA_ASSIGNEE_STATUS_NAMES:
        return True
    return is_dev_status(status_name, _test_status_keywords())


def infer_qa_from_changelog(
    histories: list[dict[str, Any]],
    *,
    current_status: str,
    current_assignee: str,
    test_status_keywords: Optional[list[str]] = None,
) -> tuple[str, str]:
    """Infer QA assignee from test-status history."""
    return _infer_role_assignee_from_changelog(
        histories,
        current_status=current_status,
        current_assignee=current_assignee,
        status_keywords=test_status_keywords or _test_status_keywords(),
        source_name="changelog",
        current_source="current",
        fallback_source="fallback",
    )


def _infer_role_assignee_from_changelog(
    histories: list[dict[str, Any]],
    *,
    current_status: str,
    current_assignee: str,
    status_keywords: list[str],
    source_name: str,
    current_source: str,
    fallback_source: str,
) -> tuple[str, str]:
    keywords = status_keywords
    assignee = ""
    status = ""
    last_role_assignee = ""

    for _created, items in _grouped_history_items(histories):
        assignee_before = assignee
        status_before = status
        status_from = ""
        status_to = ""
        assignee_from = ""

        for item in items:
            if _is_assignee_field(item.get("field")):
                assignee_from = _field_value(item.get("fromString")) or _field_value(item.get("from")) or assignee_from
                to_assignee = _field_value(item.get("toString")) or _field_value(item.get("to"))
                if to_assignee:
                    assignee = to_assignee
            if _is_status_field(item.get("field")):
                status_from = _status_from_text(item) or status_from
                status_to = _status_to_text(item) or status_to

        if status_to:
            status = status_to
        elif status_from:
            status = status_from

        leaving = is_dev_status(status_from or status_before, keywords) and not is_dev_status(
            status_to or status, keywords
        )
        if leaving:
            candidate = assignee_before or assignee_from or assignee
            if candidate:
                last_role_assignee = candidate
        elif is_dev_status(status, keywords) and assignee:
            last_role_assignee = assignee

    if last_role_assignee:
        return last_role_assignee, source_name

    current = _norm(current_assignee)
    if current and is_dev_status(current_status, keywords):
        return current, current_source

    if current:
        return current, fallback_source

    return "", fallback_source


def _parse_changelog_timestamp(value: Any) -> Optional[datetime]:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    if len(normalized) >= 5 and normalized[-5] in "+-" and normalized[-3] != ":":
        normalized = f"{normalized[:-2]}:{normalized[-2:]}"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def compute_issue_flow_timeline(
    histories: list[dict[str, Any]],
    *,
    current_status: str,
    current_assignee: str,
    created_at: str | None = None,
    ended_at: datetime | None = None,
) -> dict[str, Any]:
    """Summarize time-in-status and assignee context from Jira changelog."""
    end = ended_at or datetime.now(timezone.utc)
    start = _parse_changelog_timestamp(created_at) or end

    status = ""
    assignee = _norm(current_assignee)
    transitions: list[tuple[datetime, str, str, str]] = []

    for at_str, items in _grouped_history_items(histories):
        at = _parse_changelog_timestamp(at_str)
        if at is None:
            continue
        status_from = ""
        status_to = ""
        for item in items:
            if _is_assignee_field(item.get("field")):
                to_assignee = _field_value(item.get("toString")) or _field_value(item.get("to"))
                if to_assignee:
                    assignee = to_assignee
            if _is_status_field(item.get("field")):
                status_from = _status_from_text(item) or status_from
                status_to = _status_to_text(item) or status_to
        if status_to:
            transitions.append((at, status_to, assignee, status_from or status))
            status = status_to

    timeline_points: list[tuple[datetime, str, str]] = []
    if transitions:
        initial_status = transitions[0][3] or _norm(current_status)
        timeline_points.append((start, initial_status, ""))
        for at, status_to, assignee_at, _ in transitions:
            timeline_points.append((at, status_to, assignee_at))
    else:
        timeline_points.append((start, _norm(current_status), assignee))
    if timeline_points[-1][0] < end:
        timeline_points.append((end, _norm(current_status) or timeline_points[-1][1], assignee))

    segments: list[dict[str, Any]] = []
    durations: dict[str, float] = {}
    bucket_durations: dict[str, float] = {
        "dev": 0.0,
        "test": 0.0,
        "todo": 0.0,
        "pause": 0.0,
        "done": 0.0,
        "other": 0.0,
    }
    for index in range(len(timeline_points) - 1):
        entered_at, status_name, segment_assignee = timeline_points[index]
        left_at = timeline_points[index + 1][0]
        duration_days = max(0.0, (left_at - entered_at).total_seconds() / 86400.0)
        rounded = round(duration_days, 2)
        label = status_name or _norm(current_status) or "—"
        segments.append(
            {
                "status": label,
                "assignee": segment_assignee,
                "entered_at": entered_at.isoformat(),
                "left_at": left_at.isoformat(),
                "duration_days": rounded,
                "is_current": index == len(timeline_points) - 2,
            }
        )
        durations[label] = round(durations.get(label, 0.0) + duration_days, 2)
        bucket = classify_status_flow_bucket(label)
        bucket_durations[bucket] = round(bucket_durations.get(bucket, 0.0) + duration_days, 2)

    current_segment = segments[-1] if segments else None
    status_flow_bucket_map = {status: classify_status_flow_bucket(status) for status in durations}
    return {
        "status_durations": durations,
        "status_bucket_durations": bucket_durations,
        "status_flow_bucket_map": status_flow_bucket_map,
        "status_segments": segments,
        "current_status_assignee": _norm(current_assignee) or (current_segment or {}).get("assignee", ""),
        "current_status_days": (current_segment or {}).get("duration_days"),
    }
