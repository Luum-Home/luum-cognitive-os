#!/usr/bin/env python3
# SCOPE: both
"""Generate proposed doctrine amendments from control-plane evidence.

ADR-180: every run emits one event to
``.cognitive-os/metrics/doctrine-proposals.jsonl`` with input_signals from
SkillStore, dogfood-score, drift detectors, and aspirational-audit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import cos_boring_reliability
import cos_claim_signature_audit
from lib.doctrine_proposer import build_doctrine_proposals, build_report, write_markdown
from lib.self_improvement_loop import build_self_improvement_plan


def _safe_boring_dashboard(project_root: Path, profile: str) -> dict:
    try:
        return cos_boring_reliability.build_dashboard(profile, project_root)
    except Exception as exc:  # noqa: BLE001
        return {"status": "warn", "dashboard_error": str(exc)}


def _skillstore_signal(project_root: Path) -> dict | None:
    """Return a small, hashable summary of SkillStore state, or None if absent.

    ADR-180 input signal: skillstore.
    """
    db_path = project_root / ".cognitive-os" / "skill-store.db"
    if not db_path.exists():
        return None
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        rows = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(total_completions), 0), COALESCE(SUM(total_applied), 0) FROM skill_records"
        ).fetchone()
        conn.close()
    except sqlite3.Error as exc:  # noqa: BLE001
        return {"error": str(exc)}
    skill_count, completions, applied = rows or (0, 0, 0)
    digest = hashlib.sha256(f"{skill_count}:{completions}:{applied}".encode()).hexdigest()[:16]
    return {
        "skill_count": int(skill_count or 0),
        "completions": int(completions or 0),
        "applied": int(applied or 0),
        "digest": digest,
    }


def _dogfood_signal(project_root: Path) -> dict | None:
    """Return latest dogfood score summary, or None.

    ADR-180 input signal: dogfood.
    """
    candidates = [
        project_root / ".cognitive-os" / "metrics" / "dogfood-score-latest.json",
        project_root / ".cognitive-os" / "dogfood-score-latest.json",
    ]
    for path in candidates:
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return {
                    "score": data.get("score") or data.get("overall"),
                    "skill_coverage": data.get("skill_coverage"),
                    "source": str(path),
                }
            except (OSError, json.JSONDecodeError):
                continue
    return None


def _drift_signal(project_root: Path) -> dict | None:
    """Return latest drift detector summary, or None.

    ADR-180 input signal: drift.
    """
    metrics_dir = project_root / ".cognitive-os" / "metrics"
    candidates = [
        metrics_dir / "profile-drift.jsonl",
        metrics_dir / "docker-drift.jsonl",
    ]
    summary: dict = {}
    for p in candidates:
        if p.exists():
            try:
                with p.open("r", encoding="utf-8") as fh:
                    last = None
                    for line in fh:
                        if line.strip():
                            last = line
                    if last:
                        summary[p.name] = json.loads(last).get("status") or "unknown"
            except (OSError, json.JSONDecodeError):
                summary[p.name] = "parse_error"
    return summary or None


def _aspirational_signal(project_root: Path) -> dict | None:
    """Return latest aspirational-audit summary, or None.

    ADR-180 input signal: aspirational.
    """
    candidates = [
        project_root / ".cognitive-os" / "metrics" / "aspirational-audit-latest.json",
        project_root / ".cognitive-os" / "aspirational-audit-latest.json",
    ]
    for path in candidates:
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return {
                    "ratio": data.get("dormant_aspirational_ratio") or data.get("ratio"),
                    "source": str(path),
                }
            except (OSError, json.JSONDecodeError):
                continue
    return None


def _emit_metrics_event(
    project_root: Path,
    profile: str,
    proposals_written: int,
    written_to: str | None,
) -> Path:
    """Append one heartbeat event to doctrine-proposals.jsonl. ADR-180."""
    metrics_path = project_root / ".cognitive-os" / "metrics" / "doctrine-proposals.jsonl"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "kind": "doctrine-proposer-run",
        "profile": profile,
        "proposals_written": proposals_written,
        "written_to": written_to,
        "input_signals": {
            "skillstore": _skillstore_signal(project_root),
            "dogfood": _dogfood_signal(project_root),
            "drift": _drift_signal(project_root),
            "aspirational": _aspirational_signal(project_root),
        },
    }
    with metrics_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, sort_keys=True) + "\n")
    return metrics_path


def _self_improvement_plan(project_root: Path, profile: str) -> dict:
    boring = _safe_boring_dashboard(project_root, profile)
    claim_signature = cos_claim_signature_audit.build_report(
        project_root / "manifests" / "primitive-lifecycle.yaml",
        project_root / "manifests" / "external-adoption-evidence.yaml",
    )
    return build_self_improvement_plan(
        boring_reliability=boring,
        claim_signature=claim_signature,
        profile=profile,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--profile", choices=["core", "team", "maintainer", "lab"], default="core")
    parser.add_argument("--write", action="store_true", help="write markdown proposal under docs/proposals")
    parser.add_argument("--json", action="store_true", help="accepted for CLI consistency; output is always JSON")
    args = parser.parse_args(argv)

    project_root = args.project_dir.resolve()
    boring = _safe_boring_dashboard(project_root, args.profile)
    plan = _self_improvement_plan(project_root, args.profile)
    report = build_report(
        project_root=project_root,
        boring_reliability=boring,
        self_improvement_plan=plan,
    )
    written_to: str | None = None
    proposals_written = 0
    if args.write:
        proposals = build_doctrine_proposals(
            project_root=project_root,
            boring_reliability=boring,
            self_improvement_plan=plan,
        )
        written_to = str(write_markdown(project_root, proposals))
        report["written_to"] = written_to
        proposals_written = len(proposals) if isinstance(proposals, (list, tuple)) else 1

    # ADR-180: always emit one heartbeat event with input_signals.
    metrics_path = _emit_metrics_event(project_root, args.profile, proposals_written, written_to)
    report["metrics_path"] = str(metrics_path)

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
