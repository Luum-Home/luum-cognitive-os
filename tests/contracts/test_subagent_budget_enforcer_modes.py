# SCOPE: both
"""Two-mode contract for ADR-311 subagent budget enforcement.

Why this file exists
--------------------
`hooks/subagent-budget-enforcer.sh` is registered on `PostToolUse` only
(one entry, `matcher: ""`). A `PostToolUse` `exit 2` runs *after* the tool
already executed: the result is discarded, the file is already written, the
command already ran. 50 real `exit 2` in `hook-timing.jsonl` and 95 `block`
rows in the hook's own ledger prevented exactly zero calls.

The fix splits the hook in two modes over the same script:

* ``count``   — ``PostToolUse``. Increments the per-``(session_id, agent_id)``
  counter and writes telemetry. **Never exits 2.**
* ``enforce`` — ``PreToolUse``. *Reads* the counter without mutating it and
  blocks the call that would exceed the budget. Here ``exit 2`` cancels the
  call before it runs.

Mode resolution order: ``COS_SUBAGENT_BUDGET_MODE`` > payload
``hook_event_name`` > ``COGNITIVE_OS_HOOK_EVENT`` > ``count`` (counting is
the safe default: a hook that guesses wrong and counts is harmless, one that
guesses wrong and enforces blocks the fleet).

Status of the markers below
---------------------------
Tests that depend on the *patched* hook carry ``xfail(strict=True)``. They
fail today on purpose and turn into a hard failure the moment the hook patch
lands — that is the ratchet that forces the marker to be removed together
with the patch, instead of leaving a green test that proves nothing. The
design and the exact patches are in
``docs/06-Daily/reports/subagent-budget-enforcer-architecture-2026-08-15.md``.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / "hooks" / "subagent-budget-enforcer.sh"

PENDING = "ADR-311 mode split not applied to hooks/subagent-budget-enforcer.sh yet"


def _run(
    tmp_path: Path,
    payload: dict,
    env_extra: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "COGNITIVE_OS_PROJECT_DIR": str(tmp_path),
            "COGNITIVE_OS_SESSION_ID": "session-a",
            "COS_SUBAGENT_TOOL_CALL_BUDGET": "2",
            # Identity must come from the payload, exactly as the harness
            # delivers it. The timing wrapper only derives
            # COGNITIVE_OS_HOOK_AGENT_ID for SessionStart/SubagentStart, so on
            # tool events these are empty strings in production.
            "COGNITIVE_OS_HOOK_AGENT_ID": "",
            "COGNITIVE_OS_AGENT_ID": "",
            "CLAUDE_AGENT_ID": "",
            "CODEX_AGENT_ID": "",
            "COS_AGENT_ID": "",
            "COGNITIVE_OS_SESSION_KIND": "",
        }
    )
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=tmp_path,
        env=env,
        timeout=20,
        check=False,
    )


def _post(tool_input: dict | None = None) -> dict:
    """A PostToolUse payload as Claude Code delivers it for a subagent."""
    return {
        "hook_event_name": "PostToolUse",
        "session_id": "session-a",
        "agent_id": "a1b2c3d4e5f60718a",
        "transcript_path": "/x/projects/p/session-a/subagents/agent-a1b2c3d4e5f60718a.jsonl",
        "tool_name": "Bash",
        "tool_input": tool_input or {"command": "echo ok"},
        "tool_response": {"stdout": "ok"},
    }


def _pre(tool_input: dict | None = None) -> dict:
    """A PreToolUse payload for the same subagent."""
    payload = _post(tool_input)
    payload["hook_event_name"] = "PreToolUse"
    payload.pop("tool_response", None)
    return payload


def _counters(tmp_path: Path) -> list[Path]:
    root = tmp_path / ".cognitive-os" / "sessions" / "session-a"
    return sorted(p for p in root.glob("subagent-tool-calls-*")) if root.exists() else []


def _ledger(tmp_path: Path) -> list[dict]:
    path = tmp_path / ".cognitive-os" / "metrics" / "subagent-budget-enforcer.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


# ── count mode (PostToolUse) ────────────────────────────────────────────────


@pytest.mark.xfail(reason=PENDING, strict=True)
def test_count_mode_never_blocks_even_past_budget(tmp_path: Path) -> None:
    """A PostToolUse exit 2 cannot prevent anything; it only discards a result."""
    for _ in range(5):
        result = _run(tmp_path, _post())
        assert result.returncode == 0, result.stderr

    actions = [row["action"] for row in _ledger(tmp_path)]
    assert "block" not in actions, f"count mode must never block, got {actions}"


def test_count_mode_counts_every_call(tmp_path: Path) -> None:
    for _ in range(4):
        _run(tmp_path, _post())

    counters = _counters(tmp_path)
    assert len(counters) == 1, counters
    assert _read_count(counters[0]) == 4


def test_count_mode_warns_at_budget_without_blocking(tmp_path: Path) -> None:
    _run(tmp_path, _post())
    second = _run(tmp_path, _post())

    assert second.returncode == 0
    assert "WARN" in second.stderr
    assert [row["action"] for row in _ledger(tmp_path)][-1] == "warn"


# ── enforce mode (PreToolUse) ───────────────────────────────────────────────


@pytest.mark.xfail(reason=PENDING, strict=True)
def test_enforce_mode_does_not_mutate_the_counter(tmp_path: Path) -> None:
    """Enforce reads. If it also counted, every call would cost two."""
    _run(tmp_path, _post())
    before = _read_count(_counters(tmp_path)[0])

    _run(tmp_path, _pre())
    _run(tmp_path, _pre())

    assert _read_count(_counters(tmp_path)[0]) == before


@pytest.mark.xfail(reason=PENDING, strict=True)
def test_budget_n_means_exactly_n_calls(tmp_path: Path) -> None:
    """With BUDGET=2 the subagent consumes 2 calls and the 3rd is prevented."""
    # call 1: pre allows, post counts -> 1
    assert _run(tmp_path, _pre()).returncode == 0
    assert _run(tmp_path, _post()).returncode == 0
    # call 2: pre allows (1 < 2), post counts -> 2
    assert _run(tmp_path, _pre()).returncode == 0
    assert _run(tmp_path, _post()).returncode == 0
    # call 3: pre blocks BEFORE the tool runs
    third = _run(tmp_path, _pre())
    assert third.returncode == 2, third.stderr
    assert "BLOCK" in third.stderr
    assert "ESCALATION:" in third.stderr

    assert _read_count(_counters(tmp_path)[0]) == 2, "a blocked call must not consume budget"


@pytest.mark.xfail(reason=PENDING, strict=True)
def test_enforce_allows_when_no_counter_exists(tmp_path: Path) -> None:
    """Fail-open on absence: absence is the legitimate state of call #1.

    Fail-closed here would block every fresh subagent on its first tool call.
    The gate's integrity lives on the write side (count mode must not fail
    silently), not on the read side.
    """
    result = _run(tmp_path, _pre())

    assert result.returncode == 0, result.stderr
    assert _counters(tmp_path) == [], "enforce must not create the counter"


@pytest.mark.xfail(reason=PENDING, strict=True)
def test_enforce_records_degraded_when_counter_is_unreadable(tmp_path: Path) -> None:
    """Fail-open, but never silently: a lost gate must be observable."""
    _run(tmp_path, _post())
    counter = _counters(tmp_path)[0]
    counter.write_text("not-a-number")

    result = _run(tmp_path, _pre())

    assert result.returncode == 0
    assert any(row["action"] == "degraded" for row in _ledger(tmp_path))


@pytest.mark.xfail(reason=PENDING, strict=True)
def test_escalation_grace_is_bounded_and_recorded(tmp_path: Path) -> None:
    """An unbounded `ESCALATION:` substring pass is a hole, not an escape hatch.

    Production evidence: one agent used the pass 53 times and reached 96 tool
    calls under a budget of 50.
    """
    for _ in range(3):
        _run(tmp_path, _post())

    escalation = _run(tmp_path, _pre({"command": "printf 'ESCALATION: diagnosis + next safe action'"}))
    assert escalation.returncode == 0, escalation.stderr

    second = _run(tmp_path, _pre({"command": "printf 'ESCALATION: again'"}))
    assert second.returncode == 2, "the grace is one-time, not a permanent bypass"


def test_bypass_without_reason_blocks_in_enforce(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        _pre(),
        {"COS_ALLOW_SUBAGENT_BUDGET_BYPASS": "1", "COS_SUBAGENT_BUDGET_BYPASS_REASON": ""},
    )

    assert result.returncode == 2
    assert "COS_SUBAGENT_BUDGET_BYPASS_REASON" in result.stderr


def test_bypass_with_reason_allows_and_audits(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        _pre(),
        {
            "COS_ALLOW_SUBAGENT_BUDGET_BYPASS": "1",
            "COS_SUBAGENT_BUDGET_BYPASS_REASON": "operator-approved sweep",
        },
    )

    assert result.returncode == 0
    assert any("bypass:" in row["reason"] for row in _ledger(tmp_path))


# ── mode resolution ─────────────────────────────────────────────────────────


@pytest.mark.xfail(reason=PENDING, strict=True)
def test_mode_defaults_to_count_without_any_event_signal(tmp_path: Path) -> None:
    """No event anywhere -> count. Guessing `enforce` would block blind."""
    payload = _post()
    payload.pop("hook_event_name")

    for _ in range(5):
        assert _run(tmp_path, payload, {"COGNITIVE_OS_HOOK_EVENT": ""}).returncode == 0


@pytest.mark.xfail(reason=PENDING, strict=True)
def test_env_override_wins_over_payload_event(tmp_path: Path) -> None:
    for _ in range(3):
        _run(tmp_path, _post())

    before = _read_count(_counters(tmp_path)[0])

    forced = _run(tmp_path, _post(), {"COS_SUBAGENT_BUDGET_MODE": "enforce"})

    assert forced.returncode == 2, "explicit mode must win over hook_event_name"
    assert _read_count(_counters(tmp_path)[0]) == before, "enforce must not count"


@pytest.mark.xfail(reason=PENDING, strict=True)
def test_hook_event_env_resolves_mode_when_payload_lacks_it(tmp_path: Path) -> None:
    payload = _pre()
    payload.pop("hook_event_name")
    for _ in range(3):
        _run(tmp_path, _post())

    before = _read_count(_counters(tmp_path)[0])

    result = _run(tmp_path, payload, {"COGNITIVE_OS_HOOK_EVENT": "PreToolUse"})

    assert result.returncode == 2
    assert _read_count(_counters(tmp_path)[0]) == before, "enforce must not count"


# ── identity: the load-bearing premise of the whole split ───────────────────


def test_orchestrator_payload_is_ignored_and_writes_nothing(tmp_path: Path) -> None:
    """Passes today. The cheap shell bail must not regress it."""
    payload = {
        "hook_event_name": "PostToolUse",
        "session_id": "session-a",
        "transcript_path": "/x/projects/p/session-a.jsonl",
        "tool_name": "Bash",
        "tool_input": {"command": "echo ok"},
    }

    result = _run(tmp_path, payload)

    assert result.returncode == 0, result.stderr
    assert _counters(tmp_path) == []


@pytest.mark.xfail(reason=PENDING, strict=True)
def test_transcript_path_alone_identifies_the_same_agent_as_agent_id(tmp_path: Path) -> None:
    """Pre and Post must agree on the key even if one channel lacks agent_id.

    Subagent transcripts are `.../subagents/agent-<agent_id>.jsonl`, verified
    against production: transcript `agent-afbce854e9979dd85.jsonl` matches the
    ledger's `agent_id: afbce854e9979dd85`. Deriving the id from the basename
    makes both channels produce one counter instead of two.
    """
    with_id = _post()
    without_id = _post()
    without_id.pop("agent_id")

    _run(tmp_path, with_id)
    _run(tmp_path, without_id)

    counters = _counters(tmp_path)
    assert len(counters) == 1, f"expected one shared counter, got {counters}"
    assert counters[0].name.endswith("a1b2c3d4e5f60718a")
    assert _read_count(counters[0]) == 2


def test_parallel_calls_do_not_lose_increments(tmp_path: Path) -> None:
    """Regression guard for the shared counter under concurrent writers.

    Passes today: 12/30/60 concurrent invocations lost 0 increments, because
    the ~264 ms python startup dwarfs the read-modify-write critical section
    and desynchronises the writers. Kept so a future "optimisation" that makes
    the hook cheap does not silently reintroduce lost updates."""
    procs = [
        subprocess.Popen(
            ["bash", str(HOOK)],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
            cwd=tmp_path,
            env={
                **os.environ,
                "COGNITIVE_OS_PROJECT_DIR": str(tmp_path),
                "COGNITIVE_OS_SESSION_ID": "session-a",
                "COS_SUBAGENT_TOOL_CALL_BUDGET": "100",
                "COGNITIVE_OS_HOOK_AGENT_ID": "",
                "COGNITIVE_OS_SESSION_KIND": "",
            },
        )
        for _ in range(12)
    ]
    for proc in procs:
        proc.communicate(json.dumps(_post()))

    assert _read_count(_counters(tmp_path)[0]) == 12


def _read_count(path: Path) -> int:
    """Counter reader tolerant of both representations (digits or ticks)."""
    raw = path.read_bytes()
    text = raw.decode("utf-8", "ignore").strip()
    if text.isdigit():
        return int(text)
    return len(raw)
