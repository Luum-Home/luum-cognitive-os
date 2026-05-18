"""Behavioral tests for subagent-input-schema-validator.sh hook (ADR-038 Wave 2).

Verifies that the hook:
  1. Passes silently when no INPUT SCHEMA block is present.
  2. Passes when all required fields are provided in COS_AGENT_PAYLOAD.
  3. Blocks (exit 2 + ESCALATION text) when a required field is missing.
  4. Blocks when a field has the wrong type.
  5. Ignores non-Agent tool launches.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
HOOK_PATH = PROJECT_ROOT / "hooks" / "subagent-input-schema-validator.sh"
LIB_DIR = PROJECT_ROOT / "lib"

# A minimal prompt that declares an INPUT SCHEMA block.
_SCHEMA_PROMPT = """\
You are a sub-agent. Complete the task.

INPUT SCHEMA:
  task_description: str (required) — what to do
  blast_radius: int (optional) — files affected

Do the work now.
"""

_NO_SCHEMA_PROMPT = "You are a sub-agent. Complete the task without any schema."


def _run(
    prompt: str,
    payload: dict | None = None,
    tool_name: str = "Agent",
    extra_env: dict | None = None,
) -> subprocess.CompletedProcess:
    """Execute the hook and return the CompletedProcess."""
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(PROJECT_ROOT)
    env["COGNITIVE_OS_PROJECT_DIR"] = str(PROJECT_ROOT)
    env["COGNITIVE_OS_HOOK_HEARTBEAT"] = "false"
    if payload is not None:
        env["COS_AGENT_PAYLOAD"] = json.dumps(payload)
    elif "COS_AGENT_PAYLOAD" in env:
        del env["COS_AGENT_PAYLOAD"]
    if extra_env:
        env.update(extra_env)

    stdin_json = {
        "tool_name": tool_name,
        "tool_input": {"prompt": prompt},
    }

    return subprocess.run(
        ["bash", str(HOOK_PATH)],
        input=json.dumps(stdin_json),
        capture_output=True,
        text=True,
        env=env,
        timeout=20,
    )


@pytest.mark.skipif(not HOOK_PATH.exists(), reason="Hook not yet deployed")
class TestSubagentInputSchemaValidator:

    def test_no_schema_passes_silently(self):
        """Prompt with no INPUT SCHEMA block must exit 0 without output."""
        result = _run(prompt=_NO_SCHEMA_PROMPT, payload=None)
        assert result.returncode == 0, f"stderr: {result.stderr}"
        # No blocking output expected.
        assert "ESCALATION" not in result.stdout
        assert "BLOCK" not in result.stdout

    def test_valid_payload_passes(self):
        """All required fields present must exit 0."""
        result = _run(
            prompt=_SCHEMA_PROMPT,
            payload={"task_description": "Write tests for the validator hook"},
        )
        assert result.returncode == 0, (
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_missing_required_field_blocks(self):
        """Missing required field must exit 2 and emit ESCALATION to stderr."""
        result = _run(
            prompt=_SCHEMA_PROMPT,
            payload={},  # task_description is required but absent
        )
        assert result.returncode == 2, (
            f"Expected exit 2, got {result.returncode}.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        combined = result.stdout + result.stderr
        assert "ESCALATION" in combined or "BLOCK" in combined, (
            f"Expected escalation text, got: {combined[:500]}"
        )

    def test_type_mismatch_blocks(self):
        """Wrong type for a typed field must exit 2."""
        result = _run(
            prompt=_SCHEMA_PROMPT,
            payload={
                "task_description": "fix bug",
                "blast_radius": "not-an-int",   # declared as int
            },
        )
        # blast_radius is optional so type mismatch must still block.
        assert result.returncode == 2, (
            f"Expected exit 2 for type mismatch, got {result.returncode}.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_non_agent_tool_skipped(self):
        """Non-Agent tool calls must exit 0 even with a schema in prompt."""
        result = _run(
            prompt=_SCHEMA_PROMPT,
            payload={},  # missing required field — but should not matter
            tool_name="Bash",
        )
        assert result.returncode == 0, (
            f"Non-Agent launch should be skipped. stderr: {result.stderr}"
        )
