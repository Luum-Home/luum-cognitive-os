# SCOPE: os-only
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
    reports = project_dir / "docs" / "06-Daily" / "reports"
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
    reports = project_dir / "docs" / "06-Daily" / "reports"
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
        {"adr": "ADR-100-x", "adr_num": 100, "path": "docs/02-Decisions/adrs/ADR-100-x.md",
         "verdict": "missing", "priority": "P0", "age_days": 1, "tier": "maintainer",
         "status": "accepted", "subsection_count": 0},
    ])
    (tmp_path / "docs" / "05-Methodology" / "runbooks" / "adr-X-staging").mkdir(parents=True)
    (tmp_path / "docs" / "05-Methodology" / "runbooks" / "adr-X-staging" / "README.md").write_text("staged")

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
        {"adr": "ADR-101-y", "adr_num": 101, "path": "docs/02-Decisions/adrs/ADR-101-y.md",
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
        {"adr": f"ADR-{200+i}-z", "adr_num": 200 + i, "path": f"docs/02-Decisions/adrs/ADR-{200+i}-z.md",
         "verdict": "missing", "priority": "P0", "age_days": 1, "tier": "maintainer",
         "status": "accepted", "subsection_count": 0}
        for i in range(3)
    ])
    (tmp_path / "docs" / "05-Methodology" / "runbooks" / "adr-Y-staging").mkdir(parents=True)

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


def _seed_adr_partial_backlog(project_dir: Path, items: list[dict]) -> None:
    reports = project_dir / "docs" / "06-Daily" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    by_impl: dict[str, int] = {}
    for item in items:
        status = item["implementation_status"]
        by_impl[status] = by_impl.get(status, 0) + 1
    payload = {
        "schema_version": "adr-partial-backlog/v1",
        "generated_at": "<generated>",
        "summary": {
            "total": len(items),
            "by_implementation_status": by_impl,
            "missing_partial_remaining": sum(1 for item in items if not item.get("partial_remaining")),
        },
        "items": items,
    }
    (reports / "adr-partial-backlog-latest.json").write_text(json.dumps(payload))


def test_adr_partial_backlog_is_first_class_projector_source(tmp_path: Path) -> None:
    """ADR lifecycle debt is projected next to pending-truth, not hidden in docs."""
    _seed_adr_partial_backlog(tmp_path, [
        {
            "adr": "ADR-234",
            "path": "docs/02-Decisions/adrs/ADR-234-approval-policies-as-code.md",
            "implementation_status": "partial",
            "classification_basis": "advisory implementation exists; blocking promotion remains pending",
            "remaining": "blocking promotion remains pending",
            "partial_remaining": "blocking promotion after soak",
            "implementation_files": [],
        },
        {
            "adr": "ADR-236",
            "path": "docs/02-Decisions/adrs/ADR-236-deferred-tool-loading-and-toolsearch.md",
            "implementation_status": "partial",
            "classification_basis": "Slices A-D implemented; transport remains explicitly not implemented",
            "remaining": "transport remains explicitly not implemented",
            "partial_remaining": "real MCP list_changed transport emission",
            "implementation_files": [],
        },
    ])

    cp = _run(tmp_path, "--json", "--limit", "5")
    assert cp.returncode == 0, cp.stderr
    payload = json.loads(cp.stdout)
    adr_partials = payload["sections"]["adr_partials"]
    assert adr_partials["total"] == 2
    assert adr_partials["by_implementation_status"] == {"partial": 2}
    assert adr_partials["top_actionable"][0]["adr"] == "ADR-234"
    assert any(action["kind"] == "adr-partial-close" for action in payload["suggested_next_actions"])


def test_control_plane_counts_findings_not_event_rows(tmp_path: Path) -> None:
    """Regression: the remediation JSONL is an append-only proposal log.

    Seeded with 30 rows over 3 stable_ids of which 1 is active, the projector
    must report 1 open finding (state-machine authority) and expose the row
    count separately as `queue_event_rows`.
    """
    tasks = tmp_path / ".cognitive-os" / "tasks"
    tasks.mkdir(parents=True)
    with (tasks / "control-plane-remediation.jsonl").open("w", encoding="utf-8") as fh:
        for i in range(30):
            fh.write(json.dumps({
                "event": "proposed", "status": "queued", "adr": "ADR-001",
                "stable_id": f"sid{i % 3}", "created_at": "2026-05-14T16:11:33Z",
            }) + "\n")
    state_dir = tmp_path / ".cognitive-os" / "runtime" / "control-plane-audit"
    state_dir.mkdir(parents=True)
    (state_dir / "findings-state.json").write_text(json.dumps({
        "updated_at": "2026-08-21T00:00:00Z",
        "findings": {
            "sid0": {"stable_id": "sid0", "status": "active", "adr": "ADR-001"},
            "sid1": {"stable_id": "sid1", "status": "resolved", "adr": "ADR-001"},
            "sid2": {"stable_id": "sid2", "status": "resolved", "adr": "ADR-001"},
        },
    }))

    cp = _run(tmp_path, "--json")
    assert cp.returncode == 0, cp.stderr
    section = json.loads(cp.stdout)["sections"]["control_plane"]
    assert section["open_findings"] == 1, section
    assert section["open_findings_known"] is True
    assert section["queue_event_rows"] == 30
    assert section["queue_distinct_findings"] == 3
    assert section["queue_window"]["first_event_at"] == "2026-05-14T16:11:33Z"


def test_control_plane_declines_to_count_without_state_machine(tmp_path: Path) -> None:
    """Falsification: log rows but no state machine -> null + stated reason."""
    tasks = tmp_path / ".cognitive-os" / "tasks"
    tasks.mkdir(parents=True)
    (tasks / "control-plane-remediation.jsonl").write_text(
        json.dumps({"event": "proposed", "status": "queued", "stable_id": "sid0"}) + "\n"
    )
    cp = _run(tmp_path, "--json")
    assert cp.returncode == 0, cp.stderr
    section = json.loads(cp.stdout)["sections"]["control_plane"]
    assert section["open_findings"] is None
    assert section["open_findings_known"] is False
    assert "findings-state.json" in section["unknown_reason"]
    human = _run(tmp_path)
    assert "control-plane open findings: UNKNOWN" in human.stderr, human.stderr


def test_operational_guide_priority_zero_is_not_invented(tmp_path: Path) -> None:
    """Falsification: results present but no `priority` field -> unknown, not 0."""
    reports = tmp_path / "docs" / "06-Daily" / "reports"
    reports.mkdir(parents=True)
    (reports / "operational-guide-audit-latest.json").write_text(json.dumps({
        "generated_at": "2026-05-12T17:12:06Z",
        "summary": {"total_adrs": 2, "by_verdict": {}, "by_priority": {}},
        "results": [{"adr": "ADR-001", "verdict": "compliant"}, {"adr": "ADR-002", "verdict": "compliant"}],
    }))
    cp = _run(tmp_path, "--json")
    assert cp.returncode == 0, cp.stderr
    og = json.loads(cp.stdout)["sections"]["operational_guide"]
    assert og["total_p0"] is None and og["total_p1"] is None
    assert og["priorities_known"] is False
    assert og["results_total"] == 2
