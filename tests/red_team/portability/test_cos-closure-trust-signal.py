# SCOPE: os-only
"""Portability probes for scripts/cos-closure-trust-signal.py (ADR-275 §10 P3).

Bilateral: reads ledger + closure-trail, computes signal correctly across bands.

Falsification:
  1. No ledger -> error, exit 2
  2. No closure-trail + N done items -> all unaudited, signal ZERO
  3. All done items have closure entries -> signal HIGH (>= 90%)
  4. dry_run entries in trail -> NOT counted as audited
  5. --strict on LOW -> exit 2
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "scripts" / "cos-closure-trust-signal.py"


def _run(project_dir: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("COGNITIVE_OS_PROJECT_DIR", None)
    env.pop("CODEX_PROJECT_DIR", None)
    env.pop("CLAUDE_PROJECT_DIR", None)
    cmd = [sys.executable, str(SCRIPT), "--project-dir", str(project_dir), *extra]
    return subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=10)


def _seed_ledger(project_dir: Path, items: list[dict]) -> None:
    reports = project_dir / "docs" / "06-Daily" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "pending-truth-latest.json").write_text(json.dumps({
        "schema_version": "pending-truth/v1",
        "generated_at": "2026-05-12T00:00:00Z",
        "items": items,
        "summary": {},
    }))


def _seed_trail(project_dir: Path, entries: list[dict]) -> None:
    audit = project_dir / ".cognitive-os" / "audit"
    audit.mkdir(parents=True, exist_ok=True)
    with (audit / "closure-trail.jsonl").open("w", encoding="utf-8") as fh:
        for e in entries:
            fh.write(json.dumps(e) + "\n")


def test_falsification_no_ledger_exits_2(tmp_path: Path) -> None:
    cp = _run(tmp_path)
    assert cp.returncode == 2
    out = json.loads(cp.stdout)
    assert "error" in out


def test_zero_closures_yields_zero(tmp_path: Path) -> None:
    """No verified-done items at all -> ZERO signal (empty trust)."""
    _seed_ledger(tmp_path, [{"id": "x", "status": "verified-pending"}])
    cp = _run(tmp_path)
    assert cp.returncode == 0
    out = json.loads(cp.stdout)
    assert out["total_verified_done"] == 0
    assert out["trust_signal"] == "ZERO"


def test_bilateral_all_audited_yields_high(tmp_path: Path) -> None:
    """All done items have trail entries -> HIGH signal."""
    _seed_ledger(tmp_path, [
        {"id": f"d{i}", "status": "verified-done"} for i in range(10)
    ])
    _seed_trail(tmp_path, [
        {"id": f"d{i}", "schema_version": "closure-trail/v1", "dry_run": False}
        for i in range(10)
    ])
    cp = _run(tmp_path)
    assert cp.returncode == 0
    out = json.loads(cp.stdout)
    assert out["audited_closures"] == 10
    assert out["unaudited_closures"] == 0
    assert out["audit_coverage_pct"] == 100.0
    assert out["trust_signal"] == "HIGH"


def test_falsification_dry_run_not_counted(tmp_path: Path) -> None:
    """dry_run entries must NOT count as audited."""
    _seed_ledger(tmp_path, [{"id": "d1", "status": "verified-done"}])
    _seed_trail(tmp_path, [
        {"id": "d1", "schema_version": "closure-trail/v1", "dry_run": True},
    ])
    cp = _run(tmp_path)
    out = json.loads(cp.stdout)
    assert out["audited_closures"] == 0
    assert out["unaudited_closures"] == 1


def test_bilateral_partial_yields_medium(tmp_path: Path) -> None:
    """8/10 audited -> 80% -> MEDIUM band (70-90)."""
    _seed_ledger(tmp_path, [
        {"id": f"d{i}", "status": "verified-done"} for i in range(10)
    ])
    _seed_trail(tmp_path, [
        {"id": f"d{i}", "schema_version": "closure-trail/v1", "dry_run": False}
        for i in range(8)
    ])
    cp = _run(tmp_path)
    out = json.loads(cp.stdout)
    assert out["audit_coverage_pct"] == 80.0
    assert out["trust_signal"] == "MEDIUM"


def test_falsification_strict_blocks_on_low(tmp_path: Path) -> None:
    _seed_ledger(tmp_path, [
        {"id": f"d{i}", "status": "verified-done"} for i in range(10)
    ])
    # No trail entries at all -> 0% -> ZERO
    cp = _run(tmp_path, "--strict")
    assert cp.returncode == 2


def test_strict_passes_on_high(tmp_path: Path) -> None:
    _seed_ledger(tmp_path, [{"id": "d1", "status": "verified-done"}])
    _seed_trail(tmp_path, [
        {"id": "d1", "schema_version": "closure-trail/v1", "dry_run": False}
    ])
    cp = _run(tmp_path, "--strict")
    assert cp.returncode == 0


def test_tracked_baseline_counts_as_audited(tmp_path: Path) -> None:
    """Tracked baseline records pre-ADR-275 manual closures without committing runtime trail."""
    _seed_ledger(tmp_path, [{"id": "d1", "status": "verified-done"}])
    reports = tmp_path / "docs" / "06-Daily" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "closure-trust-baseline.json").write_text(json.dumps({
        "schema_version": "closure-trust-baseline/v1",
        "audited_closures": [{"id": "d1", "reason": "retroactive"}],
    }))
    cp = _run(tmp_path)
    assert cp.returncode == 0
    out = json.loads(cp.stdout)
    assert out["audited_closures"] == 1
    assert out["unaudited_closures"] == 0
    assert out["trust_signal"] == "HIGH"
