# SCOPE: both
"""Portability probes for scripts/cos-session-start-projector (ADR-275).

Bilateral assertion: projector reads four optional sources (pending-truth,
operational-guide audit, control-plane remediation, staged dirs) plus git
state, and emits a deterministic schema regardless of which are missing.

Falsification probes:
  1. All sources absent -> still returns valid schema with zeros
  2. Only pending-truth present -> by_status counted, others empty
  3. Only OG audit present -> P0/P1 counted, top_backfill populated
  4. Staged dir present -> shows up in staged_deployments + ranked first in actions
  5. --json emits full machine payload; default emits to stderr

ADR reference: ADR-275 §1 projector contract.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "cos-session-start-projector"


def _run(project_dir: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("COGNITIVE_OS_PROJECT_DIR", None)
    env.pop("CODEX_PROJECT_DIR", None)
    env.pop("CLAUDE_PROJECT_DIR", None)
    env["COS_PROJECTOR_NOCACHE"] = "1"  # disable cache for deterministic tests
    cmd = [sys.executable, str(SCRIPT), "--project-dir", str(project_dir), *extra]
    return subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=15)


def _seed_pending_truth(project_dir: Path, items: list[dict]) -> None:
    reports = project_dir / "docs" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    by_status: dict[str, int] = {}
    for it in items:
        by_status[it["status"]] = by_status.get(it["status"], 0) + 1
    payload = {
        "schema_version": "pending-truth/v1",
        "generated_at": "2026-05-12T00:00:00Z",
        "summary": {"total_items": len(items), "by_status": by_status, "by_type": {}},
        "items": items,
    }
    (reports / "pending-truth-latest.json").write_text(json.dumps(payload))


def _seed_og_audit(project_dir: Path, results: list[dict]) -> None:
    reports = project_dir / "docs" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    by_priority: dict[str, int] = {}
    for r in results:
        if r.get("priority"):
            by_priority[r["priority"]] = by_priority.get(r["priority"], 0) + 1
    payload = {
        "schema_version": "operational-guide-audit/v1",
        "generated_at": "2026-05-12T00:00:00Z",
        "summary": {"total_adrs": len(results), "by_verdict": {}, "by_priority": by_priority},
        "results": results,
    }
    (reports / "operational-guide-audit-latest.json").write_text(json.dumps(payload))


def test_empty_project_returns_zeros(tmp_path: Path) -> None:
    """Falsification 1: no sources, no git -> valid schema with zeros."""
    cp = _run(tmp_path, "--json")
    assert cp.returncode == 0, cp.stderr
    payload = json.loads(cp.stdout)
    assert payload["schema_version"] == "session-start-projection/v1"
    s = payload["sections"]
    assert s["pending_truth"]["total"] == 0
    assert s["operational_guide"]["total_p0"] == 0
    assert s["control_plane"]["open_findings"] == 0
    assert s["staged_deployments"]["dirs"] == []


def test_bilateral_all_sources_populated(tmp_path: Path) -> None:
    """Bilateral: seed every source, every section reflects it."""
    _seed_pending_truth(tmp_path, [
        {"id": "p1", "type": "plan-checkbox", "source": "plans/x.md:L1",
         "status": "verified-pending", "next_action": "do X", "owner_adr": None},
        {"id": "p2", "type": "plan-checkbox", "source": "plans/x.md:L2",
         "status": "verified-done", "next_action": "", "owner_adr": None},
    ])
    _seed_og_audit(tmp_path, [
        {"adr": "ADR-100-x", "adr_num": 100, "path": "docs/adrs/ADR-100-x.md",
         "verdict": "missing", "priority": "P0", "age_days": 1, "tier": "maintainer",
         "status": "accepted", "subsection_count": 0},
    ])
    (tmp_path / "docs" / "runbooks" / "adr-X-staging").mkdir(parents=True)
    (tmp_path / "docs" / "runbooks" / "adr-X-staging" / "README.md").write_text("staged")

    cp = _run(tmp_path, "--json")
    assert cp.returncode == 0, cp.stderr
    payload = json.loads(cp.stdout)
    s = payload["sections"]
    assert s["pending_truth"]["total"] == 2
    assert s["pending_truth"]["by_status"]["verified-pending"] == 1
    assert len(s["pending_truth"]["top_actionable"]) == 1
    assert s["pending_truth"]["top_actionable"][0]["id"] == "p1"
    assert s["operational_guide"]["total_p0"] == 1
    assert len(s["operational_guide"]["top_backfill"]) == 1
    assert "adr-X-staging" in s["staged_deployments"]["dirs"][0]


def test_falsification_only_og_present(tmp_path: Path) -> None:
    """Falsification: only OG audit present, pending+cp+staged empty."""
    _seed_og_audit(tmp_path, [
        {"adr": "ADR-101-y", "adr_num": 101, "path": "docs/adrs/ADR-101-y.md",
         "verdict": "missing", "priority": "P1", "age_days": 100, "tier": "maintainer",
         "status": "accepted", "subsection_count": 0},
    ])
    cp = _run(tmp_path, "--json")
    payload = json.loads(cp.stdout)
    assert payload["sections"]["pending_truth"]["total"] == 0
    assert payload["sections"]["operational_guide"]["total_p1"] == 1


def test_suggested_actions_rank_staged_first(tmp_path: Path) -> None:
    """Bilateral: staged dirs outrank backfill items in suggested_next_actions."""
    _seed_og_audit(tmp_path, [
        {"adr": f"ADR-{200+i}-z", "adr_num": 200 + i, "path": f"docs/adrs/ADR-{200+i}-z.md",
         "verdict": "missing", "priority": "P0", "age_days": 1, "tier": "maintainer",
         "status": "accepted", "subsection_count": 0}
        for i in range(3)
    ])
    (tmp_path / "docs" / "runbooks" / "adr-Y-staging").mkdir(parents=True)

    cp = _run(tmp_path, "--json")
    payload = json.loads(cp.stdout)
    actions = payload["suggested_next_actions"]
    assert actions, "expected at least one suggested action"
    assert actions[0]["kind"] == "operator-deploy-staged", \
        f"staged should rank first, got {actions[0]['kind']}"


def test_json_vs_human_output_destinations(tmp_path: Path) -> None:
    """Bilateral: --json -> stdout; default -> stderr."""
    cp_json = _run(tmp_path, "--json")
    assert cp_json.stdout.strip(), "--json should write to stdout"
    cp_human = _run(tmp_path)
    assert cp_human.stderr.strip(), "default should write human text to stderr"
    assert "Session Start Projection" in cp_human.stderr


def test_strict_mode_emits_to_stdout(tmp_path: Path) -> None:
    """--strict mode emits human summary to stdout (for piping)."""
    cp = _run(tmp_path, "--strict")
    assert "Session Start Projection" in cp.stdout


def test_limit_caps_top_actionable(tmp_path: Path) -> None:
    """--limit N caps top_actionable to N items."""
    items = [
        {"id": f"p{i}", "type": "plan-checkbox", "source": f"plans/x.md:L{i}",
         "status": "verified-pending", "next_action": f"action{i}", "owner_adr": None}
        for i in range(10)
    ]
    _seed_pending_truth(tmp_path, items)
    cp = _run(tmp_path, "--json", "--limit", "3")
    payload = json.loads(cp.stdout)
    assert len(payload["sections"]["pending_truth"]["top_actionable"]) == 3
