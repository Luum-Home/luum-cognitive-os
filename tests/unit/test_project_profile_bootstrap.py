from __future__ import annotations

import json
from pathlib import Path

from lib.project_profile_bootstrap import (
    build_project_profile_draft,
    detect_conflicts,
    sanitize_text,
    promote_project_profile,
    wipe_project_profile,
    write_project_profile_draft,
    ProfileEntry,
    ProfileSource,
)


def _session(project: Path, session_id: str, start: str = "2026-04-29T00:00:00Z") -> None:
    session_dir = project / ".cognitive-os" / "sessions" / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "meta.json").write_text(
        json.dumps(
            {
                "session_id": session_id,
                "start_time": start,
                "working_directory": str(project),
                "user": "local-dev",
            }
        )
    )


def test_generates_draft_for_first_three_sessions(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "go.mod").write_text("module example.com/app\n")
    _session(project, "s1")

    draft_path = write_project_profile_draft(project)

    assert draft_path is not None
    data = json.loads(draft_path.read_text())
    assert data["status"] == "draft"
    assert data["session_count"] == 1
    assert any(entry["value"] == "go" for entry in data["entries"])
    assert (project / ".cognitive-os" / "project-profile" / "draft.md").exists()


def test_does_not_generate_after_third_session_when_missing(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    for idx in range(4):
        _session(project, f"s{idx}", f"2026-04-29T00:00:0{idx}Z")

    assert write_project_profile_draft(project) is None
    assert not (project / ".cognitive-os" / "project-profile" / "draft.json").exists()


def test_keeps_existing_draft_after_bootstrap_window(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    for idx in range(4):
        _session(project, f"s{idx}", f"2026-04-29T00:00:0{idx}Z")
    draft_dir = project / ".cognitive-os" / "project-profile"
    draft_dir.mkdir(parents=True)
    existing = draft_dir / "draft.json"
    existing.write_text('{"status":"draft"}\n')

    assert write_project_profile_draft(project) == existing
    assert existing.read_text() == '{"status":"draft"}\n'


def test_draft_entries_are_source_linked(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "package.json").write_text('{"scripts":{}}\n')
    _session(project, "s1")

    draft = build_project_profile_draft(project)

    assert draft["entries"]
    for entry in draft["entries"]:
        assert entry["source"]["type"]
        assert entry["source"]["path"]


def test_absolute_project_and_home_paths_are_sanitized(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    mac_home = "/" + "Users" + "/alice/private/app"
    raw = f"Use {project}/src and {mac_home}"

    sanitized = sanitize_text(raw, project)

    assert str(project) not in sanitized
    assert mac_home not in sanitized
    assert "<project-root>" in sanitized
    assert "<developer-home>" in sanitized


def test_secret_like_content_blocks_entry(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    metrics = project / ".cognitive-os" / "metrics"
    metrics.mkdir(parents=True)
    (metrics / "prompt-captures.jsonl").write_text(
        json.dumps({"category": "cat .env"}) + "\n"
    )
    _session(project, "s1")

    draft = build_project_profile_draft(project)

    assert all(".env" not in json.dumps(entry) for entry in draft["entries"])


def test_conflicting_entries_are_marked_not_overwritten() -> None:
    entries = [
        ProfileEntry("a", "preference", "language", "Spanish", 0.7, "draft", ProfileSource("test", "a")),
        ProfileEntry("b", "preference", "language", "English", 0.6, "draft", ProfileSource("test", "b")),
    ]

    conflicts = detect_conflicts(entries)

    assert len(conflicts) == 1
    assert conflicts[0].key == "preference:language"
    assert conflicts[0].values == ["English", "Spanish"]


def test_promote_requires_approval(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "go.mod").write_text("module example.com/app\n")
    _session(project, "s1")
    write_project_profile_draft(project)

    try:
        promote_project_profile(project)
    except PermissionError as exc:
        assert "requires" in str(exc)
    else:
        raise AssertionError("profile promotion without approval should fail")


def test_promote_writes_active_profile_without_leaking_approval_path(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "go.mod").write_text("module example.com/app\n")
    _session(project, "s1")
    write_project_profile_draft(project)
    approver = "/" + "Users" + "/alice"

    active = promote_project_profile(project, approved_by=approver)

    data = json.loads(active.read_text())
    assert data["status"] == "active"
    assert data["promoted_by"] == "<developer-home>"
    assert approver not in active.read_text()


def test_wipe_removes_project_profile_dir(tmp_path: Path) -> None:
    project = tmp_path / "project"
    profile_dir = project / ".cognitive-os" / "project-profile"
    profile_dir.mkdir(parents=True)
    (profile_dir / "draft.json").write_text("{}")

    wipe_project_profile(project)

    assert not profile_dir.exists()


def test_fail_open_on_corrupt_session_meta(tmp_path: Path) -> None:
    project = tmp_path / "project"
    bad = project / ".cognitive-os" / "sessions" / "bad"
    bad.mkdir(parents=True)
    (bad / "meta.json").write_text("not json")

    draft = build_project_profile_draft(project)

    assert draft["session_count"] == 0
