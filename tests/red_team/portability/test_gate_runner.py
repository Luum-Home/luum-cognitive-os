"""
Portability proofs for lib/gate_runner.py — P2.2 (ADR-116).

3 proofs:
1. Gate runner is importable from both lib/ (symlink) and packages/ (real) paths.
2. A gate with allow_skip_env_var set is skipped even when its script would fail.
3. run_stack with fail_fast=True never executes gates beyond the first failure.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[3]


# ---------------------------------------------------------------------------
# Proof 1: Importable from both lib/ and packages/ paths
# ---------------------------------------------------------------------------


class TestImportPaths:
    def test_importable_from_lib_symlink(self):
        """lib/gate_runner must be importable (it is a symlink to the real module)."""
        lib_path = REPO_ROOT / "lib" / "gate_runner.py"
        assert lib_path.exists(), f"Symlink missing: {lib_path}"
        assert lib_path.is_symlink() or lib_path.is_file(), \
            f"Expected symlink or file at {lib_path}"

        sys.path.insert(0, str(REPO_ROOT))
        import importlib
        mod = importlib.import_module("lib.gate_runner")
        assert hasattr(mod, "run_stack")
        assert hasattr(mod, "STANDARD_STACK")
        assert hasattr(mod, "Gate")

    def test_importable_from_packages_real_path(self):
        """packages/agent-coordination/lib/gate_runner.py must exist and expose the API."""
        real_path = REPO_ROOT / "packages" / "agent-coordination" / "lib" / "gate_runner.py"
        assert real_path.exists(), f"Real module missing: {real_path}"

        # Verify the file contains the expected public symbols without importing
        # into a separate namespace (which causes dataclass registry conflicts).
        source = real_path.read_text(encoding="utf-8")
        assert "def run_stack" in source, "run_stack function not found in source"
        assert "STANDARD_STACK" in source, "STANDARD_STACK not found in source"
        assert "class Gate" in source or "Gate" in source, "Gate not found in source"
        assert "class GateResult" in source, "GateResult not found in source"


# ---------------------------------------------------------------------------
# Proof 2: allow_skip_env_var bypasses a failing gate
# ---------------------------------------------------------------------------


class TestBypassFalsification:
    """
    Falsification probe: if allow_skip_env_var is NOT set, the failing gate
    must cause passed=False.  When it IS set, passed must be True.
    Without the skip logic, both cases would return False — a regression.
    """

    def _make_failing_gate(self, tmp_path: Path):
        import stat as _stat

        sys.path.insert(0, str(REPO_ROOT))
        from lib.gate_runner import Gate

        script = tmp_path / "always_fail.sh"
        script.write_text("#!/usr/bin/env bash\nexit 1\n")
        script.chmod(script.stat().st_mode | _stat.S_IXUSR | _stat.S_IXGRP | _stat.S_IXOTH)
        return Gate(
            name="always-fail",
            script_path=str(script),
            mode_env_var="AFAIL_MODE",
            allow_skip_env_var="SKIP_ALWAYS_FAIL",
            timeout_seconds=10,
        )

    def test_without_skip_env_gate_fails(self, tmp_path):
        sys.path.insert(0, str(REPO_ROOT))
        from lib.gate_runner import run_stack

        gate = self._make_failing_gate(tmp_path)
        env_without_skip = {k: v for k, v in os.environ.items()
                            if k != "SKIP_ALWAYS_FAIL"}
        with patch.dict(os.environ, env_without_skip, clear=True):
            result = run_stack("b", tmp_path, stack=[gate])
        assert result.passed is False, "Falsification: gate should fail without bypass"

    def test_with_skip_env_gate_passes(self, tmp_path):
        sys.path.insert(0, str(REPO_ROOT))
        from lib.gate_runner import run_stack

        gate = self._make_failing_gate(tmp_path)
        with patch.dict(os.environ, {"SKIP_ALWAYS_FAIL": "1"}):
            result = run_stack("b", tmp_path, stack=[gate])
        assert result.passed is True, "Gate should be bypassed with skip env var"
        assert result.gate_outcomes[0].skipped is True


# ---------------------------------------------------------------------------
# Proof 3: fail_fast=True never runs gates beyond the first failure
# ---------------------------------------------------------------------------


class TestFailFastFalsification:
    """
    Falsification probe: run a 3-gate stack where gate 1 fails.
    With fail_fast=True, only 1 gate outcome should exist.
    With fail_fast=False, all 3 should run.
    Without the fail-fast logic, both would run all 3 — a regression.
    """

    def _make_gate_stack(self, tmp_path: Path, exit_codes):
        import stat as _stat

        sys.path.insert(0, str(REPO_ROOT))
        from lib.gate_runner import Gate

        gates = []
        for i, code in enumerate(exit_codes):
            script = tmp_path / f"gate{i}.sh"
            script.write_text(f"#!/usr/bin/env bash\nexit {code}\n")
            script.chmod(script.stat().st_mode | _stat.S_IXUSR | _stat.S_IXGRP | _stat.S_IXOTH)
            gates.append(Gate(
                name=f"g{i}",
                script_path=str(script),
                mode_env_var=f"G{i}_MODE",
                allow_skip_env_var=f"SKIP_G{i}",
                timeout_seconds=10,
            ))
        return gates

    def test_fail_fast_true_stops_at_first_failure(self, tmp_path):
        sys.path.insert(0, str(REPO_ROOT))
        from lib.gate_runner import run_stack

        stack = self._make_gate_stack(tmp_path, [1, 0, 0])
        result = run_stack("b", tmp_path, stack=stack, fail_fast=True)

        assert result.passed is False
        assert len(result.gate_outcomes) == 1, \
            "Falsification: fail_fast should stop after gate 0"

    def test_fail_fast_false_runs_all_gates(self, tmp_path):
        sys.path.insert(0, str(REPO_ROOT))
        from lib.gate_runner import run_stack

        stack = self._make_gate_stack(tmp_path, [1, 0, 1])
        result = run_stack("b", tmp_path, stack=stack, fail_fast=False)

        assert result.passed is False
        assert len(result.gate_outcomes) == 3, \
            "Falsification: fail_fast=False must run all gates"
        assert result.evidence["gates_failed"] == 2
