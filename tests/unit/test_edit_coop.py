"""Behavioral tests for scripts/edit-coop.sh — ADR-098 Layer 4 file locks."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
COOP = REPO_ROOT / "scripts" / "edit-coop.sh"


def _run(args: list[str], session: str = "test-session-A", env_extra: dict | None = None, project_dir: Path | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["COGNITIVE_OS_SESSION_ID"] = session
    # Each subprocess invocation in tests is a fresh bash that exits before
    # the next call, making every lock look PID-stale. Production keeps the
    # PID check; tests skip it so we exercise the time-based logic instead.
    env.setdefault("COS_EDIT_LOCK_NO_PID_CHECK", "1")
    env.pop("COS_BYPASS_EDIT_LOCK", None)
    if project_dir is not None:
        env["CLAUDE_PROJECT_DIR"] = str(project_dir)
        env["COGNITIVE_OS_PROJECT_DIR"] = str(project_dir)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", str(COOP), *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )


@pytest.fixture
def fake_project(tmp_path: Path) -> Path:
    """Minimal project dir so edit-coop's _resolve_project_dir picks it up."""
    (tmp_path / ".claude").mkdir()
    return tmp_path


def test_acquire_then_check_returns_own(fake_project):
    r = _run(["acquire", "tests/sample.py", "demo", "exclusive-edit"], project_dir=fake_project)
    assert r.returncode == 0, r.stderr
    r = _run(["check", "tests/sample.py"], project_dir=fake_project)
    assert r.returncode == 0
    assert "OWN" in r.stdout


def test_acquire_blocks_other_session(fake_project):
    r = _run(["acquire", "tests/sample.py", "x", "exclusive-edit"], session="A", project_dir=fake_project)
    assert r.returncode == 0
    r = _run(["acquire", "tests/sample.py", "y", "exclusive-edit"], session="B", project_dir=fake_project)
    assert r.returncode == 2, f"Expected 2 (blocked), got {r.returncode}"
    assert "BLOCKED" in r.stderr


def test_check_reports_held_for_other_session(fake_project):
    _run(["acquire", "tests/sample.py", "x", "exclusive-edit"], session="A", project_dir=fake_project)
    r = _run(["check", "tests/sample.py"], session="B", project_dir=fake_project)
    assert r.returncode == 2
    assert "HELD" in r.stdout
    assert "session=A" in r.stdout


def test_release_clears_lock(fake_project):
    _run(["acquire", "tests/sample.py", "x", "exclusive-edit"], project_dir=fake_project)
    r = _run(["release", "tests/sample.py"], project_dir=fake_project)
    assert r.returncode == 0
    r = _run(["check", "tests/sample.py"], project_dir=fake_project)
    assert "FREE" in r.stdout


def test_release_refuses_other_sessions_lock(fake_project):
    _run(["acquire", "tests/sample.py", "x", "exclusive-edit"], session="A", project_dir=fake_project)
    r = _run(["release", "tests/sample.py"], session="B", project_dir=fake_project)
    assert r.returncode == 2
    assert "refusing" in r.stderr.lower()


def test_idempotent_reacquire_by_owner(fake_project):
    r = _run(["acquire", "tests/sample.py", "x", "exclusive-edit"], project_dir=fake_project)
    assert r.returncode == 0
    r = _run(["acquire", "tests/sample.py", "x updated", "exclusive-edit"], project_dir=fake_project)
    assert r.returncode == 0, "Re-acquire by same session must succeed (idempotent)"
    assert "re-acquired" in r.stderr.lower()


def test_status_lists_active_locks_as_json(fake_project):
    _run(["acquire", "tests/sample_a.py", "purpose-a", "exclusive-edit"], session="S1", project_dir=fake_project)
    _run(["acquire", "tests/sample_b.py", "purpose-b", "shared-read"], session="S2", project_dir=fake_project)
    r = _run(["status"], project_dir=fake_project)
    assert r.returncode == 0
    import json
    data = json.loads(r.stdout)
    targets = [lock["target"] for lock in data["locks"]]
    assert "tests/sample_a.py" in targets
    assert "tests/sample_b.py" in targets


def test_release_mine_only_releases_own(fake_project):
    _run(["acquire", "tests/a.py", "x", "exclusive-edit"], session="A", project_dir=fake_project)
    _run(["acquire", "tests/b.py", "x", "exclusive-edit"], session="B", project_dir=fake_project)
    r = _run(["release-mine"], session="A", project_dir=fake_project)
    assert r.returncode == 0
    # A's lock gone
    r = _run(["check", "tests/a.py"], session="A", project_dir=fake_project)
    assert "FREE" in r.stdout
    # B's lock still held
    r = _run(["check", "tests/b.py"], session="A", project_dir=fake_project)
    assert "HELD" in r.stdout
    assert "session=B" in r.stdout


def test_bypass_skips_lock(fake_project):
    _run(["acquire", "tests/sample.py", "x", "exclusive-edit"], session="A", project_dir=fake_project)
    r = _run(
        ["acquire", "tests/sample.py", "y", "exclusive-edit"],
        session="B",
        env_extra={"COS_BYPASS_EDIT_LOCK": "1"},
        project_dir=fake_project,
    )
    assert r.returncode == 0
    assert "BYPASS" in r.stderr


def test_metadata_yaml_has_required_fields(fake_project):
    _run(["acquire", "tests/sample.py", "demo purpose", "exclusive-edit"], project_dir=fake_project)
    meta = fake_project / ".cognitive-os" / "runtime" / "edit-locks" / "tests--sample.py" / "meta.yaml"
    assert meta.exists()
    content = meta.read_text()
    for field in ("session_id:", "agent_id:", "target_file:", "intent:", "since:", "heartbeat:", "expires_at:", "purpose:", "status:"):
        assert field in content, f"missing required field {field!r} in meta.yaml"


def test_heartbeat_refreshes_only_own_lock(fake_project):
    _run(["acquire", "tests/sample.py", "x", "exclusive-edit"], session="A", project_dir=fake_project)
    r = _run(["heartbeat", "tests/sample.py"], session="A", project_dir=fake_project)
    assert r.returncode == 0
    r = _run(["heartbeat", "tests/sample.py"], session="B", project_dir=fake_project)
    assert r.returncode != 0
    assert "not owner" in r.stderr.lower()


def test_safe_path_collapses_slashes(fake_project):
    """Path traversal attempts get sanitized (no directory escape)."""
    _run(["acquire", "tests/sample.py", "x", "exclusive-edit"], project_dir=fake_project)
    locks_dir = fake_project / ".cognitive-os" / "runtime" / "edit-locks"
    safe = list(locks_dir.iterdir())
    # Exactly one lock dir, key uses "--" separator (no path traversal).
    assert len(safe) == 1
    assert safe[0].name == "tests--sample.py"
