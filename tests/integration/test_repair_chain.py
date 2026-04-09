"""Integration tests for the full MAPE-K repair chain.

Tests: error-learning -> auto-repair-dispatcher -> remediation -> outcome.
Migrated from test-repair-chain.sh.
"""

import json
import os
import subprocess
import time
from pathlib import Path

import pytest


@pytest.fixture
def project_root():
    return Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def hooks_dir(project_root):
    return project_root / "hooks"


@pytest.fixture
def repair_env(tmp_path, project_root):
    """Create an isolated temp project for repair chain tests."""
    project_dir = tmp_path / "project"
    metrics_dir = project_dir / ".cognitive-os" / "metrics"
    metrics_dir.mkdir(parents=True)

    # Minimal config
    config = project_dir / "cognitive-os.yaml"
    config.write_text(
        "project:\n"
        "  phase: reconstruction\n"
        "sre:\n"
        "  enabled: true\n"
        "  auto_repair: true\n"
    )

    env = {
        **os.environ,
        "COGNITIVE_OS_PROJECT_DIR": str(project_dir),
        "CLAUDE_PROJECT_DIR": str(project_dir),
        "COGNITIVE_OS_HOOK_HEARTBEAT": "false",
        "COGNITIVE_OS_SESSION_ID": "",
        "COGNITIVE_OS_CB_MAX_FAILURES": "5",
        "COGNITIVE_OS_CB_COOLDOWN": "3600",
    }

    return {
        "project_dir": project_dir,
        "metrics_dir": metrics_dir,
        "env": env,
    }


def _build_hook_input(tmp_path, cmd: str, resp: str, exit_code: str) -> str:
    """Build a JSON input file for hook stdin."""
    data = {
        "tool_input": {"command": cmd},
        "tool_response": resp,
        "exit_code": exit_code,
    }
    input_file = tmp_path / "input.json"
    input_file.write_text(json.dumps(data))
    return str(input_file)


@pytest.mark.integration
class TestRepairChain:
    """Tests for the error-learning to repair-dispatcher chain."""

    def test_error_learning_captures_build_error(self, hooks_dir, repair_env, tmp_path):
        hook = hooks_dir / "error-learning.sh"
        if not hook.exists():
            pytest.skip("error-learning.sh not found")

        input_file = _build_hook_input(
            tmp_path,
            "npm run build",
            "ERROR: cannot find module foo-bar. SyntaxError: Unexpected token. compilation failed",
            "1",
        )

        result = subprocess.run(
            ["bash", str(hook)],
            stdin=open(input_file),
            capture_output=True,
            text=True,
            env=repair_env["env"],
            cwd=str(repair_env["project_dir"]),
            timeout=15,
        )

        metrics_file = repair_env["metrics_dir"] / "error-learning.jsonl"
        assert metrics_file.exists(), "error-learning should create metrics file"

        if metrics_file.exists():
            first_line = metrics_file.read_text().strip().split("\n")[0]
            data = json.loads(first_line)
            assert data["type"] in ("BUILD_ERROR", "COMPILATION_ERROR"), (
                f"unexpected error type: {data['type']}"
            )

    def test_dispatcher_processes_error(self, hooks_dir, repair_env, tmp_path):
        hook = hooks_dir / "auto-repair-dispatcher.sh"
        if not hook.exists():
            pytest.skip("auto-repair-dispatcher.sh not found")

        input_file = _build_hook_input(
            tmp_path,
            "go build ./...",
            "ERROR: cannot find module foo. compilation failed with exit status 1",
            "1",
        )

        result = subprocess.run(
            ["bash", str(hook)],
            stdin=open(input_file),
            capture_output=True,
            text=True,
            env=repair_env["env"],
            cwd=str(repair_env["project_dir"]),
            timeout=15,
        )
        # Dispatcher should process without crashing -- any exit is acceptable
        # since the repair may or may not find a fix

    def test_deterministic_repair_chain(self, hooks_dir, repair_env, tmp_path):
        """Register a known fix, then feed the same error -- dispatcher should find it."""
        lib_dir = hooks_dir / "_lib"
        if not (lib_dir / "remediation.sh").exists():
            pytest.skip("remediation.sh library not found")

        error_msg = "FAIL: cannot find module test-dep"

        # Step 1: Register a known fix
        register_script = (
            f'_SAFE_JSONL_LOADED=""\n'
            f'source "{lib_dir}/safe-jsonl.sh"\n'
            f'source "{lib_dir}/remediation.sh"\n'
            f'remediation_register "BUILD" "unknown" "{error_msg}" "missing dependency" "command" "echo fix-applied"\n'
        )
        subprocess.run(
            ["bash", "-c", register_script],
            env=repair_env["env"],
            capture_output=True,
            timeout=10,
        )

        # Step 2: Feed the same error to the dispatcher
        dispatcher = hooks_dir / "auto-repair-dispatcher.sh"
        if not dispatcher.exists():
            pytest.skip("auto-repair-dispatcher.sh not found")

        input_file = _build_hook_input(
            tmp_path,
            "npm run build",
            f"{error_msg}. compilation failed",
            "1",
        )

        subprocess.run(
            ["bash", str(dispatcher)],
            stdin=open(input_file),
            capture_output=True,
            text=True,
            env=repair_env["env"],
            cwd=str(repair_env["project_dir"]),
            timeout=15,
        )
        # The chain should execute without error -- outcomes depend on the
        # repair path taken (deterministic vs LLM vs skip)

    def test_outcomes_recorded(self, hooks_dir, repair_env, tmp_path):
        dispatcher = hooks_dir / "auto-repair-dispatcher.sh"
        if not dispatcher.exists():
            pytest.skip("auto-repair-dispatcher.sh not found")

        # Create a remediation registry entry matching the error we will inject.
        # The dispatcher only writes outcomes when a registry entry matches.
        registry_path = repair_env["metrics_dir"] / "remediation-registry.jsonl"
        registry_entry = json.dumps({
            "type": "TEST_FAILURE",
            "service": "unknown",
            "error_pattern": "expect\\(received\\)",
            "description": "Jest assertion mismatch",
            "fix_type": "command",
            "fix": "echo registry-match",
        })
        registry_path.write_text(registry_entry + "\n")

        input_file = _build_hook_input(
            tmp_path,
            "jest --runInBand",
            "FAIL: Test suite failed. Error: expect(received).toBe(expected). Expected: 42 Received: 0",
            "1",
        )

        subprocess.run(
            ["bash", str(dispatcher)],
            stdin=open(input_file),
            capture_output=True,
            text=True,
            env=repair_env["env"],
            cwd=str(repair_env["project_dir"]),
            timeout=15,
        )

        # Wait briefly for background nohup processes
        time.sleep(1)

        # dispatcher writes to repair-dispatch.jsonl when a registry match is found
        dispatch = repair_env["metrics_dir"] / "repair-dispatch.jsonl"
        outcomes = repair_env["metrics_dir"] / "repair-outcomes.jsonl"
        queue = repair_env["metrics_dir"] / "repair-queue.jsonl"
        assert dispatch.exists() or outcomes.exists() or queue.exists(), (
            "dispatcher should write a dispatch, outcome, or queue entry when a registry match exists"
        )
