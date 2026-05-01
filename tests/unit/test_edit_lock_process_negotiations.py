"""Behavioral tests for hooks/edit-lock-process-negotiations.sh — ADR-098 Phase D2."""
from __future__ import annotations

import os
import subprocess
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / "hooks" / "edit-lock-process-negotiations.sh"
COOP = REPO_ROOT / "scripts" / "edit-coop.sh"


def _run_hook(
    fake_project: Path,
    session: str = "session-A",
    env_extra: dict | None = None,
) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["COGNITIVE_OS_SESSION_ID"] = session
    env["CLAUDE_PROJECT_DIR"] = str(fake_project)
    env["COGNITIVE_OS_PROJECT_DIR"] = str(fake_project)
    env.setdefault("COS_EDIT_LOCK_NO_PID_CHECK", "1")
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", str(HOOK)],
        input="",
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )


def _make_negotiation_request(
    fake_project: Path,
    my_session: str,
    requester_session: str,
    target_file: str = "tests/sample.py",
    intent: str = "exclusive-edit",
) -> Path:
    """Create a negotiation request YAML in my_session's inbox."""
    inbox = (
        fake_project / ".cognitive-os" / "runtime" / "edit-negotiations" / my_session
    )
    inbox.mkdir(parents=True, exist_ok=True)
    req_file = inbox / f"{requester_session}.yaml"
    req_file.write_text(
        textwrap.dedent(f"""\
            requester_session: "{requester_session}"
            target_file: "{target_file}"
            intent: "{intent}"
            purpose: "testing negotiation"
            requested_at: "2026-04-30T10:00:00Z"
        """)
    )
    return req_file


@pytest.fixture
def fake_project(tmp_path: Path) -> Path:
    (tmp_path / ".claude").mkdir()
    return tmp_path


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_no_inbox_exits_cleanly(fake_project):
    """Hook exits 0 when there is no inbox directory for this session."""
    r = _run_hook(fake_project, session="session-A")
    assert r.returncode == 0


def test_seen_at_appended_to_request(fake_project):
    """Processing a negotiation request appends seen_at to the YAML."""
    req_file = _make_negotiation_request(fake_project, my_session="session-A", requester_session="session-B")

    r = _run_hook(fake_project, session="session-A")
    assert r.returncode == 0

    content = req_file.read_text()
    assert "seen_at:" in content, "seen_at must be appended to the request YAML"


def test_seen_at_is_iso8601(fake_project):
    """The seen_at timestamp looks like a valid ISO-8601 UTC timestamp."""
    req_file = _make_negotiation_request(fake_project, my_session="session-A", requester_session="session-B")
    _run_hook(fake_project, session="session-A")

    content = req_file.read_text()
    seen_line = next((l for l in content.splitlines() if l.startswith("seen_at:")), "")
    assert "T" in seen_line and "Z" in seen_line, f"seen_at should be ISO-8601, got: {seen_line!r}"


def test_already_seen_request_is_skipped(fake_project):
    """A request that already has seen_at is silently skipped (idempotent)."""
    req_file = _make_negotiation_request(fake_project, my_session="session-A", requester_session="session-B")
    # Pre-mark as seen.
    req_file.write_text(req_file.read_text() + 'seen_at: "2026-04-30T09:00:00Z"\n')
    original_content = req_file.read_text()

    r = _run_hook(fake_project, session="session-A")
    assert r.returncode == 0

    content = req_file.read_text()
    # Content should be unchanged (no duplicate seen_at).
    assert content.count("seen_at:") == 1, "seen_at should not be appended twice"
    assert "skipped" in r.stderr.lower(), "Hook should report skipped-seen count"


def test_multiple_requests_all_marked_seen(fake_project):
    """Multiple incoming requests in the inbox are all processed."""
    _make_negotiation_request(fake_project, my_session="session-A", requester_session="session-B")
    _make_negotiation_request(fake_project, my_session="session-A", requester_session="session-C")

    r = _run_hook(fake_project, session="session-A")
    assert r.returncode == 0

    inbox = fake_project / ".cognitive-os" / "runtime" / "edit-negotiations" / "session-A"
    for req_file in inbox.glob("*.yaml"):
        content = req_file.read_text()
        assert "seen_at:" in content, f"seen_at missing from {req_file.name}"


def test_stderr_contains_structured_output(fake_project):
    """The hook surfaces request details to stderr in a structured, agent-readable format."""
    _make_negotiation_request(
        fake_project, my_session="session-A", requester_session="session-B",
        target_file="tests/conftest.py",
    )
    r = _run_hook(fake_project, session="session-A")
    assert r.returncode == 0
    # Should surface the requester session and target file.
    assert "session-B" in r.stderr
    assert "tests/conftest.py" in r.stderr
    assert "NEGOTIATION" in r.stderr.upper()


def test_does_not_process_other_sessions_inbox(fake_project):
    """The hook only processes its OWN inbox, not other sessions' inboxes."""
    # Create a request for session-B's inbox.
    _make_negotiation_request(fake_project, my_session="session-B", requester_session="session-C")

    # Run as session-A — should not touch session-B's inbox.
    r = _run_hook(fake_project, session="session-A")
    assert r.returncode == 0

    req_file = (
        fake_project / ".cognitive-os" / "runtime" / "edit-negotiations"
        / "session-B" / "session-C.yaml"
    )
    content = req_file.read_text()
    assert "seen_at:" not in content, "Must not process another session's inbox"


def test_hook_exits_zero_on_empty_inbox(fake_project):
    """Hook exits 0 when the inbox directory exists but has no request files."""
    inbox = fake_project / ".cognitive-os" / "runtime" / "edit-negotiations" / "session-A"
    inbox.mkdir(parents=True)

    r = _run_hook(fake_project, session="session-A")
    assert r.returncode == 0
