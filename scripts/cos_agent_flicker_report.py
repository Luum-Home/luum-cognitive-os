#!/usr/bin/env python3
# SCOPE: os-only
"""Build the Agent Flicker Control capability report.

The report groups existing Cognitive OS primitives that bound AI-agent
oscillation, false completion, retry thrashing, drift, and concurrent-work
conflicts. It is intentionally evidence-oriented: static readiness is based on
repo artifacts and hook registrations, while runtime attention is derived only
from local metrics/state files that already exist.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

SCHEMA_VERSION = "agent-flicker-control-report/v1"


@dataclass(frozen=True)
class ControlSurface:
    """One anti-flicker control surface and its evidence links."""

    control_id: str
    title: str
    failure_modes: list[str]
    enforcement: str
    artifacts: list[str]
    docs: list[str]
    tests: list[str]
    hooks: list[str] = field(default_factory=list)
    status: str = "unknown"
    missing_artifacts: list[str] = field(default_factory=list)
    missing_docs: list[str] = field(default_factory=list)
    missing_tests: list[str] = field(default_factory=list)
    registered_surfaces: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable control surface."""
        return asdict(self)


@dataclass(frozen=True)
class RuntimeSignal:
    """A local runtime signal that may indicate active agent flicker pressure."""

    signal_id: str
    severity: str
    message: str
    evidence: str

    def to_dict(self) -> dict[str, str]:
        """Return a JSON-serializable runtime signal."""
        return asdict(self)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _exists_all(project_dir: Path, paths: Iterable[str]) -> list[str]:
    return [path for path in paths if not (project_dir / path).exists()]


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _hook_registrations(project_dir: Path, hooks: Sequence[str]) -> list[str]:
    """Return settings/config surfaces that mention at least one hook."""
    config_paths = [
        ".claude/settings.json",
        ".codex/hooks.json",
        ".cognitive-os/cos-runner-hooks.json",
        "cognitive-os.yaml",
    ]
    surfaces: list[str] = []
    for rel in config_paths:
        text = _read_text(project_dir / rel)
        if not text:
            continue
        if any(hook in text for hook in hooks):
            surfaces.append(rel)
    return surfaces


def _control_definitions() -> list[dict[str, Any]]:
    return [
        {
            "control_id": "bounded-reflection",
            "title": "Bounded reflection loop",
            "failure_modes": ["single-pass answer drift", "unbounded self-critique loops"],
            "enforcement": "composable primitive; bounded by min_reflect/max_reflect",
            "artifacts": ["lib/agent_reflection.py"],
            "docs": ["docs/02-Decisions/adrs/ADR-295-agent-reflection-loop-primitive.md"],
            "tests": ["tests/unit/test_agent_reflection.py"],
        },
        {
            "control_id": "deterministic-goal-loop",
            "title": "Deterministic goal completion contract",
            "failure_modes": ["false completion", "proxy evidence", "no-progress loops", "budget runaway"],
            "enforcement": (
                "Stop hook blocks active incomplete goals; terminal budget/escalation "
                "states allow stop honestly"
            ),
            "artifacts": [
                "lib/goal_state.py",
                "lib/goal_evaluator.py",
                "lib/goal_evidence.py",
                "lib/goal_budget.py",
                "hooks/goal-stop-gate.sh",
                "scripts/cos_goal.py",
                "scripts/cos-goal",
            ],
            "docs": ["docs/04-Concepts/architecture/goal-loop.md"],
            "tests": [
                "tests/unit/test_goal_state.py",
                "tests/unit/test_goal_evidence.py",
                "tests/unit/test_goal_evaluator.py",
                "tests/unit/test_goal_budget.py",
                "tests/behavior/test_goal_stop_hook.py",
            ],
            "hooks": ["goal-stop-gate"],
        },
        {
            "control_id": "task-closure-ledger",
            "title": "Task closure ledger gate",
            "failure_modes": ["claimability oscillation", "hidden remaining work", "closed/open state divergence"],
            "enforcement": "ledger invariants plus optional closureGate execution",
            "artifacts": ["scripts/cos_task_closure_gate.py", "scripts/cos-task-closure-gate"],
            "docs": [
                "docs/02-Decisions/adrs/ADR-335-generic-task-closure-ledger-gate.md",
                "docs/04-Concepts/architecture/task-closure-ledger-gate.md",
            ],
            "tests": ["tests/unit/test_cos_task_closure_gate.py", "tests/contracts/test_task_closure_gate_contract.py"],
        },
        {
            "control_id": "claim-verification",
            "title": "High-stakes claim verification",
            "failure_modes": ["contradictory completion claims", "hallucinated files", "test-pass self-report"],
            "enforcement": "claim enforcer reruns verification and gates plan/commit claims",
            "artifacts": [
                "scripts/claim_enforcer.py",
                "hooks/claim-validator.sh",
                "hooks/orchestrator-claim-gate.sh",
                "hooks/agent-output-verifier.sh",
            ],
            "docs": [
                "docs/02-Decisions/adrs/ADR-105-claim-verification-contract.md",
                "docs/02-Decisions/adrs/ADR-244-trust-report-claim-validator-must-enforce.md",
            ],
            "tests": ["tests/behavior/test_claim_enforcer.py", "tests/contracts/test_orchestrator_claim_gate.py"],
            "hooks": ["claim-validator", "orchestrator-claim-gate", "agent-output-verifier"],
        },
        {
            "control_id": "retry-backoff-circuit-breaker",
            "title": "Retry, backoff, queue, and circuit breaker",
            "failure_modes": ["retry thrashing", "rate-limit bursts", "persistent provider failure loops"],
            "enforcement": "persistent queue, retry caps, exponential backoff, cooldown, half-open probe",
            "artifacts": [
                "lib/rate_limiter.py",
                "lib/circuit_breaker.py",
                "hooks/rate-limiter.sh",
                "hooks/rate-limit-precheck.sh",
                "hooks/rate-limit-drain.sh",
            ],
            "docs": [
                "docs/02-Decisions/adrs/ADR-228-retry-contract-and-cost-budget.md",
                "docs/04-Concepts/architecture/rate-limiter-flow-control.md",
            ],
            "tests": [
                "tests/unit/test_rate_limiter.py",
                "tests/unit/test_rate_limiter_behavior.py",
                "tests/unit/test_circuit_breaker.py",
                "tests/integration/test_rate_limiter_hook_retry_flow.py",
            ],
            "hooks": ["rate-limiter", "rate-limit-precheck", "rate-limit-drain"],
        },
        {
            "control_id": "no-progress-escalation",
            "title": "No-progress and repeated-pattern escalation",
            "failure_modes": ["same command loop", "same file edit loop", "same error loop", "timeout-risk drift"],
            "enforcement": "structured ESCALATION signal with evidence and next action",
            "artifacts": ["lib/escalation_detector.py"],
            "docs": ["docs/02-Decisions/adrs/ADR-228-retry-contract-and-cost-budget.md"],
            "tests": ["tests/unit/test_escalation_detector.py", "tests/behavior/test_agent_escalation.py"],
        },
        {
            "control_id": "coordination-locks",
            "title": "Cross-session coordination and write guards",
            "failure_modes": [
                "parallel agents overwrite each other",
                "duplicate task claims",
                "branch/worktree conflict",
            ],
            "enforcement": "claim ledgers, fcntl locks, concurrent write guards, coordination status",
            "artifacts": [
                "lib/session_coordination.py",
                "lib/task_claim_ledger.py",
                "hooks/concurrent-write-guard.sh",
                "hooks/cross-session-coordination-guard.sh",
            ],
            "docs": [
                "docs/02-Decisions/adrs/ADR-108-concurrent-agent-safety-layer.md",
                "docs/02-Decisions/adrs/ADR-116-multi-session-coordination-primitives.md",
            ],
            "tests": [
                "tests/unit/test_session_coordination.py",
                "tests/unit/test_concurrent_write_guard_behavior.py",
            ],
            "hooks": ["concurrent-write-guard", "cross-session-coordination-guard"],
        },
        {
            "control_id": "checkpoint-repair-isolation",
            "title": "Checkpoint and repair isolation",
            "failure_modes": ["repair pollution", "unsafe rollback", "lost work after crash"],
            "enforcement": (
                "copy-only checkpoints, reviewed stash restore, "
                "worktree-isolated auto-repair, repair circuit breaker"
            ),
            "artifacts": [
                "lib/checkpoint_manager.py",
                "lib/auto_repair.py",
                "hooks/auto-checkpoint.sh",
                "hooks/auto-repair-dispatcher.sh",
            ],
            "docs": [
                "docs/04-Concepts/root/auto-repair-system.md",
                "docs/02-Decisions/adrs/ADR-318-copy-only-checkpoints-and-stash-quarantine.md",
            ],
            "tests": ["tests/unit/test_checkpoint_manager.py", "tests/unit/test_auto_repair.py"],
            "hooks": ["auto-checkpoint", "auto-repair-dispatcher"],
        },
        {
            "control_id": "skill-drift-detection",
            "title": "Skill registry runtime drift detection",
            "failure_modes": ["runtime skill drift", "silent mutation", "federated evidence invalidation"],
            "enforcement": "SessionStart drift detector with warn/block policy",
            "artifacts": ["lib/skill_drift_detector.py", "hooks/skill-drift-detector.sh"],
            "docs": ["docs/02-Decisions/adrs/ADR-285-skill-registry-runtime-drift-detection.md"],
            "tests": ["tests/unit/test_skill_drift_detector.py"],
            "hooks": ["skill-drift-detector"],
        },
        {
            "control_id": "context-quality-close",
            "title": "Context budget and session quality close gates",
            "failure_modes": ["context overload", "closing after known failing evidence", "validation drift"],
            "enforcement": "context meter plus Stop close gate for explicit failing quality evidence",
            "artifacts": [
                "hooks/context-budget-meter.sh",
                "hooks/session-quality-close-gate.sh",
                "lib/context_budget_monitor.py",
            ],
            "docs": [
                "docs/02-Decisions/adrs/ADR-143-closure-discipline-gate.md",
                "docs/04-Concepts/architecture/hook-quality-system.md",
            ],
            "tests": [
                "tests/unit/test_context_budget_monitor.py",
                "tests/contracts/test_context_budget_hook_wiring.py",
            ],
            "hooks": ["context-budget-meter", "session-quality-close-gate"],
        },
    ]


def build_controls(project_dir: Path) -> list[ControlSurface]:
    """Build static readiness rows for every flicker-control surface."""
    rows: list[ControlSurface] = []
    for definition in _control_definitions():
        missing_artifacts = _exists_all(project_dir, definition["artifacts"])
        missing_docs = _exists_all(project_dir, definition["docs"])
        missing_tests = _exists_all(project_dir, definition["tests"])
        registered = _hook_registrations(project_dir, definition.get("hooks", [])) if definition.get("hooks") else []
        status = "pass"
        if missing_artifacts or missing_docs or missing_tests:
            status = "fail"
        elif definition.get("hooks") and not registered:
            status = "warn"
        rows.append(
            ControlSurface(
                control_id=definition["control_id"],
                title=definition["title"],
                failure_modes=list(definition["failure_modes"]),
                enforcement=definition["enforcement"],
                artifacts=list(definition["artifacts"]),
                docs=list(definition["docs"]),
                tests=list(definition["tests"]),
                hooks=list(definition.get("hooks", [])),
                status=status,
                missing_artifacts=missing_artifacts,
                missing_docs=missing_docs,
                missing_tests=missing_tests,
                registered_surfaces=registered,
            )
        )
    return rows


def _jsonl_rows(path: Path, max_rows: int = 2000) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    buffered: deque[str] = deque(maxlen=max_rows)
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                buffered.append(line)
    except OSError:
        return []
    rows: list[dict[str, Any]] = []
    for line in buffered:
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            rows.append(item)
    return rows


def _queue_items(project_dir: Path) -> list[dict[str, Any]]:
    queue_path = project_dir / ".cognitive-os" / "rate-limit-queue.jsonl"
    rows = _jsonl_rows(queue_path)
    active: dict[str, dict[str, Any]] = {}
    for row in rows:
        action = row.get("action")
        item = row.get("item") if isinstance(row.get("item"), dict) else None
        action_id = str(row.get("action_id") or (item or {}).get("queue_id") or "")
        if not action_id:
            continue
        if action in {"queued", "retried"} and item is not None:
            active[action_id] = item
        elif action in {"dequeued", "dropped", "cancelled"}:
            active.pop(action_id, None)
    return list(active.values())


def build_runtime_signals(project_dir: Path) -> list[RuntimeSignal]:
    """Collect local runtime signals that may require attention."""
    signals: list[RuntimeSignal] = []

    goal_path = project_dir / ".cognitive-os" / "goals" / "default" / "current.json"
    if goal_path.exists():
        try:
            goal = json.loads(goal_path.read_text(encoding="utf-8"))
            if goal.get("status") == "active":
                signals.append(
                    RuntimeSignal(
                        "active-goal",
                        "info",
                        "An active goal is present; Stop should be controlled by goal-stop-gate.",
                        str(goal_path),
                    )
                )
        except (OSError, json.JSONDecodeError):
            signals.append(
                RuntimeSignal(
                    "goal-state-unreadable",
                    "warn",
                    "Goal state exists but could not be parsed.",
                    str(goal_path),
                )
            )

    queue_items = _queue_items(project_dir)
    if queue_items:
        max_retry = max(int(item.get("retry_count", 0)) for item in queue_items)
        severity = "warn" if max_retry >= 2 or len(queue_items) >= 5 else "info"
        signals.append(
            RuntimeSignal(
                "rate-limit-queue",
                severity,
                f"Rate-limit retry queue has {len(queue_items)} active item(s); max retry_count={max_retry}.",
                ".cognitive-os/rate-limit-queue.jsonl",
            )
        )

    dropped = _jsonl_rows(project_dir / ".cognitive-os" / "rate-limit-dropped.jsonl")
    if dropped:
        signals.append(
            RuntimeSignal(
                "rate-limit-dropped",
                "warn",
                f"Rate-limit retry cap dropped {len(dropped)} item(s) in the sampled log.",
                ".cognitive-os/rate-limit-dropped.jsonl",
            )
        )

    claim_rows = _jsonl_rows(project_dir / ".cognitive-os" / "metrics" / "claim-enforcer.jsonl")
    blocked_claims = [
        row for row in claim_rows if str(row.get("status", "")).lower() == "block" or row.get("ok") is False
    ]
    if blocked_claims:
        signals.append(
            RuntimeSignal(
                "claim-enforcer-blocks",
                "warn",
                (
                    f"Claim enforcer recorded {len(blocked_claims)} blocking "
                    "high-stakes claim event(s) in sampled metrics."
                ),
                ".cognitive-os/metrics/claim-enforcer.jsonl",
            )
        )

    drift_rows = _jsonl_rows(project_dir / ".cognitive-os" / "metrics" / "skill-drift.jsonl")
    if drift_rows:
        signals.append(
            RuntimeSignal(
                "skill-drift-events",
                "warn",
                f"Skill drift detector recorded {len(drift_rows)} drift event(s) in sampled metrics.",
                ".cognitive-os/metrics/skill-drift.jsonl",
            )
        )

    quality_paths = [
        project_dir / ".cognitive-os" / "metrics" / "auto-verify.jsonl",
        project_dir / ".cognitive-os" / "metrics" / "quality-gate.jsonl",
        project_dir / ".cognitive-os" / "metrics" / "session-quality.jsonl",
    ]
    failing_quality = 0
    for path in quality_paths:
        for row in _jsonl_rows(path):
            fields = [
                str(row.get(key, "")).lower()
                for key in ("status", "result", "outcome", "verdict", "decision")
            ]
            if any(
                value in {"fail", "failed", "failure", "block", "blocked", "error", "deny", "denied"}
                for value in fields
            ):
                failing_quality += 1
    if failing_quality:
        signals.append(
            RuntimeSignal(
                "quality-close-blockers",
                "warn",
                f"Quality/session metrics include {failing_quality} explicit failing event(s) in sampled logs.",
                ".cognitive-os/metrics",
            )
        )

    return signals


def build_report(project_dir: str | Path) -> dict[str, Any]:
    """Build the complete Agent Flicker Control report."""
    root = Path(project_dir).resolve()
    controls = build_controls(root)
    signals = build_runtime_signals(root)
    fail_count = sum(1 for item in controls if item.status == "fail")
    warn_count = sum(1 for item in controls if item.status == "warn")
    runtime_warn_count = sum(1 for item in signals if item.severity == "warn")
    status = "pass"
    if fail_count:
        status = "fail"
    elif warn_count or runtime_warn_count:
        status = "warn"
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "project_dir": str(root),
        "status": status,
        "summary": {
            "control_count": len(controls),
            "static_pass": sum(1 for item in controls if item.status == "pass"),
            "static_warn": warn_count,
            "static_fail": fail_count,
            "runtime_signal_count": len(signals),
            "runtime_warn_count": runtime_warn_count,
        },
        "definition": {
            "agent_flicker": (
                "Oscillation or instability in agent behavior: false completion, "
                "contradictory claims, repeated retries, no-progress loops, runtime drift, "
                "or concurrent sessions overwriting each other."
            ),
            "claim_boundary": (
                "This report groups existing controls; it does not claim a single "
                "always-on model-level anti-flicker algorithm."
            ),
        },
        "controls": [item.to_dict() for item in controls],
        "runtime_signals": [item.to_dict() for item in signals],
        "next_actions": _next_actions(fail_count, warn_count, runtime_warn_count),
    }


def _next_actions(fail_count: int, warn_count: int, runtime_warn_count: int) -> list[str]:
    actions: list[str] = []
    if fail_count:
        actions.append("Restore missing artifacts, docs, or tests before claiming Agent Flicker Control readiness.")
    if warn_count:
        actions.append(
            "Review hook registration warnings; some controls may be available but not projected on every harness."
        )
    if runtime_warn_count:
        actions.append(
            "Inspect runtime warning signals and clear them only by replacing "
            "stale failing evidence with passing evidence."
        )
    if not actions:
        actions.append("Keep this report in release/doctor evidence when making product claims about agent stability.")
    return actions


def print_text(report: dict[str, Any]) -> None:
    """Print a compact human-readable report."""
    summary = report["summary"]
    print(f"Agent Flicker Control: {report['status'].upper()}")
    print(
        "controls={control_count} pass={static_pass} warn={static_warn} fail={static_fail} "
        "runtime_signals={runtime_signal_count}".format(**summary)
    )
    print("Definition: " + report["definition"]["agent_flicker"])
    print("\nControls:")
    for control in report["controls"]:
        print(f"- {control['control_id']}: {control['status']} — {control['title']}")
        if control["registered_surfaces"]:
            print("  registered: " + ", ".join(control["registered_surfaces"]))
        missing = control["missing_artifacts"] + control["missing_docs"] + control["missing_tests"]
        if missing:
            print("  missing: " + ", ".join(missing))
    if report["runtime_signals"]:
        print("\nRuntime signals:")
        for signal in report["runtime_signals"]:
            print(f"- [{signal['severity']}] {signal['signal_id']}: {signal['message']} ({signal['evidence']})")
    print("\nNext actions:")
    for action in report["next_actions"]:
        print(f"- {action}")


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Report Cognitive OS Agent Flicker Control readiness and runtime signals."
    )
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=Path(os.environ.get("COGNITIVE_OS_PROJECT_DIR") or os.getcwd()),
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    parser.add_argument("--strict", action="store_true", help="Exit 2 on warn/fail status.")
    args = parser.parse_args(list(argv) if argv is not None else None)
    report = build_report(args.project_dir)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_text(report)
    if report["status"] == "fail":
        return 2
    if args.strict and report["status"] != "pass":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
