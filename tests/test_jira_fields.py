from jira_fields import KNOWN_SP_TRACKS, map_sp_tracks_to_fields, resolve_sp_track_field


def test_known_sp_tracks():
    assert "dev" in KNOWN_SP_TRACKS
    assert "qa" in KNOWN_SP_TRACKS


def test_resolve_sp_track_field_missing(monkeypatch):
    monkeypatch.delenv("JIRA_SP_DEV_FIELD", raising=False)
    env_name, field_id = resolve_sp_track_field("dev")
    assert env_name == "JIRA_SP_DEV_FIELD"
    assert field_id is None


def test_map_sp_tracks_to_fields(monkeypatch):
    monkeypatch.setenv("JIRA_SP_DEV_FIELD", "customfield_111")
    monkeypatch.setenv("JIRA_SP_TEST_FIELD", "")
    fields, skipped, field_to_track = map_sp_tracks_to_fields({"dev": 5, "test": 3})
    assert fields == {"customfield_111": 5}
    assert skipped == ["test"]
    assert field_to_track == {"customfield_111": "dev"}
