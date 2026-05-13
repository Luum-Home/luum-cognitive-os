# SCOPE: os-only
"""Portability probes for scripts/cos-pending-truth-aggregator (ADR-273 Slice A).

Bilateral assertion: aggregator runs against a synthetic project structure
mirroring the production layout (.cognitive-os/plans/, docs/02-Decisions/adrs/, sessions,
tasks) and produces a valid schema-v1 payload with items normalized from
each of the 5 source kinds.

Falsification probes:
  1. Empty project (no surfaces) -> empty items list, valid schema header.
  2. Plan checkbox already done (`[x]`) is NOT ingested as pending.
  3. ADR with `status: accepted` is NOT ingested as adr-slice.
  4. User-request with `status: done` is NOT ingested as pending.

ADR reference: ADR-273 §Slice A acceptance.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "cos-pending-truth-aggregator"


def _run(project_dir: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("COGNITIVE_OS_PROJECT_DIR", None)
    env.pop("CODEX_PROJECT_DIR", None)
    env.pop("CLAUDE_PROJECT_DIR", None)
    cmd = [sys.executable, str(SCRIPT), "--project-dir", str(project_dir), *extra]
    return subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=30)


def test_bilateral_aggregator_runs_against_synthetic_repo(tmp_path: Path) -> None:
    """Bilateral: build a synthetic project with 1 item of each source kind, assert aggregator finds all 5."""
    # Plan with one open + one done checkbox
    plan_dir = tmp_path / ".cognitive-os" / "plans" / "features"
    plan_dir.mkdir(parents=True)
    (plan_dir / "demo-plan.md").write_text(
        "# Demo plan\n\n- [ ] open item alpha\n- [x] done item beta\n",
        encoding="utf-8",
    )
    # ADR with status: proposed
    adr_dir = tmp_path / "docs" / "02-Decisions" / "adrs"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-999-demo.md").write_text(
        "---\nadr: 999\ntitle: Demo\nstatus: proposed\n---\n# ADR-999 Demo\n",
        encoding="utf-8",
    )
    # Radar tracker with one 🔲 row
    reports_dir = tmp_path / "docs" / "reports"
    reports_dir.mkdir(parents=True)
    (reports_dir / "radar-2026-05-08-implementation-tracker.md").write_text(
        "# Tracker\n\n| T1 | demo follow-up | 🔲 | source |\n",
        encoding="utf-8",
    )
    # User-request jsonl
    session_dir = tmp_path / ".cognitive-os" / "sessions" / "test-session"
    session_dir.mkdir(parents=True)
    (session_dir / "user-requests.jsonl").write_text(
        '{"timestamp":"2026-05-12T00:00:00Z","message":"demo pending request","status":"pending"}\n'
        '{"timestamp":"2026-05-12T00:00:00Z","message":"already done","status":"done"}\n',
        encoding="utf-8",
    )
    # Active-tasks json with one non-stale + one cancelled
    tasks_dir = tmp_path / ".cognitive-os" / "tasks"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / "active-tasks.json").write_text(
        json.dumps({"tasks": [
            {"id": "t-1", "description": "active task alpha", "status": "blocked_by_claim"},
            {"id": "t-2", "description": "cancelled stale", "status": "cancelled-stale"},
        ]}),
        encoding="utf-8",
    )

    result = _run(tmp_path)
    assert result.returncode == 0, f"stderr: {result.stderr}"
    payload = json.loads(result.stdout)

    assert payload["schema_version"] == "pending-truth/v1"
    by_type = payload["summary"]["by_type"]
    # All 5 source kinds present
    assert by_type.get("plan-checkbox", 0) == 1
    assert by_type.get("adr-slice", 0) == 1
    assert by_type.get("follow-up", 0) == 1
    assert by_type.get("user-request", 0) == 1
    assert by_type.get("audit-finding", 0) == 1
    assert payload["summary"]["total_items"] == 5
    # All items default to unverified per Slice A
    assert payload["summary"]["by_status"].get("unverified", 0) == 5


def test_falsification_empty_project_yields_empty_items(tmp_path: Path) -> None:
    """Falsification 1: empty project produces valid schema with 0 items."""
    result = _run(tmp_path)
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "pending-truth/v1"
    assert payload["summary"]["total_items"] == 0
    assert payload["items"] == []


def test_falsification_done_checkbox_not_ingested(tmp_path: Path) -> None:
    """Falsification 2: [x] DONE checkboxes are NOT ingested as pending."""
    plan_dir = tmp_path / ".cognitive-os" / "plans" / "features"
    plan_dir.mkdir(parents=True)
    (plan_dir / "all-done.md").write_text(
        "# All done\n\n- [x] item 1 done\n- [x] item 2 done\n- [x] item 3 done\n",
        encoding="utf-8",
    )
    result = _run(tmp_path)
    payload = json.loads(result.stdout)
    assert payload["summary"]["by_type"].get("plan-checkbox", 0) == 0, "DONE checkboxes leaked into pending"


def test_falsification_accepted_adr_not_ingested(tmp_path: Path) -> None:
    """Falsification 3: ADR with status: accepted is NOT a pending adr-slice."""
    adr_dir = tmp_path / "docs" / "02-Decisions" / "adrs"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-100-accepted.md").write_text(
        "---\nadr: 100\nstatus: accepted\n---\n# Accepted ADR\n",
        encoding="utf-8",
    )
    (adr_dir / "ADR-200-tombstone.md").write_text(
        "---\nadr: 200\nstatus: tombstone\n---\n# Tombstone ADR\n",
        encoding="utf-8",
    )
    result = _run(tmp_path)
    payload = json.loads(result.stdout)
    assert payload["summary"]["by_type"].get("adr-slice", 0) == 0, "non-pending ADR leaked into items"


def test_falsification_done_user_request_not_ingested(tmp_path: Path) -> None:
    """Falsification 4: user-request with status: done is NOT ingested."""
    session_dir = tmp_path / ".cognitive-os" / "sessions" / "s1"
    session_dir.mkdir(parents=True)
    (session_dir / "user-requests.jsonl").write_text(
        '{"timestamp":"2026-05-12T00:00:00Z","message":"already shipped","status":"done"}\n'
        '{"timestamp":"2026-05-12T00:00:00Z","message":"obsolete","status":"obsolete"}\n',
        encoding="utf-8",
    )
    result = _run(tmp_path)
    payload = json.loads(result.stdout)
    assert payload["summary"]["by_type"].get("user-request", 0) == 0, "non-pending user-request leaked"


def test_write_mode_emits_json_and_md(tmp_path: Path) -> None:
    """--write mode produces both pending-truth-latest.{json,md} at the expected path."""
    plan_dir = tmp_path / ".cognitive-os" / "plans" / "features"
    plan_dir.mkdir(parents=True)
    (plan_dir / "p.md").write_text("- [ ] one\n", encoding="utf-8")
    result = _run(tmp_path, "--write")
    assert result.returncode == 0, f"stderr: {result.stderr}"
    json_path = tmp_path / "docs" / "reports" / "pending-truth-latest.json"
    md_path = tmp_path / "docs" / "reports" / "pending-truth-latest.md"
    assert json_path.is_file()
    assert md_path.is_file()
    data = json.loads(json_path.read_text())
    assert data["schema_version"] == "pending-truth/v1"
    assert data["summary"]["total_items"] == 1
    assert "Pending Truth Ledger" in md_path.read_text()
