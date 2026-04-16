"""Behavioral tests for ADR-022 prompt-type hooks.

Verifies that the three Haiku-evaluated advisory hooks:
  - hooks/prompt-quality-llm.sh
  - hooks/completeness-check-llm.sh
  - hooks/confidence-gate-llm.sh

emit a valid type:"prompt" hookSpecificOutput JSON envelope when given
real Agent input, and that they degrade gracefully (exit 0, no output, no
block) when:
  - stdin is empty
  - the tool is not Agent
  - the agent prompt is missing/null
  - jq is not on PATH (simulated by an empty PATH)

These are behavioral, not snapshot tests — they assert the contract the
parent orchestrator depends on, not the exact wording of the system prompt.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.behavior]


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
HOOKS_DIR = PROJECT_ROOT / "hooks"

PROMPT_QUALITY_LLM = "prompt-quality-llm.sh"
COMPLETENESS_LLM = "completeness-check-llm.sh"
CONFIDENCE_LLM = "confidence-gate-llm.sh"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(
    hook_name: str,
    stdin: "str | None" = None,
    env_overrides: "dict | None" = None,
    timeout: int = 10,
) -> subprocess.CompletedProcess:
    hook_path = HOOKS_DIR / hook_name
    if not hook_path.exists():
        pytest.skip(f"Hook {hook_name} not present at {hook_path}")

    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)

    return subprocess.run(
        ["bash", str(hook_path)],
        input=stdin if stdin is not None else "",
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
    )


def _agent_input(prompt: str) -> str:
    return json.dumps({"tool_name": "Agent", "tool_input": {"prompt": prompt}})


def _agent_response_input(result: str) -> str:
    return json.dumps({"tool_name": "Agent", "tool_result": result})


def _parse_hook_envelope(stdout: str) -> dict:
    """Parse the hook output and validate it's a type:'prompt' envelope.

    Returns the inner hookSpecificOutput dict.
    """
    assert stdout.strip(), "hook produced no output"
    try:
        obj = json.loads(stdout)
    except json.JSONDecodeError as e:
        raise AssertionError(f"hook output is not valid JSON: {stdout!r}") from e

    assert "hookSpecificOutput" in obj, f"missing hookSpecificOutput: {obj}"
    inner = obj["hookSpecificOutput"]
    assert inner.get("type") == "prompt", f"type must be 'prompt': {inner}"
    assert inner.get("model"), "must specify a model"
    assert inner.get("system"), "must specify a system prompt"
    assert inner.get("prompt"), "must specify a user prompt"
    assert inner.get("decision") == "advisory", "must be advisory"
    assert inner.get("hookEventName") in (
        "PreToolUse",
        "PostToolUse",
    ), f"unexpected hookEventName: {inner}"
    return inner


# ---------------------------------------------------------------------------
# 1. prompt-quality-llm.sh — emits valid type:"prompt" JSON
# ---------------------------------------------------------------------------


def test_prompt_quality_llm_emits_valid_prompt_envelope():
    """Real Agent prompt → emits type:'prompt' JSON for Haiku evaluation."""
    stdin = _agent_input(
        "Refactor internal/payments/handler.go to extract the fee calculation "
        "into a new package. Acceptance: all 4 endpoints still pass `go test ./...`."
    )
    result = _run(PROMPT_QUALITY_LLM, stdin=stdin)

    assert result.returncode == 0, f"hook must exit 0; stderr={result.stderr!r}"
    inner = _parse_hook_envelope(result.stdout)

    # The hook routes to Haiku for cost/latency reasons (ADR-022)
    assert "haiku" in inner["model"].lower()
    # The user prompt sent to Haiku must include the original agent prompt
    assert "internal/payments/handler.go" in inner["prompt"]
    # PreToolUse — fires before the Agent call dispatches
    assert inner["hookEventName"] == "PreToolUse"
    assert inner.get("label") == "prompt-quality-llm"


def test_prompt_quality_llm_truncates_oversized_prompt():
    """Prompts > 4 KB are truncated to keep the Haiku call cheap."""
    big_prompt = "Refactor X. " + ("padding " * 2000)  # ~16 KB
    stdin = _agent_input(big_prompt)
    result = _run(PROMPT_QUALITY_LLM, stdin=stdin)

    assert result.returncode == 0
    inner = _parse_hook_envelope(result.stdout)
    assert len(inner["prompt"]) <= 4000, "user prompt must be truncated to 4 KB"


# ---------------------------------------------------------------------------
# 2. completeness-check-llm.sh — emits valid JSON
# ---------------------------------------------------------------------------


def test_completeness_check_llm_emits_valid_prompt_envelope():
    """Vague Agent prompt → emits type:'prompt' JSON asking Haiku for verdict."""
    stdin = _agent_input("rebrand everything across the entire codebase")
    result = _run(COMPLETENESS_LLM, stdin=stdin)

    assert result.returncode == 0, f"hook must exit 0; stderr={result.stderr!r}"
    inner = _parse_hook_envelope(result.stdout)

    assert "haiku" in inner["model"].lower()
    assert inner["hookEventName"] == "PreToolUse"
    assert inner.get("label") == "completeness-check-llm"
    # The system prompt must instruct Haiku on the JSON schema we expect back
    assert "complete" in inner["system"].lower()


def test_completeness_check_llm_passes_through_well_formed_prompt():
    """Even an exhaustive prompt is sent to Haiku — Haiku decides verdict."""
    stdin = _agent_input(
        "Migrate these 3 endpoints in cmd/api/router.go: /v1/users, /v1/orders, "
        "/v1/health. Acceptance: `go test ./cmd/api/...` exits 0."
    )
    result = _run(COMPLETENESS_LLM, stdin=stdin)

    assert result.returncode == 0
    inner = _parse_hook_envelope(result.stdout)
    assert "/v1/users" in inner["prompt"]


# ---------------------------------------------------------------------------
# 3. confidence-gate-llm.sh — emits valid JSON for agent responses
# ---------------------------------------------------------------------------


def test_confidence_gate_llm_emits_valid_prompt_envelope():
    """Agent response with a Trust Report → emits type:'prompt' JSON."""
    response = (
        "Done. Migrated 3 endpoints. "
        "Trust Report: Score 78/100. Evidence: tests pass. "
        "Uncertainties: did not exercise edge case X."
    )
    stdin = _agent_response_input(response)
    result = _run(CONFIDENCE_LLM, stdin=stdin)

    assert result.returncode == 0
    inner = _parse_hook_envelope(result.stdout)

    assert "haiku" in inner["model"].lower()
    assert inner["hookEventName"] == "PostToolUse"
    assert inner.get("label") == "confidence-gate-llm"
    assert "trust report" in inner["system"].lower()


def test_confidence_gate_llm_handles_task_and_delegate_tools():
    """Confidence gate also fires for task and delegate tools (not just Agent)."""
    for tool in ("task", "delegate"):
        stdin = json.dumps({"tool_name": tool, "tool_result": "Done. Score 85/100."})
        result = _run(CONFIDENCE_LLM, stdin=stdin)
        assert result.returncode == 0, f"failed for tool={tool}"
        inner = _parse_hook_envelope(result.stdout)
        assert inner["hookEventName"] == "PostToolUse"


# ---------------------------------------------------------------------------
# 4. Graceful degradation — never block, never noisy
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "hook",
    [PROMPT_QUALITY_LLM, COMPLETENESS_LLM, CONFIDENCE_LLM],
)
def test_hook_exits_silently_on_empty_stdin(hook: str):
    """Empty stdin → exit 0, no output, no block."""
    result = _run(hook, stdin="")
    assert result.returncode == 0, f"hook must exit 0 on empty stdin"
    assert result.stdout.strip() == "", "hook must produce no output on empty stdin"


@pytest.mark.parametrize(
    "hook",
    [PROMPT_QUALITY_LLM, COMPLETENESS_LLM, CONFIDENCE_LLM],
)
def test_hook_exits_silently_on_wrong_tool(hook: str):
    """Tool != Agent/task/delegate → exit 0, no output."""
    stdin = json.dumps({"tool_name": "Read", "tool_input": {"file_path": "/etc/hosts"}})
    result = _run(hook, stdin=stdin)
    assert result.returncode == 0
    assert result.stdout.strip() == "", "hook must not emit a prompt for non-target tool"


@pytest.mark.parametrize(
    "hook",
    [PROMPT_QUALITY_LLM, COMPLETENESS_LLM],
)
def test_pre_hook_exits_silently_on_missing_prompt(hook: str):
    """Agent input with no prompt field → exit 0, no output."""
    stdin = json.dumps({"tool_name": "Agent", "tool_input": {}})
    result = _run(hook, stdin=stdin)
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_confidence_gate_llm_exits_silently_on_missing_result():
    """Agent input with no tool_result/tool_response → exit 0, no output."""
    stdin = json.dumps({"tool_name": "Agent"})
    result = _run(CONFIDENCE_LLM, stdin=stdin)
    assert result.returncode == 0
    assert result.stdout.strip() == ""


@pytest.mark.parametrize(
    "hook",
    [PROMPT_QUALITY_LLM, COMPLETENESS_LLM, CONFIDENCE_LLM],
)
def test_hook_degrades_when_jq_unavailable(hook: str, tmp_path):
    """When jq is not on PATH (simulating Haiku/jq unavailable), exit 0 silently.

    This is the contract for advisory hooks per ADR-022: if any dependency
    is missing, the hook MUST NOT block and MUST NOT spam stderr — the
    legacy regex hook is still in place as the safety net.

    To simulate jq being unavailable while keeping bash itself reachable,
    we point PATH at a temp dir that contains symlinks to coreutils
    (date, head, printf, dirname, basename, cat, rm, mkdir, grep) and
    bash, but NO jq.
    """
    # Build a minimal PATH containing everything the hook touches except jq.
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    needed = [
        "bash",
        "cat",
        "head",
        "printf",
        "dirname",
        "basename",
        "grep",
        "echo",
        "command",
        "true",
        "false",
        "date",
        "mkdir",
        "rm",
        "test",
        "[",
    ]
    for name in needed:
        # Resolve via /usr/bin and /bin first; fall back to which
        for src in (f"/usr/bin/{name}", f"/bin/{name}"):
            if os.path.exists(src):
                os.symlink(src, fake_bin / name)
                break

    hook_path = HOOKS_DIR / hook
    if not hook_path.exists():
        pytest.skip(f"Hook {hook} not present at {hook_path}")

    stdin = json.dumps({"tool_name": "Agent", "tool_input": {"prompt": "do X"}})
    # Use absolute path to bash so subprocess can find it regardless of PATH.
    bash_abs = "/bin/bash" if os.path.exists("/bin/bash") else "/usr/bin/bash"

    result = subprocess.run(
        [bash_abs, str(hook_path)],
        input=stdin,
        capture_output=True,
        text=True,
        env={"PATH": str(fake_bin)},
        timeout=10,
    )

    assert result.returncode == 0, (
        f"hook must exit 0 when jq unavailable; "
        f"got rc={result.returncode}, stderr={result.stderr!r}"
    )
    assert result.stdout.strip() == "", (
        "hook must not emit anything when jq is unavailable; "
        f"stdout={result.stdout!r}"
    )
