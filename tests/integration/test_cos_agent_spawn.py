"""Integration test: end-to-end cos-agent spawn via shell invocation (ADR-064).

This test invokes ``bin/cos-agent spawn`` as a subprocess.  LLM dispatch is
stubbed via a minimal Python script that simulates a single-step agent loop
returning a fixed response, so the test never touches the network.

The stub is injected by setting ``_COS_AGENT_STUB_RUNNER=1`` and placing a
``lib/agent_runner.py``-compatible stub on ``PYTHONPATH`` using
``_COS_AGENT_STUB_DIR``.
"""

from __future__ import annotations

import json
import os
import subprocess
import textwrap
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BIN_COS_AGENT = PROJECT_ROOT / "bin" / "cos-agent"


def _stub_runner_source() -> str:
    """Return Python source for a stub agent_runner module."""
    return textwrap.dedent('''\
        """Stub agent_runner for cos-agent integration tests."""
        from dataclasses import dataclass, field, asdict
        from typing import Any, Dict, List, Optional
        from pathlib import Path

        @dataclass
        class AgentResult:
            status: str = "success"
            final_response: str = "stub: hello world"
            events: List[Dict[str, Any]] = field(default_factory=list)
            tokens_used: Dict[str, int] = field(default_factory=dict)
            session_id: str = "stub-session"
            provider: str = "stub"
            model: str = "stub-model"
            iterations: int = 1
            error: str = ""

            def to_dict(self) -> Dict[str, Any]:
                return asdict(self)

        def spawn(prompt, *, model="auto", allowed_tools=None,
                  timeout_s=600, session_id=None, project_dir=None,
                  verbose=False, _run_agent_fn=None):
            return AgentResult(
                final_response=f"stub: {prompt[:80]}",
                status="success",
            )
    ''')


@pytest.fixture()
def stub_lib(tmp_path: Path) -> Path:
    """Create a temporary lib/ directory with a stub agent_runner."""
    lib_dir = tmp_path / "lib"
    lib_dir.mkdir()
    (lib_dir / "__init__.py").write_text("")
    (lib_dir / "agent_runner.py").write_text(_stub_runner_source())
    return tmp_path


def _run_cos_agent(args: list[str], stub_lib: Path, env_overrides: dict | None = None, stdin: str | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    # Prepend stub lib so our stub agent_runner shadows the real one
    env["PYTHONPATH"] = str(stub_lib) + ":" + env.get("PYTHONPATH", "")
    env["COGNITIVE_OS_PROJECT_DIR"] = str(stub_lib)
    env["COGNITIVE_OS_HARNESS"] = "bare_cli"
    env.pop("COS_AGENT_DEPTH", None)
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        ["bash", str(BIN_COS_AGENT)] + args,
        capture_output=True,
        text=True,
        env=env,
        cwd=str(stub_lib),
        input=stdin,
    )


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestCosAgentHelp:
    def test_help_exits_zero(self, stub_lib):
        result = _run_cos_agent(["--help"], stub_lib)
        assert result.returncode == 0
        assert "spawn" in result.stdout.lower() or "spawn" in result.stderr.lower()

    def test_no_args_exits_zero(self, stub_lib):
        result = _run_cos_agent([], stub_lib)
        assert result.returncode == 0


class TestCosAgentSpawn:
    def test_spawn_simple_prompt(self, stub_lib):
        result = _run_cos_agent(["spawn", "--prompt", "echo hello world"], stub_lib)
        assert result.returncode == 0, result.stderr
        assert "hello world" in result.stdout.lower() or "stub" in result.stdout.lower()

    def test_spawn_stdin_prompt(self, stub_lib):
        # The shell script reads stdin when --prompt is "-"
        result = _run_cos_agent(
            ["spawn", "--prompt", "-"], stub_lib, stdin="tell me about stdin"
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip()

    def test_spawn_json_output(self, stub_lib):
        result = _run_cos_agent(["spawn", "--prompt", "test prompt", "--json"], stub_lib)
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert data["status"] == "success"
        assert "final_response" in data

    def test_spawn_with_model_flag(self, stub_lib):
        result = _run_cos_agent(
            ["spawn", "--prompt", "simple task", "--model=haiku"], stub_lib
        )
        assert result.returncode == 0, result.stderr

    def test_spawn_with_tools_flag(self, stub_lib):
        result = _run_cos_agent(
            ["spawn", "--prompt", "list files", "--tools=read_file,glob_files"], stub_lib
        )
        assert result.returncode == 0, result.stderr

    def test_spawn_unknown_subcommand_exits_one(self, stub_lib):
        result = _run_cos_agent(["badcmd", "--prompt", "x"], stub_lib)
        assert result.returncode != 0

    def test_spawn_missing_prompt_exits_nonzero(self, stub_lib):
        result = _run_cos_agent(["spawn"], stub_lib)
        assert result.returncode != 0

    def test_spawn_cos_skill_awareness(self, stub_lib):
        """Verifies cos-agent knows how to pass tool names including cos_skill_run.

        cos_skill_run is not in the default tool set (it's available only when
        bin/cos-skill is installed), but cos-agent must not crash when it's
        passed explicitly via --tools.
        """
        result = _run_cos_agent(
            ["spawn", "--prompt", "run a skill", "--tools=read_file,cos_skill_run"],
            stub_lib,
        )
        # The stub loop doesn't validate tool names; we just check the CLI handles it
        assert result.returncode == 0, result.stderr
