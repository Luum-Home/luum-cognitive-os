# SCOPE: both
# scope: both
"""
Composable gate runner — P2.2 (ADR-116).

Provides a standard stack of pre-merge gates that the merge-queue worker
invokes BEFORE ff-merging a session branch.  Each gate is a subprocess with
a configurable timeout, per-gate bypass env var, and event-bus emission.

Gate stack order (STANDARD_STACK):
  1. scope-marker-portability-gate  — SCOPE: both files have paired tests
  2. orchestrator-claim-gate         — bilateral claim verification
  3. plan-claim-validator            — checkbox transitions have evidence
  4. push-collision-check            — subject collision vs origin/main
  5. precommit_content_hash          — patch-id dedupe (P4.1)

Public API
----------
run_stack(branch, repo_root, stack=STANDARD_STACK, fail_fast=True) -> GateResult

Python 3.9+ compatible.
"""

from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class Gate:
    """Descriptor for a single gate in the stack."""

    name: str
    """Human-readable gate name."""

    script_path: str
    """Path to the gate script/binary, relative to repo_root (or absolute)."""

    mode_env_var: str
    """Environment variable that controls the gate's mode (warn/block)."""

    allow_skip_env_var: str
    """Setting this env var to '1' or 'true' bypasses the gate entirely."""

    timeout_seconds: int = 60
    """Subprocess timeout in seconds."""


@dataclass
class GateOutcome:
    """Result for a single gate execution."""

    gate_name: str
    passed: bool
    skipped: bool = False
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    missing_script: bool = False


@dataclass
class GateResult:
    """Aggregate result of running a gate stack."""

    passed: bool
    gate_outcomes: List[GateOutcome] = field(default_factory=list)
    failed_gate: Optional[str] = None
    evidence: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Standard gate stack
# ---------------------------------------------------------------------------

STANDARD_STACK: List[Gate] = [
    Gate(
        name="scope-marker-portability-gate",
        script_path="hooks/scope-marker-portability-gate.sh",
        mode_env_var="COS_SCOPE_GATE_MODE",
        allow_skip_env_var="COS_SKIP_SCOPE_GATE",
        timeout_seconds=60,
    ),
    Gate(
        name="orchestrator-claim-gate",
        script_path="hooks/orchestrator-claim-gate.sh",
        mode_env_var="COS_ORCHESTRATOR_CLAIM_GATE_MODE",
        allow_skip_env_var="COS_SKIP_CLAIM_GATE",
        timeout_seconds=120,
    ),
    Gate(
        name="plan-claim-validator",
        script_path="hooks/plan-claim-validator.sh",
        mode_env_var="COS_PLAN_VALIDATOR_MODE",
        allow_skip_env_var="COS_SKIP_PLAN_VALIDATOR",
        timeout_seconds=60,
    ),
    Gate(
        name="push-collision-check",
        script_path="hooks/_lib/push-collision-check.sh",
        mode_env_var="COS_PUSH_COLLISION_MODE",
        allow_skip_env_var="DISABLE_HOOK_PUSH_COLLISION_CHECK",
        timeout_seconds=60,
    ),
    Gate(
        name="precommit-content-hash",
        script_path="scripts/precommit_content_hash.py",
        mode_env_var="COS_DEDUPE_MODE",
        allow_skip_env_var="COS_SKIP_DEDUPE",
        timeout_seconds=120,
    ),
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _emit_event(event_type: str, payload: dict, session_id: str) -> None:
    """Emit an event to the bus — best-effort; never raises."""
    try:
        from lib.event_bus import emit  # type: ignore[import]

        emit(event_type, payload, session_id=session_id)
    except Exception as exc:  # noqa: BLE001
        logger.debug("gate_runner: event_bus emit failed (best-effort): %s", exc)


def _resolve_script(script_path: str, repo_root: Path) -> Optional[Path]:
    """Return absolute Path for *script_path* or None if not found."""
    p = Path(script_path)
    if p.is_absolute():
        return p if p.exists() else None
    candidate = repo_root / script_path
    return candidate if candidate.exists() else None


def _build_env(gate: Gate, branch: str, repo_root: Path) -> dict:
    """Build the subprocess environment for a gate run."""
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(repo_root)
    env["CLAUDE_PROJECT_DIR"] = str(repo_root)
    env["PYTHONPATH"] = str(repo_root)
    env["GIT_BRANCH"] = branch
    # Gates that look at git context should operate in the repo root.
    env["GIT_DIR"] = str(repo_root / ".git")
    env["GIT_WORK_TREE"] = str(repo_root)
    return env


def _is_python_script(script_path: str) -> bool:
    return script_path.endswith(".py")


def _run_gate(gate: Gate, branch: str, repo_root: Path) -> GateOutcome:
    """Execute a single gate and return its GateOutcome."""
    # Check per-gate bypass.
    bypass_val = os.environ.get(gate.allow_skip_env_var, "")
    if bypass_val in ("1", "true", "True", "yes"):
        logger.info("gate_runner: gate '%s' SKIPPED (%s=1)", gate.name, gate.allow_skip_env_var)
        return GateOutcome(
            gate_name=gate.name,
            passed=True,
            skipped=True,
            exit_code=0,
        )

    # Resolve script.
    script = _resolve_script(gate.script_path, repo_root)
    if script is None:
        logger.warning(
            "gate_runner: gate '%s' script not found at '%s' — tolerating missing gate",
            gate.name,
            gate.script_path,
        )
        return GateOutcome(
            gate_name=gate.name,
            passed=True,
            skipped=True,
            missing_script=True,
            exit_code=0,
        )

    env = _build_env(gate, branch, repo_root)

    # Build command: python scripts or bash scripts.
    if _is_python_script(gate.script_path):
        cmd = ["python3", str(script)]
    else:
        cmd = ["bash", str(script)]

    # Inject a minimal hook-style JSON payload for hooks that read stdin.
    # For Python scripts (like precommit_content_hash), stdin is not used.
    stdin_payload: Optional[bytes] = None
    if not _is_python_script(gate.script_path):
        import json

        stdin_payload = json.dumps(
            {
                "tool_name": "Bash",
                "tool_input": {
                    "command": f"git push origin main  # gate-runner branch={branch}"
                },
            }
        ).encode("utf-8")

    try:
        result = subprocess.run(
            cmd,
            input=stdin_payload,
            capture_output=True,
            env=env,
            cwd=str(repo_root),
            timeout=gate.timeout_seconds,
        )
        stdout = result.stdout.decode("utf-8", errors="replace")
        stderr = result.stderr.decode("utf-8", errors="replace")
        passed = result.returncode == 0
        return GateOutcome(
            gate_name=gate.name,
            passed=passed,
            exit_code=result.returncode,
            stdout=stdout,
            stderr=stderr,
        )
    except subprocess.TimeoutExpired as exc:
        logger.warning("gate_runner: gate '%s' timed out after %ds", gate.name, gate.timeout_seconds)
        stdout = (exc.stdout or b"").decode("utf-8", errors="replace")
        stderr = (exc.stderr or b"").decode("utf-8", errors="replace")
        return GateOutcome(
            gate_name=gate.name,
            passed=False,
            timed_out=True,
            exit_code=-1,
            stdout=stdout,
            stderr=stderr,
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_stack(
    branch: str,
    repo_root: str | Path,
    stack: List[Gate] = STANDARD_STACK,
    fail_fast: bool = True,
    session_id: Optional[str] = None,
) -> GateResult:
    """Run a list of gates in order against *branch*.

    Parameters
    ----------
    branch:
        The session branch name being evaluated (informational for env injection).
    repo_root:
        Absolute path to the repository root.
    stack:
        Ordered list of Gate descriptors to run.
    fail_fast:
        If True, stop on the first failing gate.  If False, run all gates and
        aggregate failures.
    session_id:
        Session ID for event emission; defaults to ``COGNITIVE_OS_SESSION_ID``.

    Returns
    -------
    GateResult
        Aggregate result with per-gate outcomes and evidence dict.
    """
    root = Path(repo_root).resolve()
    sid = session_id or os.environ.get("COGNITIVE_OS_SESSION_ID", "gate-runner")

    outcomes: List[GateOutcome] = []
    failed_gate: Optional[str] = None
    all_passed = True

    for gate in stack:
        logger.info("gate_runner: running gate '%s' on branch '%s'", gate.name, branch)
        outcome = _run_gate(gate, branch, root)
        outcomes.append(outcome)

        _emit_event(
            "gate_outcome" if outcome.passed else "gate_failed",
            {
                "gate": gate.name,
                "branch": branch,
                "passed": outcome.passed,
                "skipped": outcome.skipped,
                "exit_code": outcome.exit_code,
                "timed_out": outcome.timed_out,
                "missing_script": outcome.missing_script,
            },
            session_id=sid,
        )

        if not outcome.passed:
            all_passed = False
            if failed_gate is None:
                failed_gate = gate.name
            if fail_fast:
                logger.info(
                    "gate_runner: FAIL-FAST on gate '%s' (exit=%d)",
                    gate.name,
                    outcome.exit_code,
                )
                break

    evidence = {
        "branch": branch,
        "gates_run": len(outcomes),
        "gates_passed": sum(1 for o in outcomes if o.passed),
        "gates_failed": sum(1 for o in outcomes if not o.passed),
        "gates_skipped": sum(1 for o in outcomes if o.skipped),
        "outcomes": [
            {
                "gate": o.gate_name,
                "passed": o.passed,
                "skipped": o.skipped,
                "exit_code": o.exit_code,
                "timed_out": o.timed_out,
                "missing_script": o.missing_script,
            }
            for o in outcomes
        ],
    }

    return GateResult(
        passed=all_passed,
        gate_outcomes=outcomes,
        failed_gate=failed_gate,
        evidence=evidence,
    )
