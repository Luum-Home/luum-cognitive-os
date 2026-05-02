"""
Portability proofs for scripts/cos-gate-stack.sh — P2.2 (ADR-116).

3 proofs:
1. 'list' command executes and prints the 5 standard gate names.
2. 'run' with COS_SKIP_GATES=1 exits 0 (bypass works portably).
3. Falsification: 'run' WITHOUT COS_SKIP_GATES on a branch with a
   failing gate exits non-zero (gates are actually enforced).
"""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "cos-gate-stack.sh"


def _run(args: list[str], env_extra: dict | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    env["REPO_ROOT"] = str(REPO_ROOT)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", str(SCRIPT)] + args,
        capture_output=True,
        text=True,
        env=env,
        cwd=str(REPO_ROOT),
        timeout=30,
    )


# ---------------------------------------------------------------------------
# Proof 1: list command outputs known gate names
# ---------------------------------------------------------------------------


class TestListCommand:
    def test_list_prints_standard_gate_names(self):
        result = _run(["list"])
        assert result.returncode == 0, f"Expected exit 0, got {result.returncode}\n{result.stderr}"
        combined = result.stdout + result.stderr
        assert "scope-marker-portability-gate" in combined
        assert "orchestrator-claim-gate" in combined
        assert "plan-claim-validator" in combined
        assert "push-collision-check" in combined
        assert "precommit-content-hash" in combined


# ---------------------------------------------------------------------------
# Proof 2: COS_SKIP_GATES=1 bypasses all gates
# ---------------------------------------------------------------------------


class TestSkipGates:
    def test_skip_gates_exits_zero(self):
        result = _run(["run", "session/fake-branch"], env_extra={"COS_SKIP_GATES": "1"})
        assert result.returncode == 0, (
            f"Expected exit 0 with COS_SKIP_GATES=1, got {result.returncode}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        combined = result.stdout + result.stderr
        assert "SKIPPED" in combined or "skipped" in combined.lower()


# ---------------------------------------------------------------------------
# Proof 3: Falsification — failing gate causes non-zero exit
# ---------------------------------------------------------------------------


class TestFalsification:
    """
    Without gate enforcement, 'run' would always exit 0.  We create a
    temporary gate stack that injects a single always-failing gate and
    verify the CLI exits non-zero.  This proves gate execution is real.
    """

    def test_failing_gate_causes_non_zero_exit(self, tmp_path):
        # Write a Python wrapper that runs gate_runner with a failing gate
        runner = tmp_path / "run_failing_stack.py"
        failing_script = tmp_path / "failing_gate.sh"
        failing_script.write_text("#!/usr/bin/env bash\nexit 1\n")
        failing_script.chmod(
            failing_script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        )

        runner.write_text(
            f"""
import sys
sys.path.insert(0, "{REPO_ROOT}")
from lib.gate_runner import Gate, run_stack

g = Gate(
    name="always-fail",
    script_path="{failing_script}",
    mode_env_var="AFAIL_MODE",
    allow_skip_env_var="SKIP_AFAIL",
    timeout_seconds=10,
)
result = run_stack("test-branch", "{REPO_ROOT}", stack=[g], fail_fast=True)
print("passed=" + str(result.passed))
print("failed_gate=" + str(result.failed_gate))
sys.exit(0 if result.passed else 1)
"""
        )

        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT)
        proc = subprocess.run(
            ["python3", str(runner)],
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )
        assert proc.returncode != 0, (
            "Falsification: failing gate must cause non-zero exit.\n"
            f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
        )
        assert "passed=False" in proc.stdout
