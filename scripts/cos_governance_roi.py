#!/usr/bin/env python3
# SCOPE: os-only
"""Governance ROI/friction dashboard for Cognitive OS.

This is intentionally heuristic. It does not claim exact productivity, but it
turns governance overhead and benefit signals into a stable JSON report so the
SO can decide whether governance is paying for itself.
"""
from __future__ import annotations

import argparse
import json
import sys
import math
import os
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.time_utils import parse_ts
from typing import Any, Iterable

DEFAULT_WINDOW_HOURS = 24
# Conservative estimates; callers can override later via config/env once the
# metric is calibrated against real sessions.
MINUTES_PER_BLOCKED_INCIDENT = 5.0
MINUTES_PER_WIP_RESTORE = 30.0
MINUTES_PER_FALSE_POSITIVE_CANDIDATE = 5.0

GOVERNANCE_CATCH_LEDGER = Path(".cognitive-os") / "metrics" / "governance-catches.jsonl"

CONFIRMED_VALID_BLOCK_VALUES = {
    "confirmed-valid-block",
    "confirmed_valid_block",
    "valid-block",
    "valid_block",
    "true_positive",
    "correct_block",
}
FALSE_POSITIVE_VALUES = {
    "false-positive",
    "false_positive",
    "false-positive-override",
    "false_positive_override",
    "override_false_positive",
}
SILENT_LOSS_VALUES = {
    "silent-loss-prevented",
    "silent_loss_prevented",
    "work-loss-prevented",
    "work_loss_prevented",
}
HIGH_BLAST_RADIUS_VALUES = {
    "high-blast-radius-catch",
    "high_blast_radius_catch",
    "high-risk-catch",
    "high_risk_catch",
}

PHASE_POLICIES: dict[str, dict[str, Any]] = {
    "reconstruction": {
        "strictness": "minimal-blocking",
        "block": ["destructive-git", "secret-write", "credential-leak", "work-loss"],
        "advisory": ["style", "process", "low-risk-structure"],
    },
    "stabilization": {
        "strictness": "contract-focused",
        "block": ["contracts", "tests", "primitive-drift", "runtime-state-loss"],
        "advisory": ["style", "low-signal-process"],
    },
    "production": {
        "strictness": "strict-release",
        "block": ["release", "security", "migration", "public-claim", "config-protection"],
        "advisory": ["low-risk-exploration"],
    },
    "maintenance": {
        "strictness": "regression-focused",
        "block": ["regressions", "security", "unsafe-change", "data-loss"],
        "advisory": ["new-surface-expansion"],
    },
}


def project_dir(raw: str | None = None) -> Path:
    value = raw or os.environ.get("COGNITIVE_OS_PROJECT_DIR") or os.environ.get("CODEX_PROJECT_DIR") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return Path(value).expanduser().resolve()


def iter_jsonl(path: Path, *, since_epoch: float | None = None) -> Iterable[dict[str, Any]]:
    if not path.is_file():
        return
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return
    for line in lines:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        if since_epoch is not None:
            ts = parse_ts(row.get("timestamp") or row.get("ts") or row.get("created_at"))
            if ts is not None and ts < since_epoch:
                continue
        yield row


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    if len(values) == 1:
        return values[0]
    rank = (len(values) - 1) * p
    lo = math.floor(rank)
    hi = math.ceil(rank)
    if lo == hi:
        return values[lo]
    return values[lo] + (values[hi] - values[lo]) * (rank - lo)


def collect_hook_metrics(root: Path, since_epoch: float | None) -> dict[str, Any]:
    rows = list(iter_jsonl(root / ".cognitive-os" / "metrics" / "hook-timing.jsonl", since_epoch=since_epoch) or [])
    by_hook: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        hook = str(row.get("hook") or row.get("name") or "unknown")
        by_hook.setdefault(hook, []).append(row)

    blocks = [r for r in rows if str(r.get("exit_code", "")) == "2" or str(r.get("execution_status", "")).lower() == "blocked"]
    errors = [r for r in rows if str(r.get("exit_code", "0")) not in {"0", "2", ""}]
    safe_mode = [r for r in rows if str(r.get("safe_mode", "0")) in {"1", "true", "True"}]
    killed = [r for r in rows if str(r.get("signal") or "")]
    body_ms = [float(r.get("body_duration_ms") or r.get("duration_ms") or 0) for r in rows]

    top_blocking = Counter(str(r.get("hook") or "unknown") for r in blocks).most_common(10)
    top_latency = []
    for hook, hook_rows in by_hook.items():
        vals = [float(r.get("body_duration_ms") or r.get("duration_ms") or 0) for r in hook_rows]
        top_latency.append({"hook": hook, "count": len(vals), "p95_body_ms": round(percentile(vals, 0.95), 2)})
    top_latency.sort(key=lambda item: item["p95_body_ms"], reverse=True)

    return {
        "invocations": len(rows),
        "blocking_events": len(blocks),
        "error_events": len(errors),
        "safe_mode_events": len(safe_mode),
        "killed_events": len(killed),
        "body_time_minutes": round(sum(body_ms) / 60000.0, 2),
        "top_blocking_hooks": [{"hook": h, "count": c} for h, c in top_blocking],
        "top_latency_hooks": top_latency[:10],
    }


def _normal_value(row: dict[str, Any]) -> str:
    """Return a normalized verdict/type/action token for catch-ledger rows."""
    raw = (
        row.get("verdict")
        or row.get("outcome")
        or row.get("type")
        or row.get("kind")
        or row.get("event")
        or row.get("status")
        or ""
    )
    return str(raw).strip().lower().replace(" ", "_")


def collect_catch_ledger(root: Path, since_epoch: float | None) -> dict[str, Any]:
    """Collect operator-reviewed governance catch outcomes.

    Ledger path:
        .cognitive-os/metrics/governance-catches.jsonl

    Minimal row examples:
        {"ts": "...", "hook": "dispatch-gate", "verdict": "confirmed_valid_block"}
        {"ts": "...", "hook": "edit-lock", "verdict": "false_positive_override"}
        {"ts": "...", "hook": "stash-safety", "verdict": "silent_loss_prevented"}

    The ledger is intentionally sparse: absence means "not reviewed yet", not
    "no value". It keeps the ROI dashboard from pretending every block was
    correct.
    """
    rows = list(iter_jsonl(root / GOVERNANCE_CATCH_LEDGER, since_epoch=since_epoch) or [])
    confirmed_valid_blocks = 0
    false_positive_overrides = 0
    silent_loss_prevented = 0
    high_blast_radius_catches = 0
    by_hook: Counter[str] = Counter()

    for row in rows:
        value = _normal_value(row)
        value_dash = value.replace("_", "-")
        hook = str(row.get("hook") or row.get("guard") or row.get("primitive") or "unknown")

        is_silent_loss = value in SILENT_LOSS_VALUES or value_dash in SILENT_LOSS_VALUES
        is_high_blast = value in HIGH_BLAST_RADIUS_VALUES or value_dash in HIGH_BLAST_RADIUS_VALUES
        is_confirmed = (
            value in CONFIRMED_VALID_BLOCK_VALUES
            or value_dash in CONFIRMED_VALID_BLOCK_VALUES
            or is_silent_loss
            or is_high_blast
        )
        is_false_positive = value in FALSE_POSITIVE_VALUES or value_dash in FALSE_POSITIVE_VALUES

        if is_confirmed:
            confirmed_valid_blocks += 1
            by_hook[hook] += 1
        if is_false_positive:
            false_positive_overrides += 1
        if is_silent_loss:
            silent_loss_prevented += 1
        if is_high_blast:
            high_blast_radius_catches += 1

    return {
        "ledger_path": str(GOVERNANCE_CATCH_LEDGER),
        "reviewed_events": len(rows),
        "confirmed_valid_blocks": confirmed_valid_blocks,
        "false_positive_overrides": false_positive_overrides,
        "silent_loss_prevented": silent_loss_prevented,
        "high_blast_radius_catches": high_blast_radius_catches,
        "top_confirmed_hooks": [{"hook": h, "count": c} for h, c in by_hook.most_common(10)],
    }


def friction_ratio_status(total_blocks: int, confirmed_valid_blocks: int) -> dict[str, Any]:
    """Return explicit friction-vs-catch ratio and recommendation band.

    Ratio definition:
        total guard blocks / operator-confirmed valid blocks

    Bands:
        <= 2x  -> paying
        <= 5x  -> watch/tune
        > 5x   -> cut/demote candidates
    """
    if confirmed_valid_blocks <= 0:
        return {
            "ratio": None,
            "status": "unknown",
            "threshold": "needs confirmed catch ledger entries",
            "recommendation": "record confirmed_valid_block or false_positive_override rows before judging guard ROI",
        }

    ratio = total_blocks / confirmed_valid_blocks
    if ratio <= 2.0:
        status = "paying"
        recommendation = "keep current blocking posture"
    elif ratio <= 5.0:
        status = "watch"
        recommendation = "review top blocking hooks and tune false positives"
    else:
        status = "cut"
        recommendation = "demote, relax, or make high-friction guards phase-aware"
    return {
        "ratio": round(ratio, 2),
        "status": status,
        "threshold": "<=2 paying, 2-5 watch, >5 cut",
        "recommendation": recommendation,
    }


def read_project_phase(root: Path) -> str:
    """Read project.phase from cognitive-os.yaml, fallback unknown."""
    config = root / "cognitive-os.yaml"
    if not config.is_file():
        return "unknown"
    try:
        import yaml

        data = yaml.safe_load(config.read_text(encoding="utf-8")) or {}
        phase = ((data.get("project") or {}).get("phase") or data.get("phase") or "unknown")
        return str(phase)
    except Exception:
        # Regex fallback keeps the command usable if PyYAML is unavailable.
        in_project = False
        for line in config.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("project:"):
                in_project = True
                continue
            if in_project and line and not line.startswith((" ", "\t")):
                in_project = False
            if in_project and line.strip().startswith("phase:"):
                return line.split(":", 1)[1].split("#", 1)[0].strip().strip("'\"")
    return "unknown"


def phase_policy_for(phase: str) -> dict[str, Any]:
    policy = PHASE_POLICIES.get(phase, {})
    return {
        "phase": phase,
        "strictness": policy.get("strictness", "unknown"),
        "block": policy.get("block", []),
        "advisory": policy.get("advisory", []),
    }


def collect_snapshot_benefits(root: Path, since_epoch: float | None) -> dict[str, Any]:
    rows = list(iter_jsonl(root / ".cognitive-os" / "metrics" / "agent-snapshots.jsonl", since_epoch=since_epoch) or [])
    restored = [r for r in rows if r.get("event") == "agent_snapshot_restore" and r.get("action") == "restored"]
    conflicts = [r for r in rows if r.get("event") == "agent_snapshot_restore" and r.get("action") == "conflict"]
    orphan_markers = list((root / ".cognitive-os" / "runtime").glob("pre-agent-snapshot-*.json")) if (root / ".cognitive-os" / "runtime").is_dir() else []
    auto_stashes = []
    try:
        import subprocess

        proc = subprocess.run(["git", "stash", "list"], cwd=root, text=True, capture_output=True, check=False, timeout=60)
        auto_stashes = [line for line in proc.stdout.splitlines() if "auto-pre-agent-" in line]
    except Exception:
        auto_stashes = []
    return {
        "snapshot_events": len(rows),
        "wip_restore_events": len(restored),
        "restore_conflicts": len(conflicts),
        "orphan_marker_count": len(orphan_markers),
        "auto_pre_agent_stash_count": len(auto_stashes),
    }


def collect_discovery(root: Path) -> dict[str, Any]:
    skills = sorted(p.parent.name for p in root.glob("skills/*/SKILL.md"))
    hook_files = sorted(p.name for p in (root / "hooks").glob("*.sh")) if (root / "hooks").is_dir() else []
    registered_hooks = 0
    try:
        import yaml

        cfg = yaml.safe_load((root / "cognitive-os.yaml").read_text(encoding="utf-8")) or {}
        hooks = ((cfg.get("harness") or {}).get("hooks") or {})
        registered_hooks = len(hooks) if isinstance(hooks, dict) else 0
    except Exception:
        registered_hooks = 0

    skill_usage = Counter()
    for row in iter_jsonl(root / ".cognitive-os" / "metrics" / "skill-usage.jsonl") or []:
        name = str(row.get("name") or row.get("skill") or "")
        if name:
            skill_usage[name] += 1
    zero_skill_count = len([s for s in skills if s not in skill_usage]) if skills else 0

    return {
        "skill_count": len(skills),
        "hook_file_count": len(hook_files),
        "registered_hook_count": registered_hooks,
        "zero_usage_skill_count": zero_skill_count,
        "top_skills": [{"skill": s, "count": c} for s, c in skill_usage.most_common(10)],
        "discovery_overload": len(skills) > 75 or registered_hooks > 75,
    }


def build_report(root: Path, window_hours: int) -> dict[str, Any]:
    since = time.time() - window_hours * 3600 if window_hours > 0 else None
    hooks = collect_hook_metrics(root, since)
    snapshots = collect_snapshot_benefits(root, since)
    discovery = collect_discovery(root)
    catches = collect_catch_ledger(root, since)
    friction_vs_catch = friction_ratio_status(
        hooks["blocking_events"],
        catches["confirmed_valid_blocks"],
    )
    phase_policy = phase_policy_for(read_project_phase(root))

    friction_minutes = hooks["body_time_minutes"] + hooks["blocking_events"] * 2.0
    false_positive_candidates = snapshots["orphan_marker_count"] + snapshots["auto_pre_agent_stash_count"]
    friction_minutes += false_positive_candidates * MINUTES_PER_FALSE_POSITIVE_CANDIDATE

    benefit_minutes = (
        hooks["blocking_events"] * MINUTES_PER_BLOCKED_INCIDENT
        + snapshots["wip_restore_events"] * MINUTES_PER_WIP_RESTORE
    )
    net = benefit_minutes - friction_minutes

    recommendations: list[str] = []
    if snapshots["orphan_marker_count"] or snapshots["auto_pre_agent_stash_count"]:
        recommendations.append("Run snapshot/stash repair; orphaned snapshot residue is governance friction, not value.")
    if hooks["blocking_events"] and not snapshots["wip_restore_events"]:
        recommendations.append("Review top blocking hooks for false positives before promoting more guards to block.")
    if discovery["discovery_overload"]:
        recommendations.append("Apply ADR-124 distribution tiers; active primitive discovery is too broad for default agents.")
    if net < 0:
        recommendations.append("Net governance ROI is negative in this window; demote/archive low-value primitives or switch to a leaner distribution.")
    if friction_vs_catch["status"] == "unknown" and hooks["blocking_events"]:
        recommendations.append("Record governance-catches.jsonl verdicts so friction-vs-catch ratio can distinguish correct blocks from false positives.")
    elif friction_vs_catch["status"] == "cut":
        recommendations.append("Friction-vs-catch ratio exceeds 5x; recut high-friction guards or make them advisory outside high-risk phases.")
    if phase_policy["phase"] == "reconstruction" and hooks["blocking_events"]:
        recommendations.append("Reconstruction phase should block mainly destructive/security/work-loss risks; demote low-risk process guards to advisory.")

    return {
        "project": str(root),
        "window_hours": window_hours,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "friction": hooks,
        "benefits": snapshots,
        "catch_ledger": catches,
        "friction_vs_catch": friction_vs_catch,
        "phase_policy": phase_policy,
        "discovery": discovery,
        "roi": {
            "benefit_minutes_estimate": round(benefit_minutes, 2),
            "friction_minutes_estimate": round(friction_minutes, 2),
            "net_minutes_estimate": round(net, 2),
            "status": "positive" if net >= 0 else "negative",
            "heuristic": True,
        },
        "recommendations": recommendations,
    }


def print_pretty(report: dict[str, Any]) -> None:
    print("COS Governance ROI")
    print(f"project: {report['project']}")
    print(f"window_hours: {report['window_hours']}")
    roi = report["roi"]
    print(f"net_roi: {roi['net_minutes_estimate']} min ({roi['status']}, heuristic)")
    friction = report["friction"]
    print(f"hooks: invocations={friction['invocations']} blocks={friction['blocking_events']} body_time={friction['body_time_minutes']}m")
    fvc = report["friction_vs_catch"]
    ratio = f"{fvc['ratio']}x" if fvc["ratio"] is not None else "unknown"
    print(f"friction_vs_catch: ratio={ratio} status={fvc['status']}")
    catches = report["catch_ledger"]
    print(f"catch ledger: confirmed={catches['confirmed_valid_blocks']} false_positive_overrides={catches['false_positive_overrides']} silent_loss_prevented={catches['silent_loss_prevented']}")
    phase = report["phase_policy"]
    print(f"phase policy: phase={phase['phase']} strictness={phase['strictness']}")
    benefits = report["benefits"]
    print(f"wip: restores={benefits['wip_restore_events']} orphan_markers={benefits['orphan_marker_count']} auto_stashes={benefits['auto_pre_agent_stash_count']}")
    discovery = report["discovery"]
    print(f"surface: skills={discovery['skill_count']} registered_hooks={discovery['registered_hook_count']} overload={discovery['discovery_overload']}")
    if report["recommendations"]:
        print("recommendations:")
        for item in report["recommendations"]:
            print(f"- {item}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", default=None)
    parser.add_argument("--window-hours", type=int, default=DEFAULT_WINDOW_HOURS)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = build_report(project_dir(args.project_dir), args.window_hours)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_pretty(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
