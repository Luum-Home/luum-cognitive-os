from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path

import yaml

from scripts import cos_demotion_loop_audit

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "cos-demotion-loop-audit"


def write_manifest(path: Path, primitives: list[dict]) -> Path:
    manifest = path / "primitive-lifecycle.yaml"
    manifest.write_text(yaml.safe_dump({"primitives": primitives}, sort_keys=False), encoding="utf-8")
    return manifest


def demoted(pid: str, *, primary_signal: str = "semantic-portability", demoted_on: str = "2026-05-03") -> dict:
    return {
        "id": pid,
        "lifecycle_state": "demoted",
        "demotion_evidence": {
            "demoted_on": demoted_on,
            "primary_signal": primary_signal,
            "reason": "test demotion",
            "control_plane_commands": ["scripts/cos-governance-roi --json"] if primary_signal == "governance-roi" else [],
        },
    }


def test_current_repo_reports_known_demotion_loop_gap_without_failing() -> None:
    proc = subprocess.run(
        [str(SCRIPT), "--json"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = yaml.safe_load(proc.stdout)
    assert report["demotion_count"] >= 1
    assert report["status"] in {"pass", "warn"}


def test_single_non_roi_demotion_warns(tmp_path: Path) -> None:
    manifest = write_manifest(tmp_path, [demoted("hooks/task-completed.sh")])
    report = cos_demotion_loop_audit.build_report(manifest)
    assert report["status"] == "warn"
    assert {finding["id"] for finding in report["findings"]} == {
        "second-demotion-missing",
        "roi-signed-demotion-missing",
    }


def test_second_demotion_with_roi_signature_passes(tmp_path: Path) -> None:
    manifest = write_manifest(
        tmp_path,
        [
            demoted("hooks/task-completed.sh"),
            demoted("hooks/noisy-meta-hook.sh", primary_signal="governance-roi"),
        ],
    )
    report = cos_demotion_loop_audit.build_report(manifest)
    assert report["status"] == "pass"
    assert report["demotion_count"] == 2
    assert report["roi_signed_demotion_count"] == 1


def test_roi_warning_expires_after_budget_when_second_demotion_ages(tmp_path: Path) -> None:
    manifest = write_manifest(
        tmp_path,
        [
            demoted("hooks/task-completed.sh", demoted_on="2026-05-03"),
            demoted("hooks/context-watchdog.sh", primary_signal="manifest-tier-claim-audit", demoted_on="2026-05-03"),
        ],
    )
    report = cos_demotion_loop_audit.build_report(manifest, today=date(2026, 6, 2))
    assert report["status"] == "fail"
    assert report["roi_warning_budget_days"] == 30
    assert report["roi_warning_age_days"] == 30
    assert {finding["id"]: finding["severity"] for finding in report["findings"]} == {
        "roi-signed-demotion-missing": "fail",
    }


def test_roi_warning_stays_warn_before_budget_expires(tmp_path: Path) -> None:
    manifest = write_manifest(
        tmp_path,
        [
            demoted("hooks/task-completed.sh", demoted_on="2026-05-03"),
            demoted("hooks/context-watchdog.sh", primary_signal="manifest-tier-claim-audit", demoted_on="2026-05-03"),
        ],
    )
    report = cos_demotion_loop_audit.build_report(manifest, today=date(2026, 6, 1))
    assert report["status"] == "warn"
    assert report["roi_warning_age_days"] == 29
