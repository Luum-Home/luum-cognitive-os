# SCOPE: both
"""Portability probes for scripts/cos-operational-guide-audit.py (ADR-274).

Bilateral assertion: audit reads synthetic ADRs, classifies each by the
ADR-274 §1 contract (subject_to_contract) and §2 minimum structure
(>=3 of 5 sub-sections), and emits the expected verdict + priority.

Falsification probes:
  1. Maintainer + accepted + impl_files + no §Operational Guide -> missing/P0 or P1
  2. Maintainer + accepted + §Operational Guide with 2 sub-sections -> partial
  3. Maintainer + accepted + §Operational Guide with 3 sub-sections -> compliant
  4. Tier=project -> not-applicable
  5. Status=tombstone -> not-applicable
  6. Status=superseded -> not-applicable
  7. Maintainer + accepted but no implementation_files -> not-applicable
  8. <!-- adr-274-exempt: --> marker -> exempt
  9. --strict with P0 items -> exit 2

ADR reference: ADR-274 §3-4 audit + gate contract.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "cos-operational-guide-audit.py"

TODAY = "2026-05-12"


def _write_adr(
    project_dir: Path,
    num: int,
    slug: str,
    *,
    tier: str | None = "maintainer",
    status: str = "accepted",
    date: str = TODAY,
    impl_files: list[str] | None = None,
    operational_guide_subs: list[str] | None = None,
    exempt: bool = False,
    is_tombstone: bool = False,
) -> Path:
    adr_dir = project_dir / "docs" / "adrs"
    adr_dir.mkdir(parents=True, exist_ok=True)
    name = f"ADR-{num:03d}-{slug}"
    if is_tombstone:
        name += "-tombstone"
    path = adr_dir / f"{name}.md"

    front = ["---", f"adr: {num}", f"title: Test ADR {num}", f"status: {status}", f"date: {date}"]
    if tier:
        front.append(f"tier: {tier}")
    if impl_files:
        front.append("implementation_files:")
        for f in impl_files:
            front.append(f"  - {f}")
    front.append("---")

    body = [f"# ADR-{num}: Test"]
    body.append("## Status\nAccepted.")
    body.append("## Context\nstub")
    body.append("## Decision\nstub")
    body.append("## Consequences\nstub")
    body.append("## Alternatives rejected\nstub")
    body.append("## Verification\nstub")

    if exempt:
        body.append("<!-- adr-274-exempt: pure architectural decision -->")

    if operational_guide_subs is not None:
        body.append("## Operational Guide")
        for sub in operational_guide_subs:
            body.append(f"### {sub}\nbody")

    path.write_text("\n".join(front) + "\n" + "\n\n".join(body) + "\n", encoding="utf-8")
    return path


def _run(project_dir: Path, *extra: str) -> tuple[subprocess.CompletedProcess[str], dict]:
    env = os.environ.copy()
    env.pop("COGNITIVE_OS_PROJECT_DIR", None)
    env.pop("CODEX_PROJECT_DIR", None)
    env.pop("CLAUDE_PROJECT_DIR", None)
    cmd = [sys.executable, str(SCRIPT), "--project-dir", str(project_dir), "--write", *extra]
    cp = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=30)
    json_path = project_dir / "docs" / "reports" / "operational-guide-audit-latest.json"
    payload = json.loads(json_path.read_text()) if json_path.exists() else {}
    return cp, payload


def _by_adr(payload: dict) -> dict[str, dict]:
    return {r["adr"]: r for r in payload.get("results", [])}


def test_bilateral_audit_classifies_all_verdicts(tmp_path: Path) -> None:
    """Bilateral: 6 seeded ADRs, each demonstrating a different verdict."""
    _write_adr(tmp_path, 100, "no-guide",
               impl_files=["lib/a.py"], operational_guide_subs=None)
    _write_adr(tmp_path, 101, "partial-guide",
               impl_files=["lib/b.py"],
               operational_guide_subs=["What changes for the operator", "Daily operational pattern"])
    _write_adr(tmp_path, 102, "compliant",
               impl_files=["lib/c.py"],
               operational_guide_subs=[
                   "What changes for the operator",
                   "Daily operational pattern",
                   "Reading guide for cold readers",
               ])
    _write_adr(tmp_path, 103, "tombstone-na",
               impl_files=["lib/d.py"], is_tombstone=True,
               operational_guide_subs=None)
    _write_adr(tmp_path, 104, "exempt",
               impl_files=["lib/e.py"], exempt=True,
               operational_guide_subs=None)
    _write_adr(tmp_path, 105, "no-impl",
               impl_files=None, operational_guide_subs=None)

    cp, payload = _run(tmp_path)
    assert cp.returncode == 0, f"stderr={cp.stderr}"
    by = _by_adr(payload)

    assert by["ADR-100-no-guide"]["verdict"] == "missing"
    assert by["ADR-101-partial-guide"]["verdict"] == "partial"
    assert by["ADR-102-compliant"]["verdict"] == "compliant"
    assert by["ADR-103-tombstone-na-tombstone"]["verdict"] == "not-applicable"
    assert by["ADR-104-exempt"]["verdict"] == "exempt"
    assert by["ADR-105-no-impl"]["verdict"] == "not-applicable"


def test_falsification_project_tier_is_not_applicable(tmp_path: Path) -> None:
    _write_adr(tmp_path, 110, "project-tier", tier="project",
               impl_files=["lib/a.py"], operational_guide_subs=None)
    _, payload = _run(tmp_path)
    assert _by_adr(payload)["ADR-110-project-tier"]["verdict"] == "not-applicable"


def test_falsification_superseded_is_not_applicable(tmp_path: Path) -> None:
    _write_adr(tmp_path, 111, "superseded", status="superseded",
               impl_files=["lib/a.py"], operational_guide_subs=None)
    _, payload = _run(tmp_path)
    assert _by_adr(payload)["ADR-111-superseded"]["verdict"] == "not-applicable"


def test_priority_p0_for_recent_missing(tmp_path: Path) -> None:
    """ADR accepted today (age 0) and missing -> P0."""
    _write_adr(tmp_path, 120, "recent-missing", impl_files=["lib/x.py"],
               operational_guide_subs=None, date=TODAY)
    _, payload = _run(tmp_path)
    rec = _by_adr(payload)["ADR-120-recent-missing"]
    assert rec["verdict"] == "missing"
    assert rec["priority"] == "P0"


def test_priority_p1_for_older_missing(tmp_path: Path) -> None:
    """Older maintainer-accepted ADR missing guide -> P1, not P0."""
    _write_adr(tmp_path, 121, "old-missing", impl_files=["lib/x.py"],
               operational_guide_subs=None, date="2025-01-01")
    _, payload = _run(tmp_path)
    rec = _by_adr(payload)["ADR-121-old-missing"]
    assert rec["verdict"] == "missing"
    assert rec["priority"] == "P1"


def test_strict_mode_exits_2_when_p0_present(tmp_path: Path) -> None:
    _write_adr(tmp_path, 130, "recent-missing", impl_files=["lib/x.py"],
               operational_guide_subs=None, date=TODAY)
    cp, _ = _run(tmp_path, "--strict")
    assert cp.returncode == 2, f"expected exit 2, got {cp.returncode}; stderr={cp.stderr}"


def test_strict_mode_exits_0_when_compliant(tmp_path: Path) -> None:
    _write_adr(tmp_path, 131, "compliant", impl_files=["lib/y.py"],
               operational_guide_subs=[
                   "What changes for the operator",
                   "Daily operational pattern",
                   "Reading guide for cold readers",
               ])
    cp, _ = _run(tmp_path, "--strict")
    assert cp.returncode == 0, f"stderr={cp.stderr}"


def test_summary_counts_match_results(tmp_path: Path) -> None:
    """Bilateral: summary.by_verdict totals == count of results per verdict."""
    _write_adr(tmp_path, 140, "a", impl_files=["lib/a.py"], operational_guide_subs=None)
    _write_adr(tmp_path, 141, "b", impl_files=["lib/b.py"], operational_guide_subs=None)
    _write_adr(tmp_path, 142, "c", tier="project", operational_guide_subs=None)
    _, payload = _run(tmp_path)
    counts: dict[str, int] = {}
    for r in payload["results"]:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    assert counts == payload["summary"]["by_verdict"]
    assert payload["summary"]["total_adrs"] == len(payload["results"])
