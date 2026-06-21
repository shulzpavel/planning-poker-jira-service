from jira_fields import KNOWN_SP_TRACKS, map_sp_tracks_to_fields, resolve_sp_track_field


def test_known_sp_tracks():
    assert "dev" in KNOWN_SP_TRACKS
    assert "qa" in KNOWN_SP_TRACKS


def test_resolve_sp_track_field_defaults():
    env_name, field_id = resolve_sp_track_field("dev")
    assert env_name == "JIRA_SP_DEV_FIELD"
    assert field_id == "customfield_12978"


def test_resolve_sp_track_field_respects_env_override(monkeypatch):
    monkeypatch.setenv("JIRA_SP_DEV_FIELD", "customfield_999")
    import importlib

    import jira_fields as mod

    importlib.reload(mod)
    env_name, field_id = mod.resolve_sp_track_field("dev")
    assert env_name == "JIRA_SP_DEV_FIELD"
    assert field_id == "customfield_999"
    monkeypatch.delenv("JIRA_SP_DEV_FIELD", raising=False)
    importlib.reload(mod)


def test_map_sp_tracks_to_fields(monkeypatch):
    monkeypatch.setenv("JIRA_SP_DEV_FIELD", "customfield_111")
    monkeypatch.setenv("JIRA_SP_TEST_FIELD", "customfield_222")
    import importlib

    import jira_fields as mod

    importlib.reload(mod)
    fields, skipped, field_to_track = mod.map_sp_tracks_to_fields({"dev": 5, "test": 3})
    assert fields == {"customfield_111": 5, "customfield_222": 3}
    assert skipped == []
    assert field_to_track == {"customfield_111": "dev", "customfield_222": "test"}
    monkeypatch.delenv("JIRA_SP_DEV_FIELD", raising=False)
    monkeypatch.delenv("JIRA_SP_TEST_FIELD", raising=False)
    importlib.reload(mod)


def test_map_sp_tracks_skips_unconfigured_optional_track(monkeypatch):
    monkeypatch.delenv("JIRA_SP_FRONT_FIELD", raising=False)
    import importlib

    import jira_fields as mod

    importlib.reload(mod)
    fields, skipped, _ = mod.map_sp_tracks_to_fields({"front": 8})
    assert fields == {}
    assert skipped == ["front"]
    importlib.reload(mod)
