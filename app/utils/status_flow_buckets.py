"""Map Jira workflow statuses to flow-time buckets for changelog phase metrics."""

from __future__ import annotations

import os
from typing import Any

FLOW_BUCKET_DONE = "done"
FLOW_BUCKET_TODO = "todo"
FLOW_BUCKET_PAUSE = "pause"
FLOW_BUCKET_TEST = "test"
FLOW_BUCKET_DEV = "dev"
FLOW_BUCKET_OTHER = "other"

_DONE_STATUS_NAMES = frozenset(
    {
        "готово",
        "done",
        "closed",
        "resolved",
        "cancelled",
        "canceled",
        "won't do",
        "wont do",
    }
)

_TODO_STATUS_NAMES = frozenset(
    {
        "backlog",
        "бэклог",
        "к выполнению",
        "to do",
        "todo",
        "open",
        "selected for development",
        "ready for development",
    }
)

_PAUSE_STATUS_NAMES = frozenset({"пауза", "pause", "on hold", "blocked", "deferred"})
_PAUSE_STATUS_KEYWORDS = ("пауз", "pause", "on hold", "blocked", "блок", "deferred")

_TEST_STATUS_NAMES = frozenset(
    {
        "тестирование",
        "к тестированию",
        "к релизу",
        "ready for test",
        "ready for testing",
        "in test",
        "in testing",
        "to test",
        "qa",
        "uat",
        "acceptance",
        "ready for release",
        "to release",
    }
)

_DEV_STATUS_NAMES = frozenset(
    {
        "в работе",
        "in progress",
        "in development",
        "development",
        "ревью",
        "review",
        "code review",
        "in review",
        "on review",
        "код-ревью",
        "ready for dev",
        "reopened",
        "implementing",
    }
)

FLOW_PHASE_STATUS_CATALOG: dict[str, tuple[str, ...]] = {
    FLOW_BUCKET_DEV: tuple(sorted(_DEV_STATUS_NAMES)),
    FLOW_BUCKET_TEST: tuple(sorted(_TEST_STATUS_NAMES)),
    FLOW_BUCKET_PAUSE: tuple(sorted(_PAUSE_STATUS_NAMES)),
    FLOW_BUCKET_TODO: tuple(sorted(_TODO_STATUS_NAMES)),
    FLOW_BUCKET_DONE: tuple(sorted(_DONE_STATUS_NAMES)),
}


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _norm_lower(value: Any) -> str:
    return _norm(value).lower()


def _matches_flow_keywords(status_name: str, keywords: list[str]) -> bool:
    normalized = _norm_lower(status_name)
    if not normalized:
        return False
    for keyword in keywords:
        target = _norm_lower(keyword)
        if not target:
            continue
        if normalized == target or target in normalized or normalized in target:
            return True
    return False


def _flow_dev_status_keywords() -> list[str]:
    raw = os.getenv(
        "JIRA_FLOW_DEV_STATUS_KEYWORDS",
        "dev,development,in progress,разработ,в работе,ready for dev,review,ревью",
    )
    return [part.strip() for part in raw.split(",") if part.strip()]


def _flow_test_status_keywords() -> list[str]:
    raw = os.getenv(
        "JIRA_FLOW_TEST_STATUS_KEYWORDS",
        "test,testing,тест,qa,к тест,to test,in test,тестирование,к релизу,release,uat",
    )
    return [part.strip() for part in raw.split(",") if part.strip()]


def classify_status_flow_bucket(status_name: str) -> str:
    """Classify a Jira status name into a changelog time bucket."""
    normalized = _norm_lower(status_name)
    if not normalized:
        return FLOW_BUCKET_OTHER

    if normalized in _DONE_STATUS_NAMES:
        return FLOW_BUCKET_DONE

    if normalized in _PAUSE_STATUS_NAMES or any(token in normalized for token in _PAUSE_STATUS_KEYWORDS):
        return FLOW_BUCKET_PAUSE

    if normalized in _TODO_STATUS_NAMES:
        return FLOW_BUCKET_TODO

    if normalized in _TEST_STATUS_NAMES or _matches_flow_keywords(status_name, _flow_test_status_keywords()):
        return FLOW_BUCKET_TEST

    if normalized in _DEV_STATUS_NAMES or _matches_flow_keywords(status_name, _flow_dev_status_keywords()):
        return FLOW_BUCKET_DEV

    return FLOW_BUCKET_DEV


def build_status_flow_bucket_map(status_durations: dict[str, float]) -> dict[str, str]:
    return {status: classify_status_flow_bucket(status) for status in status_durations}


def flow_phase_methodology_text() -> str:
    lines = [
        "Сумма дней в рабочих фазах по Jira changelog (status_bucket_durations), только закрытые задачи.",
        "Задача может быть в нескольких сегментах детализации, если провела время в разных фазах.",
        "",
        "Dev — разработка и ревью:",
        "  " + ", ".join(FLOW_PHASE_STATUS_CATALOG[FLOW_BUCKET_DEV]),
        "  + ключевые слова JIRA_FLOW_DEV_STATUS_KEYWORDS.",
        "",
        "Test/Release — QA и релиз:",
        "  " + ", ".join(FLOW_PHASE_STATUS_CATALOG[FLOW_BUCKET_TEST]),
        "  + ключевые слова JIRA_FLOW_TEST_STATUS_KEYWORDS.",
        "",
        "Пауза — блокировки:",
        "  " + ", ".join(FLOW_PHASE_STATUS_CATALOG[FLOW_BUCKET_PAUSE]),
        "  + статусы с pause/on hold/blocked/пауз/блок.",
        "",
        "Не фазы (в donut не входят):",
        "  Очередь: " + ", ".join(FLOW_PHASE_STATUS_CATALOG[FLOW_BUCKET_TODO]) + ".",
        "  Закрыто: " + ", ".join(FLOW_PHASE_STATUS_CATALOG[FLOW_BUCKET_DONE]) + ".",
        "  Нераспознанный активный статус → Dev (не «прочее»).",
    ]
    return "\n".join(lines)
