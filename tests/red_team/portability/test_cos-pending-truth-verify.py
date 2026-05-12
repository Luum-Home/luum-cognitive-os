# SCOPE: both
"""Portability probes for scripts/cos-pending-truth-verify (ADR-273 Slice B).

Bilateral assertion: verifier reads a synthetic ledger, runs deterministic
evidence checks (no LLM), and reclassifies items based on whether referenced
paths exist in a synthetic project.

Falsification probes:
  1. Item with missing paths -> verified-pending
  2. Item with all paths existing -> verified-done
  3. Item with partial paths -> ambiguous
  4. Item with obsolete marker -> obsolete
  5. ADR-slice with accepted ADR -> verified-done

ADR reference: ADR-273 §3 Slice B verifier contract.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "cos-pending-truth-verify"


def _seed_ledger(project_dir: Path, items: list[dict]) -> None:
    reports = project_dir / "docs" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "pending-truth/v1",
        "generated_at": "2026-05-12T00:00:00Z",
        "project_dir": "<repo-root>",
        "summary": {"total_items": len(items), "by_type": {}, "by_status": {}},
        "items": items,
    }
    (reports / "pending-truth-latest.json").write_text(json.dumps(payload, indent=2))


def _run(project_dir: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("COGNITIVE_OS_PROJECT_DIR", None)
    env.pop("CODEX_PROJECT_DIR", None)
    env.pop("CLAUDE_PROJECT_DIR", None)
    cmd = [sys.executable, str(SCRIPT), "--project-dir", str(project_dir), "--json", *extra]
    return subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=30)


def _classify_after_run(project_dir: Path) -> dict[str, str]:
    json_path = project_dir / "docs" / "reports" / "pending-truth-latest.json"
    data = json.loads(json_path.read_text())
    return {item["id"]: item["status"] for item in data["items"]}


def test_bilateral_verifier_reclassifies_items(tmp_path: Path) -> None:
    """Bilateral: seed 5 items, run verifier, check each gets correct status."""
    # Seed project files for tests
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "exists.py").write_text("# present\n")
    adr_dir = tmp_path / "docs" / "adrs"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-100-demo.md").write_text("---\nadr: 100\nstatus: accepted\n---\n")

    _seed_ledger(tmp_path, [
        {"id": "all-exist", "type": "plan-checkbox",
         "source": "plans/demo.md:L1", "status": "unverified",
         "last_verified": None, "evidence": [],
         "next_action": "implement lib/exists.py", "owner_adr": None},
        {"id": "all-missing", "type": "plan-checkbox",
         "source": "plans/demo.md:L2", "status": "unverified",
         "last_verified": None, "evidence": [],
         "next_action": "create lib/missing_one.py and lib/missing_two.py", "owner_adr": None},
        {"id": "partial", "type": "plan-checkbox",
         "source": "plans/demo.md:L3", "status": "unverified",
         "last_verified": None, "evidence": [],
         "next_action": "implement lib/exists.py and lib/missing_one.py", "owner_adr": None},
        {"id": "obs", "type": "plan-checkbox",
         "source": "plans/demo.md:L4", "status": "unverified",
         "last_verified": None, "evidence": [],
         "next_action": "this is obsolete and tombstoned", "owner_adr": None},
        {"id": "adr-100", "type": "adr-slice",
         "source": "docs/02-Decisions/adrs/ADR-100-demo.md", "status": "unverified",
         "last_verified": None, "evidence": [],
         "next_action": "resolve ADR-100", "owner_adr": "ADR-100"},
    ])

    result = _run(tmp_path)
    assert result.returncode == 0, f"stderr: {result.stderr}"

    statuses = _classify_after_run(tmp_path)
    assert statuses["all-exist"] == "verified-done", f"got {statuses}"
    assert statuses["all-missing"] == "verified-pending"
    assert statuses["partial"] == "ambiguous"
    assert statuses["obs"] == "obsolete"
    assert statuses["adr-100"] == "verified-done"


def test_falsification_missing_paths_yields_pending(tmp_path: Path) -> None:
    """Falsification 1: items whose referenced paths don't exist must be verified-pending."""
    _seed_ledger(tmp_path, [
        {"id": "x", "type": "plan-checkbox",
         "source": "plans/demo.md:L1", "status": "unverified",
         "last_verified": None, "evidence": [],
         "next_action": "create lib/never_existed_test.py", "owner_adr": None},
    ])
    _run(tmp_path)
    statuses = _classify_after_run(tmp_path)
    assert statuses["x"] == "verified-pending"


def test_falsification_no_paths_in_text(tmp_path: Path) -> None:
    """Falsification 2: items with no path-like tokens default to verified-pending."""
    _seed_ledger(tmp_path, [
        {"id": "vague", "type": "plan-checkbox",
         "source": "plans/demo.md:L1", "status": "unverified",
         "last_verified": None, "evidence": [],
         "next_action": "improve performance somehow", "owner_adr": None},
    ])
    _run(tmp_path)
    statuses = _classify_after_run(tmp_path)
    assert statuses["vague"] == "verified-pending"


def test_dry_run_does_not_modify_ledger(tmp_path: Path) -> None:
    """--dry-run mode prints results but does not overwrite the json."""
    initial = {
        "schema_version": "pending-truth/v1",
        "generated_at": "2026-05-12T00:00:00Z",
        "project_dir": "<repo-root>",
        "summary": {"total_items": 1, "by_type": {"plan-checkbox": 1}, "by_status": {"unverified": 1}},
        "items": [{"id": "x", "type": "plan-checkbox", "source": "p:L1",
                   "status": "unverified", "last_verified": None, "evidence": [],
                   "next_action": "do something", "owner_adr": None}],
    }
    reports = tmp_path / "docs" / "reports"
    reports.mkdir(parents=True)
    (reports / "pending-truth-latest.json").write_text(json.dumps(initial))

    _run(tmp_path, "--dry-run")
    after = json.loads((reports / "pending-truth-latest.json").read_text())
    assert after["items"][0]["status"] == "unverified", "dry-run mutated ledger"


def test_audit_finding_status_translated(tmp_path: Path) -> None:
    """Falsification: audit-finding with task_status=blocked_by_claim -> verified-pending."""
    _seed_ledger(tmp_path, [
        {"id": "t1", "type": "audit-finding",
         "source": ".cognitive-os/tasks/active-tasks.json", "status": "unverified",
         "last_verified": None,
         "evidence": [{"kind": "task_status", "result": "blocked_by_claim"}],
         "next_action": "P4.3 stash auto-reapply", "owner_adr": None},
        {"id": "t2", "type": "audit-finding",
         "source": ".cognitive-os/tasks/active-tasks.json", "status": "unverified",
         "last_verified": None,
         "evidence": [{"kind": "task_status", "result": "cancelled-stale"}],
         "next_action": "old task", "owner_adr": None},
    ])
    _run(tmp_path)
    statuses = _classify_after_run(tmp_path)
    assert statuses["t1"] == "verified-pending"
    assert statuses["t2"] == "obsolete"
