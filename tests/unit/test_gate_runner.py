"""
Unit tests for lib/gate_runner.py — P2.2 (ADR-116).

8 test cases:
1.  stack order preserved in STANDARD_STACK
2.  fail-fast stops after first failing gate
3.  fail-fast=False runs all gates, aggregates failures
4.  individual gate timeout returns failed GateOutcome with timed_out=True
5.  per-gate bypass env var skips the gate (passed=True, skipped=True)
6.  evidence dict aggregates all outcomes
7.  missing gate script is tolerated (treated as pass/skipped)
8.  full-pass smoke (all gates pass, GateResult.passed=True)
9.  full-fail smoke (first gate fails, passed=False, failed_gate set)
"""

from __future__ import annotations

import os
import stat
import sys
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from lib.gate_runner import (  # noqa: E402
    Gate,
    STANDARD_STACK,
    run_stack,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_script(tmp_path: Path, name: str, exit_code: int, content: str = "") -> Path:
    """Write a tiny bash script that exits with *exit_code*."""
    script = tmp_path / name
    body = content or f"exit {exit_code}"
    script.write_text(f"#!/usr/bin/env bash\n{body}\n")
    script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return script


def _make_gate(name: str, script: Path, timeout: int = 10) -> Gate:
    return Gate(
        name=name,
        script_path=str(script),
        mode_env_var=f"TEST_GATE_{name.upper()}_MODE",
        allow_skip_env_var=f"TEST_SKIP_{name.upper()}",
        timeout_seconds=timeout,
    )


# ---------------------------------------------------------------------------
# 1. Stack order
# ---------------------------------------------------------------------------


class TestStackOrder:
    def test_standard_stack_order(self):
        names = [g.name for g in STANDARD_STACK]
        assert names[0] == "scope-marker-portability-gate"
        assert names[1] == "orchestrator-claim-gate"
        assert names[2] == "plan-claim-validator"
        assert names[3] == "push-collision-check"
        assert names[4] == "precommit-content-hash"
        assert len(names) == 5


# ---------------------------------------------------------------------------
# 2. Fail-fast stops on first failure
# ---------------------------------------------------------------------------


class TestFailFast:
    def test_fail_fast_stops_after_first_failure(self, tmp_path):
        s1 = _make_script(tmp_path, "gate1.sh", 0)
        s2 = _make_script(tmp_path, "gate2.sh", 1)  # fails
        s3 = _make_script(tmp_path, "gate3.sh", 0)

        stack = [
            _make_gate("g1", s1),
            _make_gate("g2", s2),
            _make_gate("g3", s3),
        ]

        result = run_stack("test-branch", tmp_path, stack=stack, fail_fast=True)

        assert result.passed is False
        assert result.failed_gate == "g2"
        # gate g3 should NOT have run (fail-fast)
        run_names = [o.gate_name for o in result.gate_outcomes]
        assert "g3" not in run_names
        assert len(result.gate_outcomes) == 2


# ---------------------------------------------------------------------------
# 3. fail_fast=False runs all gates
# ---------------------------------------------------------------------------


class TestNoFailFast:
    def test_all_gates_run_when_fail_fast_false(self, tmp_path):
        s1 = _make_script(tmp_path, "gate1.sh", 1)  # fails
        s2 = _make_script(tmp_path, "gate2.sh", 0)
        s3 = _make_script(tmp_path, "gate3.sh", 1)  # also fails

        stack = [_make_gate("g1", s1), _make_gate("g2", s2), _make_gate("g3", s3)]
        result = run_stack("b", tmp_path, stack=stack, fail_fast=False)

        assert result.passed is False
        assert result.failed_gate == "g1"  # first failure recorded
        assert len(result.gate_outcomes) == 3
        assert result.evidence["gates_failed"] == 2
        assert result.evidence["gates_passed"] == 1


# ---------------------------------------------------------------------------
# 4. Individual gate timeout
# ---------------------------------------------------------------------------


class TestGateTimeout:
    def test_timeout_returns_failed_outcome(self, tmp_path):
        # Script sleeps longer than the gate timeout
        s = _make_script(tmp_path, "slow.sh", 0, content="sleep 60")
        gate = Gate(
            name="slow-gate",
            script_path=str(s),
            mode_env_var="SLOW_MODE",
            allow_skip_env_var="SKIP_SLOW",
            timeout_seconds=1,  # 1-second timeout
        )

        result = run_stack("b", tmp_path, stack=[gate], fail_fast=True)

        assert result.passed is False
        assert len(result.gate_outcomes) == 1
        outcome = result.gate_outcomes[0]
        assert outcome.timed_out is True
        assert outcome.passed is False


# ---------------------------------------------------------------------------
# 5. Per-gate bypass env var
# ---------------------------------------------------------------------------


class TestBypassEnvVar:
    def test_bypass_skips_gate(self, tmp_path):
        s = _make_script(tmp_path, "failing.sh", 1)
        gate = Gate(
            name="bypassable",
            script_path=str(s),
            mode_env_var="B_MODE",
            allow_skip_env_var="SKIP_BYPASSABLE",
            timeout_seconds=10,
        )

        with patch.dict(os.environ, {"SKIP_BYPASSABLE": "1"}):
            result = run_stack("b", tmp_path, stack=[gate])

        assert result.passed is True
        assert result.gate_outcomes[0].skipped is True
        assert result.gate_outcomes[0].passed is True


# ---------------------------------------------------------------------------
# 6. Evidence aggregation
# ---------------------------------------------------------------------------


class TestEvidenceAggregation:
    def test_evidence_dict_structure(self, tmp_path):
        s1 = _make_script(tmp_path, "g1.sh", 0)
        s2 = _make_script(tmp_path, "g2.sh", 0)
        stack = [_make_gate("e1", s1), _make_gate("e2", s2)]

        result = run_stack("ev-branch", tmp_path, stack=stack, fail_fast=True)

        ev = result.evidence
        assert ev["branch"] == "ev-branch"
        assert ev["gates_run"] == 2
        assert ev["gates_passed"] == 2
        assert ev["gates_failed"] == 0
        assert ev["gates_skipped"] == 0
        assert len(ev["outcomes"]) == 2
        assert ev["outcomes"][0]["gate"] == "e1"
        assert ev["outcomes"][1]["gate"] == "e2"


# ---------------------------------------------------------------------------
# 7. Missing gate script is tolerated
# ---------------------------------------------------------------------------


class TestMissingScript:
    def test_missing_script_treated_as_pass(self, tmp_path):
        gate = Gate(
            name="nonexistent",
            script_path="/nonexistent/path/gate.sh",
            mode_env_var="NE_MODE",
            allow_skip_env_var="SKIP_NE",
            timeout_seconds=10,
        )

        result = run_stack("b", tmp_path, stack=[gate])

        assert result.passed is True
        assert result.gate_outcomes[0].missing_script is True
        assert result.gate_outcomes[0].skipped is True


# ---------------------------------------------------------------------------
# 8. Full-pass smoke
# ---------------------------------------------------------------------------


class TestFullPassSmoke:
    def test_all_passing_gates(self, tmp_path):
        scripts = [_make_script(tmp_path, f"g{i}.sh", 0) for i in range(3)]
        stack = [_make_gate(f"pass{i}", s) for i, s in enumerate(scripts)]

        result = run_stack("main", tmp_path, stack=stack, fail_fast=True)

        assert result.passed is True
        assert result.failed_gate is None
        assert all(o.passed for o in result.gate_outcomes)


# ---------------------------------------------------------------------------
# 9. Full-fail smoke
# ---------------------------------------------------------------------------


class TestFullFailSmoke:
    def test_first_gate_fails(self, tmp_path):
        scripts = [_make_script(tmp_path, f"fail{i}.sh", 1) for i in range(2)]
        stack = [_make_gate(f"fail{i}", s) for i, s in enumerate(scripts)]

        result = run_stack("main", tmp_path, stack=stack, fail_fast=True)

        assert result.passed is False
        assert result.failed_gate == "fail0"
        # fail-fast: only one gate ran
        assert len(result.gate_outcomes) == 1
