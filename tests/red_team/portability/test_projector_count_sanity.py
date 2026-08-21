# SCOPE: os-only
"""Falsification probes for scripts/projector_count_sanity.py.

The gate guards the counts that head the session-start brief (ADR-275): a
number may not exceed the universe its label names, and a null count must
carry a stated reason.

Bilateral probes (each mutation must flip the verdict, never both branches
green):
  1. Coherent projection over seeded sources          -> exit 0
  2. open_findings inflated to the event-row count    -> exit 1 order-of-magnitude
  3. open_findings null WITHOUT a reason              -> exit 1 silent-null
  4. open_findings null WITH a reason                 -> exit 0 (valid answer)
  5. P0/P1 numbers over a source with no priority     -> exit 1 false-zero
  6. staged dir count disagreeing with disk           -> exit 1 mismatch
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
GATE = REPO_ROOT / "scripts" / "projector_count_sanity.py"


def _seed_sources(root: Path, *, queue_rows: int = 40, distinct: int = 4) -> None:
    tasks = root / ".cognitive-os" / "tasks"
    tasks.mkdir(parents=True, exist_ok=True)
    with (tasks / "control-plane-remediation.jsonl").open("w", encoding="utf-8") as fh:
        for i in range(queue_rows):
            fh.write(json.dumps({
                "event": "proposed",
                "status": "queued",
                "stable_id": f"sid{i % distinct}",
                "adr": "ADR-001",
                "created_at": "2026-05-14T16:11:33Z",
            }) + "\n")
    state_dir = root / ".cognitive-os" / "runtime" / "control-plane-audit"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "findings-state.json").write_text(json.dumps({
        "updated_at": "2026-08-21T00:00:00Z",
        "findings": {
            f"sid{i}": {"stable_id": f"sid{i}", "status": "active" if i < 2 else "resolved", "adr": "ADR-001"}
            for i in range(distinct)
        },
    }))
    reports = root / "docs" / "06-Daily" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "pending-truth-latest.json").write_text(json.dumps({
        "generated_at": "2026-08-01T00:00:00Z",
        "summary": {"total_items": 3},
        "items": [
            {"id": "a", "status": "verified-pending"},
            {"id": "b", "status": "verified-pending"},
            {"id": "c", "status": "verified-done"},
        ],
    }))
    (reports / "operational-guide-audit-latest.json").write_text(json.dumps({
        "generated_at": "2026-08-01T00:00:00Z",
        "summary": {"total_adrs": 2, "by_priority": {}},
        "results": [{"adr": "ADR-001"}, {"adr": "ADR-002"}],  # no `priority` key anywhere
    }))
    (reports / "adr-partial-backlog-latest.json").write_text(json.dumps({
        "summary": {"total": 2, "by_implementation_status": {"partial": 2}, "missing_partial_remaining": 0},
        "items": [{"adr": "ADR-001"}, {"adr": "ADR-002"}],
    }))
    (root / "docs" / "05-Methodology" / "runbooks" / "x-staging").mkdir(parents=True, exist_ok=True)


def _projection(**overrides) -> dict:
    cp = {
        "open_findings": 2,
        "open_findings_known": True,
        "unknown_reason": None,
        "tracked_findings": 4,
        "queue_event_rows": 40,
        "queue_distinct_findings": 4,
    }
    cp.update(overrides.pop("control_plane", {}))
    og = {"total_p0": None, "total_p1": None, "priorities_known": False, "unknown_reason": "no priority field"}
    og.update(overrides.pop("operational_guide", {}))
    staged = {"dirs": ["docs/05-Methodology/runbooks/x-staging"]}
    staged.update(overrides.pop("staged_deployments", {}))
    return {
        "schema_version": "session-start-projection/v1",
        "sections": {
            "control_plane": cp,
            "pending_truth": {"total": 3, "open": 2, "by_status": {}},
            "operational_guide": og,
            "adr_partials": {"total": 2},
            "staged_deployments": staged,
        },
    }


def _run(root: Path, payload: dict) -> subprocess.CompletedProcess[str]:
    pj = root / "projection.json"
    pj.write_text(json.dumps(payload))
    return subprocess.run(
        [sys.executable, str(GATE), "--project-dir", str(root), "--projection", str(pj), "--json"],
        capture_output=True, text=True, timeout=60, check=False,
    )


def _codes(cp: subprocess.CompletedProcess[str]) -> list[str]:
    return [f["code"] for f in json.loads(cp.stdout)["findings"]]


def test_coherent_projection_passes(tmp_path: Path) -> None:
    _seed_sources(tmp_path)
    cp = _run(tmp_path, _projection())
    assert cp.returncode == 0, cp.stdout + cp.stderr
    assert _codes(cp) == []


def test_row_count_wearing_findings_label_is_caught(tmp_path: Path) -> None:
    """The exact regression: open_findings set to the event-row count."""
    _seed_sources(tmp_path)
    cp = _run(tmp_path, _projection(control_plane={"open_findings": 40}))
    assert cp.returncode == 1, cp.stdout
    assert "order-of-magnitude" in _codes(cp)


def test_null_count_without_reason_is_caught(tmp_path: Path) -> None:
    _seed_sources(tmp_path)
    cp = _run(tmp_path, _projection(control_plane={
        "open_findings": None, "open_findings_known": False, "unknown_reason": None,
    }))
    assert cp.returncode == 1, cp.stdout
    assert "silent-null" in _codes(cp)


def test_null_count_with_reason_is_accepted(tmp_path: Path) -> None:
    """'I cannot count the open ones' is a valid answer when it says why."""
    _seed_sources(tmp_path)
    cp = _run(tmp_path, _projection(control_plane={
        "open_findings": None, "open_findings_known": False, "unknown_reason": "state machine absent",
    }))
    assert cp.returncode == 0, cp.stdout
    assert _codes(cp) == []


def test_false_zero_over_missing_priority_field_is_caught(tmp_path: Path) -> None:
    _seed_sources(tmp_path)
    cp = _run(tmp_path, _projection(operational_guide={
        "total_p0": 0, "total_p1": 0, "priorities_known": True, "unknown_reason": None,
    }))
    assert cp.returncode == 1, cp.stdout
    assert "false-zero" in _codes(cp)


def test_staged_dir_count_must_match_disk(tmp_path: Path) -> None:
    _seed_sources(tmp_path)
    cp = _run(tmp_path, _projection(staged_deployments={"dirs": ["a", "b", "c"]}))
    assert cp.returncode == 1, cp.stdout
    assert "mismatch" in _codes(cp)
