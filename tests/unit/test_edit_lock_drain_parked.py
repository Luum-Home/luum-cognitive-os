"""Behavioral tests for hooks/edit-lock-drain-parked.sh — ADR-098 Phase D1."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / "hooks" / "edit-lock-drain-parked.sh"
COOP = REPO_ROOT / "scripts" / "edit-coop.sh"


def _run_hook(
    fake_project: Path,
    session: str = "session-A",
    tool_input_json: str = "",
    env_extra: dict | None = None,
) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["COGNITIVE_OS_SESSION_ID"] = session
    env["CLAUDE_PROJECT_DIR"] = str(fake_project)
    env["COGNITIVE_OS_PROJECT_DIR"] = str(fake_project)
    env.pop("COS_BYPASS_EDIT_LOCK", None)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", str(HOOK)],
        input=tool_input_json,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )


def _make_parked_edit(fake_project: Path, parked_session: str, safe_key: str) -> Path:
    """Create a stub parked-edit JSON file for a sibling session."""
    parked_dir = fake_project / ".cognitive-os" / "runtime" / "parked-edits" / parked_session
    parked_dir.mkdir(parents=True, exist_ok=True)
    parked_file = parked_dir / f"{safe_key}.json"
    parked_file.write_text(
        json.dumps({"file_key": safe_key, "planned_edit": "add a line", "session": parked_session})
        + "\n"
    )
    return parked_file


@pytest.fixture
def fake_project(tmp_path: Path) -> Path:
    (tmp_path / ".claude").mkdir()
    return tmp_path


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_no_parked_edits_exits_cleanly(fake_project):
    """Hook exits 0 and emits no errors when there are no parked edits."""
    r = _run_hook(fake_project)
    assert r.returncode == 0


def test_notice_created_for_matching_parked_edit(fake_project):
    """When a sibling session has a parked edit for the same file, a .notice is created."""
    safe_key = "tests--sample.py"
    _make_parked_edit(fake_project, parked_session="session-B", safe_key=safe_key)

    tool_input = json.dumps({
        "tool_input": {"file_path": "tests/sample.py"},
        "tool_response": {},
    })
    r = _run_hook(fake_project, session="session-A", tool_input_json=tool_input)
    assert r.returncode == 0

    notice_dir = fake_project / ".cognitive-os" / "runtime" / "parked-edits-pending" / "session-B"
    notice_file = notice_dir / f"{safe_key}.notice"
    assert notice_file.exists(), f"Expected notice file at {notice_file}"


def test_notice_contains_expected_fields(fake_project):
    """The .notice file records who released the lock and which parked file was found."""
    safe_key = "tests--sample.py"
    _make_parked_edit(fake_project, parked_session="session-B", safe_key=safe_key)

    tool_input = json.dumps({
        "tool_input": {"file_path": "tests/sample.py"},
        "tool_response": {},
    })
    _run_hook(fake_project, session="session-A", tool_input_json=tool_input)

    notice_file = (
        fake_project / ".cognitive-os" / "runtime" / "parked-edits-pending"
        / "session-B" / f"{safe_key}.notice"
    )
    content = notice_file.read_text()
    assert "released_by_session:" in content
    assert "session-A" in content
    assert "parked_file:" in content


def test_idempotent_double_run(fake_project):
    """Running the hook twice on the same file does not create duplicate notices."""
    safe_key = "tests--sample.py"
    _make_parked_edit(fake_project, parked_session="session-B", safe_key=safe_key)

    tool_input = json.dumps({
        "tool_input": {"file_path": "tests/sample.py"},
        "tool_response": {},
    })
    _run_hook(fake_project, session="session-A", tool_input_json=tool_input)
    r = _run_hook(fake_project, session="session-A", tool_input_json=tool_input)

    assert r.returncode == 0
    # Only one notice should exist.
    notice_dir = fake_project / ".cognitive-os" / "runtime" / "parked-edits-pending" / "session-B"
    notices = list(notice_dir.glob("*.notice"))
    assert len(notices) == 1
    assert "idempotent" in r.stderr.lower()


def test_own_parked_edits_not_surfaced(fake_project):
    """The hook does not surface parked edits belonging to the CURRENT session."""
    safe_key = "tests--sample.py"
    _make_parked_edit(fake_project, parked_session="session-A", safe_key=safe_key)

    tool_input = json.dumps({
        "tool_input": {"file_path": "tests/sample.py"},
        "tool_response": {},
    })
    r = _run_hook(fake_project, session="session-A", tool_input_json=tool_input)
    assert r.returncode == 0

    pending_root = fake_project / ".cognitive-os" / "runtime" / "parked-edits-pending"
    notices = list(pending_root.rglob("*.notice"))
    assert len(notices) == 0, "Should not create notice for own parked edit"


def test_bypass_suppresses_hook(fake_project):
    """COS_BYPASS_EDIT_LOCK=1 causes the hook to exit 0 immediately without scanning."""
    _make_parked_edit(fake_project, parked_session="session-B", safe_key="tests--sample.py")

    tool_input = json.dumps({"tool_input": {"file_path": "tests/sample.py"}})
    r = _run_hook(
        fake_project,
        session="session-A",
        tool_input_json=tool_input,
        env_extra={"COS_BYPASS_EDIT_LOCK": "1"},
    )
    assert r.returncode == 0
    pending_root = fake_project / ".cognitive-os" / "runtime" / "parked-edits-pending"
    assert not pending_root.exists() or len(list(pending_root.rglob("*.notice"))) == 0


def test_multiple_sibling_sessions_get_separate_notices(fake_project):
    """Each sibling session gets its own notice directory entry."""
    safe_key = "tests--shared.py"
    _make_parked_edit(fake_project, parked_session="session-B", safe_key=safe_key)
    _make_parked_edit(fake_project, parked_session="session-C", safe_key=safe_key)

    tool_input = json.dumps({"tool_input": {"file_path": "tests/shared.py"}})
    r = _run_hook(fake_project, session="session-A", tool_input_json=tool_input)
    assert r.returncode == 0

    pending_root = fake_project / ".cognitive-os" / "runtime" / "parked-edits-pending"
    notice_b = pending_root / "session-B" / f"{safe_key}.notice"
    notice_c = pending_root / "session-C" / f"{safe_key}.notice"
    assert notice_b.exists(), "session-B should have a notice"
    assert notice_c.exists(), "session-C should have a notice"


def test_no_match_on_different_file(fake_project):
    """Parked edits for a different file are NOT surfaced when editing a specific file."""
    _make_parked_edit(fake_project, parked_session="session-B", safe_key="other--file.py")

    tool_input = json.dumps({"tool_input": {"file_path": "tests/sample.py"}})
    r = _run_hook(fake_project, session="session-A", tool_input_json=tool_input)
    assert r.returncode == 0

    pending_root = fake_project / ".cognitive-os" / "runtime" / "parked-edits-pending"
    notices = list(pending_root.rglob("*.notice")) if pending_root.exists() else []
    assert len(notices) == 0, "Should not surface notice for different file"
