# SCOPE: os-only
"""Portability proof for lib/audit_id.py."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from lib.audit_id import get_current_audit_context  # noqa: E402


def test_audit_context_reads_optional_state_from_arbitrary_project(tmp_path: Path, monkeypatch) -> None:
    """Falsification probe: audit IDs must not require git or COS repo layout."""
    monkeypatch.setenv("COGNITIVE_OS_SESSION_ID", "portable-session")
    state = tmp_path / ".cognitive-os" / "workflows" / "state"
    state.mkdir(parents=True)
    (state / "sprint-status.yaml").write_text('sprint_id: "portable-sprint"\n', encoding="utf-8")
    change = tmp_path / ".cognitive-os" / "pipeline-state"
    change.mkdir(parents=True)
    (change / "current-change.txt").write_text("portable-change\n", encoding="utf-8")
    ctx = get_current_audit_context(str(tmp_path))
    assert ctx.session_id == "portable-session"
    assert ctx.sprint_id == "portable-sprint"
    assert ctx.change_id == "portable-change"
