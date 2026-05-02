"""Unit tests for the portable cos_session_backlog reconciler."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


pytestmark = pytest.mark.unit

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "cos_session_backlog.py"

spec = importlib.util.spec_from_file_location("cos_session_backlog", SCRIPT_PATH)
assert spec and spec.loader
cos_session_backlog = importlib.util.module_from_spec(spec)
sys.modules["cos_session_backlog"] = cos_session_backlog
spec.loader.exec_module(cos_session_backlog)


def test_project_dir_precedence_prefers_cognitive_then_codex_then_claude(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The reconciler must not assume Claude is the only host."""
    canonical = tmp_path / "canonical"
    codex = tmp_path / "codex"
    claude = tmp_path / "claude"
    for path in (canonical, codex, claude):
        path.mkdir()

    monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", str(canonical))
    monkeypatch.setenv("CODEX_PROJECT_DIR", str(codex))
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(claude))
    assert cos_session_backlog.resolve_project_dir() == canonical.resolve()

    monkeypatch.delenv("COGNITIVE_OS_PROJECT_DIR")
    assert cos_session_backlog.resolve_project_dir() == codex.resolve()

    monkeypatch.delenv("CODEX_PROJECT_DIR")
    assert cos_session_backlog.resolve_project_dir() == claude.resolve()


def test_session_id_precedence_prefers_cognitive_then_codex_then_claude(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Session ids use the same canonical cross-harness order."""
    monkeypatch.setenv("COGNITIVE_OS_SESSION_ID", "cos-session")
    monkeypatch.setenv("CODEX_SESSION_ID", "codex-session")
    monkeypatch.setenv("CLAUDE_SESSION_ID", "claude-session")
    assert cos_session_backlog.resolve_session_id() == "cos-session"

    monkeypatch.delenv("COGNITIVE_OS_SESSION_ID")
    assert cos_session_backlog.resolve_session_id() == "codex-session"

    monkeypatch.delenv("CODEX_SESSION_ID")
    assert cos_session_backlog.resolve_session_id() == "claude-session"


def test_reconciler_writes_backlog_and_metric_from_core_sources(tmp_path: Path) -> None:
    """Active tasks, plans, user queues, changelogs, and handoffs are reconciled."""
    project = tmp_path / "project"
    project.mkdir()
    (project / ".cognitive-os" / "tasks").mkdir(parents=True)
    (project / ".cognitive-os" / "plans" / "features").mkdir(parents=True)
    (project / ".cognitive-os" / "sessions" / "session-1").mkdir(parents=True)
    (project / ".cognitive-os" / "changelogs").mkdir(parents=True)
    (project / "docs" / "adrs").mkdir(parents=True)
    (project / "scripts").mkdir(parents=True)

    (project / ".cognitive-os" / "tasks" / "active-tasks.json").write_text(
        json.dumps(
            {
                "tasks": [
                    {"id": "t1", "description": "Fix portable backlog", "status": "in_progress"},
                    {"id": "t2", "description": "Already done", "status": "completed"},
                ]
            }
        )
    )
    (project / ".cognitive-os" / "plans" / "features" / "plan.md").write_text(
        "# Portable Plan\n\n- [x] Done task\n- [ ] Add Codex path\n- [ ] Add Claude path\n"
    )
    (project / ".cognitive-os" / "sessions" / "session-1" / "user-requests.jsonl").write_text(
        json.dumps({"status": "pending", "message": "User asked for backlog", "timestamp": "2026-05-02T00:00:00Z"}) + "\n"
    )
    (project / ".cognitive-os" / "changelogs" / "session-1.md").write_text(
        "# Changelog\n\n## Next Steps\n\n- Verify portable command\n"
    )
    (project / "docs" / "SESSION-HANDOFF-2026-05-02.md").write_text(
        "# Handoff\n\n## Next Steps\n\n- Commit reconciler\n"
    )
    (project / "docs" / "adrs" / "ADR-001-pending.md").write_text(
        "# ADR-001 Pending\n\n## Status\nAccepted.\n"
    )
    (project / "scripts" / "adr_implementation_ledger.py").write_text(
        (PROJECT_ROOT / "scripts" / "adr_implementation_ledger.py").read_text()
    )

    result = cos_session_backlog.reconcile(project, "session-1", include_engram=False)
    markdown = cos_session_backlog.render_markdown(
        result,
        project,
        "session-1",
        cos_session_backlog.parse_now("2026-05-02T00:00:00Z"),
    )
    backlog_path, metric_path = cos_session_backlog.write_outputs(
        project,
        "session-1",
        markdown,
        result,
        cos_session_backlog.parse_now("2026-05-02T00:00:00Z"),
    )

    assert backlog_path.exists()
    assert metric_path.exists()
    written = backlog_path.read_text()
    assert "Fix portable backlog" in written
    assert "Add Codex path" in written
    assert "User asked for backlog" in written
    assert "Verify portable command" in written
    assert "Commit reconciler" in written
    assert "Resolve ADR implementation status: ADR-001-pending" in written

    metric = json.loads(metric_path.read_text().splitlines()[-1])
    assert metric["event"] == "backlog_reconciled"
    assert metric["priority_counts"]["1"] >= 2
    assert "active-tasks" in metric["sources"]
    assert "plans" in metric["sources"]
    assert "adr-ledger" in metric["sources"]


def test_cli_json_summary_reports_written_paths(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """CLI mode writes outputs and reports a machine-readable summary."""
    project = tmp_path / "project"
    project.mkdir()
    exit_code = cos_session_backlog.main(
        [
            "--project-dir",
            str(project),
            "--session-id",
            "s1",
            "--write",
            "--no-engram",
            "--json",
            "--now",
            "2026-05-02T00:00:00Z",
        ]
    )
    assert exit_code == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["backlog_path"].endswith(".cognitive-os/sessions/s1/backlog.md")
    assert summary["metric_path"].endswith(".cognitive-os/metrics/backlog-reconciliation.jsonl")
    assert Path(summary["backlog_path"]).exists()
    assert Path(summary["metric_path"]).exists()


def test_session_backlog_skill_points_to_portable_reconciler() -> None:
    """The user-invocable skill should route cross-harness users to the script."""
    skill = (PROJECT_ROOT / "skills" / "session-backlog" / "SKILL.md").read_text()
    assert "scripts/cos_session_backlog.py --write --sync-engram" in skill
    assert "install-meta.json" in skill
    assert '--project-dir "$PROJECT_DIR" --session-id "$SESSION_ID"' in skill
    assert "COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR" in skill
    assert 'platforms: ["codex", "claude-code", "generic-cli"]' in skill
