# SCOPE: os-only
"""Portability probes for scripts/cos-pending-truth-close (ADR-275).

Bilateral assertion: close primitive verifies the proof, applies the
canonical closure edit to the original source, and records the closure
in the audit trail.

Falsification probes:
  1. Unknown item id -> exit 2
  2. Path-proof to non-existent file -> exit 3
  3. ADR-ref proof to non-accepted ADR -> exit 3
  4. --dry-run does NOT mutate source nor audit trail
  5. Successful plan-checkbox closure flips [ ] -> [x] with (verified: ...)
  6. Closure trail entry has all required fields

ADR reference: ADR-275 §2 close primitive contract.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "cos-pending-truth-close"


def _run(project_dir: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("COGNITIVE_OS_PROJECT_DIR", None)
    env.pop("CODEX_PROJECT_DIR", None)
    env.pop("CLAUDE_PROJECT_DIR", None)
    cmd = [sys.executable, str(SCRIPT), "--project-dir", str(project_dir), *args]
    return subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=15)


def _seed_ledger(project_dir: Path, items: list[dict]) -> None:
    reports = project_dir / "docs" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "pending-truth-latest.json").write_text(json.dumps({
        "schema_version": "pending-truth/v1",
        "generated_at": "2026-05-12T00:00:00Z",
        "summary": {"total_items": len(items), "by_status": {}, "by_type": {}},
        "items": items,
    }))


def _seed_plan(project_dir: Path, rel: str, lines: list[str]) -> Path:
    target = project_dir / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def test_falsification_unknown_id_exits_2(tmp_path: Path) -> None:
    _seed_ledger(tmp_path, [])
    cp = _run(tmp_path, "--id", "nonexistent", "--proof", "docs/02-Decisions/adrs/ADR-001-x.md")
    assert cp.returncode == 2, f"expected 2, got {cp.returncode}; stderr={cp.stderr}"
    assert "not found" in cp.stderr.lower()


def test_falsification_missing_path_proof_exits_3(tmp_path: Path) -> None:
    _seed_ledger(tmp_path, [
        {"id": "x", "type": "plan-checkbox", "source": "plans/p.md:L1",
         "status": "verified-pending", "evidence": [], "next_action": "", "owner_adr": None},
    ])
    cp = _run(tmp_path, "--id", "x", "--proof", "lib/never-existed.py:42")
    assert cp.returncode == 3, f"expected 3, got {cp.returncode}; stderr={cp.stderr}"


def test_falsification_adr_ref_must_be_accepted(tmp_path: Path) -> None:
    """ADR-ref proof where the ADR is status: proposed -> rejected."""
    _seed_ledger(tmp_path, [
        {"id": "x", "type": "plan-checkbox", "source": "plans/p.md:L1",
         "status": "verified-pending", "evidence": [], "next_action": "", "owner_adr": None},
    ])
    adr_dir = tmp_path / "docs" / "02-Decisions" / "adrs"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-999-pending.md").write_text("---\nadr: 999\nstatus: proposed\n---\n")
    cp = _run(tmp_path, "--id", "x", "--proof", "ADR-999")
    assert cp.returncode == 3, f"expected 3 (proof reject), got {cp.returncode}; stderr={cp.stderr}"


def test_bilateral_plan_checkbox_closure(tmp_path: Path) -> None:
    """Bilateral: ledger + plan file -> close flips [ ] -> [x] and writes audit trail."""
    _seed_plan(tmp_path, "plans/p.md", [
        "# Plan",
        "",
        "- [ ] Build the thing",
        "- [ ] Other thing",
    ])
    _seed_ledger(tmp_path, [
        {"id": "build-thing", "type": "plan-checkbox", "source": "plans/p.md:L3",
         "status": "verified-pending", "evidence": [], "next_action": "build", "owner_adr": None},
    ])
    cp = _run(tmp_path, "--id", "build-thing", "--proof", "plans/p.md:L1",
              "--reason", "smoke", "--skip-refresh")
    assert cp.returncode == 0, f"stderr={cp.stderr}\nstdout={cp.stdout}"

    plan = (tmp_path / "plans" / "p.md").read_text()
    assert "- [x] Build the thing" in plan, f"checkbox not flipped: {plan!r}"
    assert "(verified:" in plan

    trail = tmp_path / ".cognitive-os" / "audit" / "closure-trail.jsonl"
    assert trail.exists(), "closure trail not written"
    entries = [json.loads(line) for line in trail.read_text().splitlines() if line]
    assert len(entries) == 1
    entry = entries[0]
    assert entry["id"] == "build-thing"
    assert entry["proof"] == "plans/p.md:L1"
    assert entry["reason"] == "smoke"
    assert entry["item_type"] == "plan-checkbox"
    assert entry["schema_version"] == "closure-trail/v1"
    assert entry["dry_run"] is False


def test_falsification_dry_run_does_not_mutate(tmp_path: Path) -> None:
    """--dry-run shows what would change but does not touch source or trail."""
    _seed_plan(tmp_path, "plans/p.md", ["- [ ] Item"])
    _seed_ledger(tmp_path, [
        {"id": "item", "type": "plan-checkbox", "source": "plans/p.md:L1",
         "status": "verified-pending", "evidence": [], "next_action": "", "owner_adr": None},
    ])
    cp = _run(tmp_path, "--id", "item", "--proof", "plans/p.md:L1", "--dry-run")
    assert cp.returncode == 0, cp.stderr
    plan = (tmp_path / "plans" / "p.md").read_text()
    assert "- [ ] Item" in plan, "dry-run should not modify source"
    assert "- [x]" not in plan
    assert not (tmp_path / ".cognitive-os" / "audit" / "closure-trail.jsonl").exists()


def test_bilateral_already_checked_box_rejected(tmp_path: Path) -> None:
    """A closure cannot re-close an already-checked box."""
    _seed_plan(tmp_path, "plans/p.md", ["- [x] Already done"])
    _seed_ledger(tmp_path, [
        {"id": "done", "type": "plan-checkbox", "source": "plans/p.md:L1",
         "status": "verified-pending", "evidence": [], "next_action": "", "owner_adr": None},
    ])
    cp = _run(tmp_path, "--id", "done", "--proof", "plans/p.md:L1", "--skip-refresh")
    assert cp.returncode == 4, f"expected 4, got {cp.returncode}; stderr={cp.stderr}"


def test_bilateral_adr_status_flip(tmp_path: Path) -> None:
    """adr-slice item -> implementation_status flips to implemented."""
    adr_dir = tmp_path / "docs" / "02-Decisions" / "adrs"
    adr_dir.mkdir(parents=True)
    adr_file = adr_dir / "ADR-100-x.md"
    adr_file.write_text(
        "---\nadr: 100\nstatus: accepted\nimplementation_status: partial\n---\n# X\n",
        encoding="utf-8",
    )
    _seed_ledger(tmp_path, [
        {"id": "adr-100", "type": "adr-slice", "source": "docs/02-Decisions/adrs/ADR-100-x.md",
         "status": "verified-pending", "evidence": [], "next_action": "", "owner_adr": "ADR-100"},
    ])
    cp = _run(tmp_path, "--id", "adr-100", "--proof", "ADR-100", "--skip-refresh")
    assert cp.returncode == 0, f"stderr={cp.stderr}"
    content = adr_file.read_text()
    assert "implementation_status: implemented" in content
