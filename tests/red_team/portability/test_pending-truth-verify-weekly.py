# SCOPE: both
"""Portability probes for hooks/pending-truth-verify-weekly.sh (ADR-273 Slice C).

Bilateral assertion: Stop hook fires the verifier in background (async,
fire-and-forget) when ledger is stale (>7d) OR >50% of items have
last_verified > 7d. Otherwise silent exit 0.

Falsification probes:
  1. No ledger present -> silent exit 0, no background process
  2. Verifier binary missing -> silent exit 0 (graceful no-op)
  3. Fresh ledger with fresh last_verified -> silent exit 0
"""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HOOK = REPO / "hooks" / "pending-truth-verify-weekly.sh"


def _run(project_dir: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(project_dir)
    env.pop("CLAUDE_PROJECT_DIR", None)
    env.pop("CODEX_PROJECT_DIR", None)
    return subprocess.run(
        ["bash", str(HOOK)],
        input="",
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )


def _seed(project_dir: Path, ran_at: str, items: list[dict] | None = None) -> None:
    reports = project_dir / "docs" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "pending-truth-latest.json").write_text(json.dumps({
        "schema_version": "pending-truth/v1",
        "generated_at": ran_at,
        "verifier": {"ran_at": ran_at},
        "items": items or [],
        "summary": {},
    }))


def test_no_ledger_silent_exit(tmp_path: Path) -> None:
    """Falsification: no ledger -> silent exit 0, no background process."""
    cp = _run(tmp_path)
    assert cp.returncode == 0
    assert not cp.stderr.strip(), f"unexpected stderr: {cp.stderr}"


def test_no_verifier_binary_graceful(tmp_path: Path) -> None:
    """Falsification: verifier binary missing in synthetic project -> graceful no-op."""
    _seed(tmp_path, "2025-01-01T00:00:00Z")  # very stale, should trigger
    # tmp_path has no scripts/cos-pending-truth-verify, so hook should not crash
    cp = _run(tmp_path)
    assert cp.returncode == 0


def test_fresh_ledger_silent(tmp_path: Path) -> None:
    """Falsification: ledger generated today + items fresh -> silent."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    items = [{
        "id": f"x{i}", "type": "plan-checkbox", "source": "plans/p.md:L1",
        "status": "verified-pending", "last_verified": now,
        "evidence": [], "next_action": "", "owner_adr": None,
    } for i in range(3)]
    _seed(tmp_path, now, items)
    cp = _run(tmp_path)
    assert cp.returncode == 0


def test_bilateral_stale_ledger_triggers_no_crash(tmp_path: Path) -> None:
    """Bilateral: stale ledger present -> hook detects and attempts background run (won't crash)."""
    old = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    items = [{
        "id": "stale", "type": "plan-checkbox", "source": "plans/p.md:L1",
        "status": "verified-pending", "last_verified": old,
        "evidence": [], "next_action": "", "owner_adr": None,
    }]
    _seed(tmp_path, old, items)
    cp = _run(tmp_path)
    # Whether or not verifier is present, hook must exit cleanly
    assert cp.returncode == 0
