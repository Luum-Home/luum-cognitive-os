"""CLI-level tests for scripts/orchestrator.py.

Tests the dispatch and observability surface WITHOUT spawning a real sub-Claude.
Each test exercises the CLI interface (argument parsing, exit codes, output format)
using subprocess.run. No actual agents are launched.

Every test is capped at 10 seconds via pytest-timeout.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ORCHESTRATOR = PROJECT_ROOT / "scripts" / "orchestrator.py"

pytestmark = [pytest.mark.behavior]


def _run(*args: str, stdin: str = "", timeout: int = 10, env: dict | None = None) -> subprocess.CompletedProcess:
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    return subprocess.run(
        [sys.executable, str(ORCHESTRATOR), *args],
        input=stdin,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=run_env,
    )


# ---------------------------------------------------------------------------
# --help
# ---------------------------------------------------------------------------

class TestHelpCommand:
    """orchestrator --help prints usage and documents all subcommands."""

    def test_help_exits_zero(self):
        result = _run("--help")
        assert result.returncode == 0, result.stderr

    def test_help_shows_run_subcommand(self):
        result = _run("--help")
        assert "run" in result.stdout

    def test_help_shows_list_live_subcommand(self):
        result = _run("--help")
        assert "list-live" in result.stdout

    def test_help_shows_scan_stale_subcommand(self):
        result = _run("--help")
        assert "scan-stale" in result.stdout

    def test_help_shows_kill_hung_subcommand(self):
        result = _run("--help")
        assert "kill-hung" in result.stdout


# ---------------------------------------------------------------------------
# scan-stale
# ---------------------------------------------------------------------------

class TestScanStale:
    """scan-stale subcommand: zero exit, prints readable output."""

    def test_scan_stale_exits_zero(self, tmp_path):
        result = _run(
            "scan-stale",
            env={"COGNITIVE_OS_PROJECT_DIR": str(tmp_path)},
        )
        assert result.returncode == 0, result.stderr

    def test_scan_stale_prints_no_stale_or_table_header(self, tmp_path):
        result = _run(
            "scan-stale",
            env={"COGNITIVE_OS_PROJECT_DIR": str(tmp_path)},
        )
        output = result.stdout + result.stderr
        # Either "No stale agents." OR a table header line
        assert ("No stale agents." in output) or ("AGENT ID" in output), (
            f"Unexpected output: {output!r}"
        )


# ---------------------------------------------------------------------------
# list-live
# ---------------------------------------------------------------------------

class TestListLive:
    """list-live subcommand: zero exit, prints readable output."""

    def test_list_live_exits_zero(self, tmp_path):
        result = _run(
            "list-live",
            env={"COGNITIVE_OS_PROJECT_DIR": str(tmp_path)},
        )
        assert result.returncode == 0, result.stderr

    def test_list_live_prints_no_agents_or_table_header(self, tmp_path):
        result = _run(
            "list-live",
            env={"COGNITIVE_OS_PROJECT_DIR": str(tmp_path)},
        )
        output = result.stdout + result.stderr
        assert ("No live agents." in output) or ("AGENT ID" in output), (
            f"Unexpected output: {output!r}"
        )


# ---------------------------------------------------------------------------
# run — missing task → returncode 2
# ---------------------------------------------------------------------------

class TestRunMissingTask:
    """orchestrator run with no --task and no stdin must exit 2."""

    def test_run_no_task_no_stdin_exits_2(self):
        """Pipe empty stdin so the script doesn't wait on a tty."""
        result = _run("run", stdin="")
        assert result.returncode == 2, (
            f"Expected exit 2, got {result.returncode}. stderr={result.stderr!r}"
        )

    def test_run_no_task_stderr_explains_error(self):
        result = _run("run", stdin="")
        assert "no task provided" in result.stderr.lower(), (
            f"Expected 'no task provided' in stderr. stderr={result.stderr!r}"
        )

    def test_toplevl_invocation_no_args_exits_2(self):
        """Invoking with no subcommand falls through to cmd_run with empty stdin."""
        result = _run(stdin="")
        assert result.returncode == 2, (
            f"Expected exit 2, got {result.returncode}. stderr={result.stderr!r}"
        )


# ---------------------------------------------------------------------------
# kill-hung — nonexistent agent → fallback bus artifact written
# ---------------------------------------------------------------------------

class TestKillHung:
    """kill-hung produces a stop signal artifact (FallbackBus control.jsonl)."""

    def test_kill_hung_nonexistent_agent_exits_zero(self, tmp_path):
        result = _run(
            "kill-hung", "nonexistent-agent-id",
            env={"COGNITIVE_OS_PROJECT_DIR": str(tmp_path)},
        )
        assert result.returncode == 0, result.stderr

    def test_kill_hung_writes_control_artifact(self, tmp_path):
        """When Valkey is absent, mark_hung_and_publish writes to FallbackBus control file."""
        agent_id = "nonexistent-agent-id"
        _run(
            "kill-hung", agent_id,
            env={"COGNITIVE_OS_PROJECT_DIR": str(tmp_path)},
        )
        # FallbackBus writes control signal under .cognitive-os/agent-bus/<agent-id>/control.jsonl
        agent_bus_dir = tmp_path / ".cognitive-os" / "agent-bus"
        control_files = list(agent_bus_dir.rglob("control.jsonl")) if agent_bus_dir.exists() else []

        # Also check agent-heartbeat.jsonl for the agent_hung MetricEvent
        heartbeat_file = tmp_path / ".cognitive-os" / "metrics" / "agent-heartbeat.jsonl"

        # At least one artifact must exist: control.jsonl OR heartbeat with agent_hung
        artifact_found = False
        if control_files:
            for f in control_files:
                try:
                    lines = [l for l in f.read_text().splitlines() if l.strip()]
                    if any('"stop"' in l or "stop" in l for l in lines):
                        artifact_found = True
                        break
                except Exception:
                    pass

        if not artifact_found and heartbeat_file.exists():
            try:
                lines = heartbeat_file.read_text().splitlines()
                if any("agent_hung" in l for l in lines):
                    artifact_found = True
            except Exception:
                pass

        assert artifact_found, (
            f"No control.jsonl or agent_hung heartbeat found. "
            f"agent-bus contents: {list(agent_bus_dir.rglob('*')) if agent_bus_dir.exists() else 'dir missing'}. "
            f"heartbeat exists: {heartbeat_file.exists()}"
        )

    def test_kill_hung_stdout_contains_agent_id(self, tmp_path):
        agent_id = "nonexistent-agent-id"
        result = _run(
            "kill-hung", agent_id,
            env={"COGNITIVE_OS_PROJECT_DIR": str(tmp_path)},
        )
        assert agent_id in result.stdout, (
            f"Expected agent_id in stdout. stdout={result.stdout!r}"
        )


class TestControlAndAnswer:
    def test_control_writes_interrupt_sentinel_without_valkey(self, tmp_path):
        agent_id = "agent-control-1"
        result = _run(
            "control", agent_id, "stop",
            env={
                "COGNITIVE_OS_PROJECT_DIR": str(tmp_path),
                "VALKEY_URL": "redis://localhost:1",
                "COS_AGENT_BUS_FORCE_FALLBACK": "1",
            },
        )
        assert result.returncode == 0, result.stderr
        assert "control: stop" in result.stdout
        agent_dir = tmp_path / ".cognitive-os" / "agent-bus" / agent_id
        assert (agent_dir / "control.jsonl").exists()
        assert (agent_dir / "interrupt").exists()
        assert "stop" in (agent_dir / "interrupt").read_text()

    def test_answer_writes_fallback_answer_jsonl(self, tmp_path):
        agent_id = "agent-answer-1"
        result = _run(
            "answer", agent_id, "use port 8080", "ship it", "--round", "2",
            env={
                "COGNITIVE_OS_PROJECT_DIR": str(tmp_path),
                "VALKEY_URL": "redis://localhost:1",
                "COS_AGENT_BUS_FORCE_FALLBACK": "1",
            },
        )
        assert result.returncode == 0, result.stderr
        answer = tmp_path / ".cognitive-os" / "agent-bus" / agent_id / "answer.jsonl"
        rows = [json.loads(line) for line in answer.read_text().splitlines() if line.strip()]
        assert rows[-1]["answers"] == ["use port 8080", "ship it"]
        assert rows[-1]["round"] == 2


def test_run_wires_orchestrator_subscriber_directly() -> None:
    text = ORCHESTRATOR.read_text(encoding="utf-8")
    assert "from lib.agent_bus import OrchestratorSubscriber" in text
    assert "orchestrator_subscriber = OrchestratorSubscriber" in text
    assert "orchestrator_subscriber.subscribe_agent(agent_id)" in text
