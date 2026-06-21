"""Jira custom field mapping — single source of truth for jira-service."""

from __future__ import annotations

import os
from typing import Optional

KNOWN_SP_TRACKS = frozenset({"dev", "test", "front", "back", "qa"})


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


STORY_POINTS_FIELD = _env("STORY_POINTS_FIELD", "customfield_10022")
JIRA_SP_DEV_FIELD = _env("JIRA_SP_DEV_FIELD")
JIRA_SP_TEST_FIELD = _env("JIRA_SP_TEST_FIELD")
JIRA_SP_FRONT_FIELD = _env("JIRA_SP_FRONT_FIELD")
JIRA_SP_BACK_FIELD = _env("JIRA_SP_BACK_FIELD")
JIRA_SP_QA_FIELD = _env("JIRA_SP_QA_FIELD")
JIRA_FRONT_ASSIGNEE_FIELD = _env(
    "JIRA_FRONT_ASSIGNEE_FIELD",
    _env("JIRA_FRONT_FIELD"),
)
JIRA_BACK_ASSIGNEE_FIELD = _env(
    "JIRA_BACK_ASSIGNEE_FIELD",
    _env("JIRA_BACK_FIELD"),
)
JIRA_QA_ASSIGNEE_FIELD = _env(
    "JIRA_QA_ASSIGNEE_FIELD",
    _env("JIRA_TESTER_FIELD", _env("JIRA_TEST_ASSIGNEE_FIELD")),
)
JIRA_PLAN_STATUS_FIELD = _env("JIRA_PLAN_STATUS_FIELD", "customfield_13045")
JIRA_PLAN_CHANGE_REASON_FIELD = _env("JIRA_PLAN_CHANGE_REASON_FIELD", "customfield_13047")
JIRA_SIGNIFICANCE_FIELD = _env("JIRA_SIGNIFICANCE_FIELD", "customfield_14004")
JIRA_START_DATE_FIELD = _env("JIRA_START_DATE_FIELD", "customfield_10015")

TRACK_FIELD_ENV_NAMES: dict[str, str] = {
    "dev": "JIRA_SP_DEV_FIELD",
    "test": "JIRA_SP_TEST_FIELD",
    "front": "JIRA_SP_FRONT_FIELD",
    "back": "JIRA_SP_BACK_FIELD",
    "qa": "JIRA_SP_QA_FIELD",
}


def resolve_sp_track_field(track: str) -> tuple[str, Optional[str]]:
    """Map semantic track key to (env var name, Jira field id or None if unset)."""
    key = str(track or "").strip().lower()
    env_name = TRACK_FIELD_ENV_NAMES.get(key, f"JIRA_SP_{key.upper()}_FIELD")
    field_id = _env(env_name) or None
    return env_name, field_id


def map_sp_tracks_to_fields(tracks: dict[str, int]) -> tuple[dict[str, int], list[str], dict[str, str]]:
    """Return (field_id→value, skipped track keys, field_id→track key)."""
    fields: dict[str, int] = {}
    skipped: list[str] = []
    field_to_track: dict[str, str] = {}
    for track_key, value in tracks.items():
        _env_name, field_id = resolve_sp_track_field(track_key)
        if not field_id:
            skipped.append(track_key)
            continue
        fields[field_id] = int(value)
        field_to_track[field_id] = track_key
    return fields, skipped, field_to_track
