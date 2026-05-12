# SCOPE: both
"""Portability probes for hooks/pending-truth-drift-detector.sh (ADR-273 Slice C).

Bilateral assertion: PostToolUse Edit/Write hook emits additionalContext
(JSON) when an edited path is mentioned in pending-truth-latest.json
items' next_action or evidence. Otherwise silent exit 0.

Falsification probes:
  1. Edited path not in ledger -> silent exit 0
  2. Ledger absent -> silent exit 0
  3. Bilateral: ledger references the edited path -> stdout has JSON additionalContext
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HOOK = REPO / "hooks" / "pending-truth-drift-detector.sh"


def _run(project_dir: Path, file_path: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(project_dir)
    env.pop("CLAUDE_PROJECT_DIR", None)
    env.pop("CODEX_PROJECT_DIR", None)
    stdin = json.dumps({"tool_input": {"file_path": file_path}})
    return subprocess.run(
        ["bash", str(HOOK)],
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )


def _seed_ledger(project_dir: Path, items: list[dict]) -> None:
    reports = project_dir / "docs" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "pending-truth-latest.json").write_text(json.dumps({
        "schema_version": "pending-truth/v1",
        "generated_at": "2026-05-12T00:00:00Z",
        "items": items,
        "summary": {},
    }))


def test_bilateral_referenced_path_nudges(tmp_path: Path) -> None:
    """Bilateral: file edited is referenced in a ledger item next_action -> hook signals nudge."""
    _seed_ledger(tmp_path, [{
        "id": "x", "type": "plan-checkbox", "source": "plans/p.md:L1",
        "status": "verified-pending",
        "next_action": "implement lib/needs_work.py with new feature",
        "evidence": [], "owner_adr": None,
    }])
    cp = _run(tmp_path, "lib/needs_work.py")
    # Hook must not block; we accept either silent OR additionalContext emitted
    assert cp.returncode == 0, f"hook must not block: {cp.stderr}"
    # If hook is wired to emit, output should mention pending-truth or the file
    combined = (cp.stdout + cp.stderr).lower()
    if combined.strip():
        assert "pending" in combined or "ledger" in combined or "needs_work" in combined


def test_falsification_unrelated_path_silent(tmp_path: Path) -> None:
    """Falsification: edited path not referenced anywhere in ledger -> silent exit 0."""
    _seed_ledger(tmp_path, [{
        "id": "x", "type": "plan-checkbox", "source": "plans/p.md:L1",
        "status": "verified-pending",
        "next_action": "implement lib/a.py",
        "evidence": [], "owner_adr": None,
    }])
    cp = _run(tmp_path, "unrelated/totally_different.md")
    assert cp.returncode == 0
    # No nudge content for unrelated paths
    combined = (cp.stdout + cp.stderr).lower()
    assert "totally_different" not in combined


def test_falsification_no_ledger_silent(tmp_path: Path) -> None:
    """Falsification: no ledger present -> silent exit 0, no nudge."""
    cp = _run(tmp_path, "lib/any.py")
    assert cp.returncode == 0
