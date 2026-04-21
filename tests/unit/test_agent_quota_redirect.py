"""Unit tests for ADR-056 Level 2 — auto-redirect with block.

Covers both the Python protocol library (lib.agent_redirect_protocol)
and the shell hook (hooks/agent-quota-redirect.sh). The hook is exercised
by invoking it as a subprocess with controlled env + stdin + fixture
metrics dir, so we never touch the live .cognitive-os/metrics tree.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
HOOK = REPO / "hooks" / "agent-quota-redirect.sh"

# Make lib importable for direct library tests.
sys.path.insert(0, str(REPO))
from lib.agent_redirect_protocol import (  # noqa: E402
    REASON_QUOTA_PRESSURE,
    REASON_RATE_LIMIT,
    build_redirect_message,
    format_orchestrator_command,
    parse_redirect_message,
)


# ───────────────────────── library tests ──────────────────────────────

def test_build_redirect_message_stable_format():
    msg = build_redirect_message(REASON_QUOTA_PRESSURE, 0.85, "do a thing")
    lines = msg.strip().split("\n")
    assert len(lines) == 2
    assert lines[0] == "AGENT_REDIRECT: reason=quota_pressure pressure=0.85"
    assert lines[1].startswith("SUGGESTED_COMMAND: uv run python3 scripts/orchestrator.py run")
    assert "--providers qwen,claude" in lines[1]


def test_build_redirect_rejects_invalid_reason():
    with pytest.raises(ValueError):
        build_redirect_message("bogus_reason", 0.9, "x")


def test_build_redirect_rejects_out_of_range_pressure():
    with pytest.raises(ValueError):
        build_redirect_message(REASON_RATE_LIMIT, 1.5, "x")
    with pytest.raises(ValueError):
        build_redirect_message(REASON_RATE_LIMIT, -0.1, "x")


def test_parse_redirect_message_round_trip():
    original = build_redirect_message(REASON_RATE_LIMIT, 0.92, "analyse the repo")
    parsed = parse_redirect_message(original)
    assert parsed is not None
    assert parsed["reason"] == "rate_limit"
    assert parsed["pressure"] == pytest.approx(0.92)
    assert "scripts/orchestrator.py run" in parsed["command"]
    assert "--providers qwen,claude" in parsed["command"]


def test_parse_returns_none_on_malformed_input():
    assert parse_redirect_message("") is None
    assert parse_redirect_message("just some noise\nno redirect here") is None
    # Missing the SUGGESTED_COMMAND line.
    assert parse_redirect_message("AGENT_REDIRECT: reason=quota_pressure pressure=0.80") is None


def test_parse_tolerates_surrounding_stderr_noise():
    noise_before = "[hook-runtime] elapsed=12ms\n"
    noise_after = "\nsome other log line\n"
    block = build_redirect_message(REASON_QUOTA_PRESSURE, 0.80, "hello")
    combined = noise_before + block + noise_after
    parsed = parse_redirect_message(combined)
    assert parsed is not None
    assert parsed["reason"] == "quota_pressure"


def test_format_orchestrator_command_shell_quotes_unsafe_chars():
    """Backticks, $, !, and newlines must be neutralised by shlex."""
    nasty_prompt = "rm -rf / ; echo `whoami` $HOME\n!!"
    cmd = format_orchestrator_command(nasty_prompt)
    # Must be safely quoted: shlex.quote wraps in single quotes and
    # escapes any embedded single quotes. Dangerous chars must not appear
    # outside the quoted region.
    parts = shlex.split(cmd)
    # Find --task argument and its value.
    idx = parts.index("--task")
    assert parts[idx + 1] == nasty_prompt  # round-trips intact


def test_format_orchestrator_command_includes_model_hint():
    cmd = format_orchestrator_command("hello", model_hint="sonnet")
    assert "--model sonnet" in cmd


# ───────────────────────── hook subprocess tests ──────────────────────

def _make_env(project_dir: Path, extra: dict | None = None) -> dict:
    """Build a clean env for hook subprocess runs.

    IMPORTANT: we don't copy PYTEST_CURRENT_TEST into the child, because
    one of the hook's bypass tests needs to exercise the non-bypass path.
    Callers that want the pytest-bypass behaviour set PYTEST_CURRENT_TEST
    explicitly in `extra`.
    """
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", "/tmp"),
        "CLAUDE_PROJECT_DIR": str(project_dir),
        # Strip CI and PYTEST_CURRENT_TEST by default so default hook
        # behaviour (non-bypass) can be tested.
    }
    if extra:
        env.update(extra)
    # Preserve UV-related env if available (uv needs them).
    for key in ("XDG_CACHE_HOME", "UV_CACHE_DIR", "LANG", "LC_ALL"):
        if key in os.environ:
            env.setdefault(key, os.environ[key])
    return env


def _seed_rate_limit_events(metrics_dir: Path, count: int, age_seconds: int = 30):
    """Append `count` rate-limit events aged `age_seconds` into the JSONL."""
    metrics_dir.mkdir(parents=True, exist_ok=True)
    rl_file = metrics_dir / "rate-limit-events.jsonl"
    ts_epoch = time.time() - age_seconds
    ts_iso = datetime.fromtimestamp(ts_epoch, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with rl_file.open("a") as fh:
        for _ in range(count):
            fh.write(json.dumps({"ts": ts_iso, "session_id": "t", "match": "out of extra usage"}) + "\n")


def _run_hook(project_dir: Path, env_extra: dict, stdin_payload: str = "") -> subprocess.CompletedProcess:
    env = _make_env(project_dir, env_extra)
    return subprocess.run(
        ["bash", str(HOOK)],
        input=stdin_payload,
        env=env,
        cwd=str(project_dir),
        capture_output=True,
        text=True,
        timeout=30,
    )


def _mk_project(tmp_path: Path) -> Path:
    """Create a minimal fake project dir with lib/ symlinks to the real repo.

    The hook imports lib.quota_pressure and lib.agent_redirect_protocol
    relative to CLAUDE_PROJECT_DIR. We symlink just the lib/ dir so the
    hook finds agent_redirect_protocol while quota_pressure remains
    absent (exercising the stub fallback).

    We also copy hooks/ reference (not strictly needed — the hook runs
    with absolute path).
    """
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "lib").symlink_to(REPO / "lib")
    (proj / ".cognitive-os" / "metrics").mkdir(parents=True)
    return proj


AGENT_INPUT = json.dumps({
    "tool_name": "Agent",
    "tool_input": {"prompt": "analyse the repo and summarise the auth module"},
})


def test_hook_noop_when_opt_in_not_set(tmp_path):
    proj = _mk_project(tmp_path)
    # Seed high pressure to prove we would block if opt-in were set.
    _seed_rate_limit_events(proj / ".cognitive-os" / "metrics", count=3, age_seconds=30)
    result = _run_hook(proj, env_extra={}, stdin_payload=AGENT_INPUT)
    assert result.returncode == 0, f"stderr={result.stderr}"
    # No AGENT_REDIRECT block on stdout or stderr.
    assert "AGENT_REDIRECT" not in (result.stdout + result.stderr)


def test_hook_blocks_on_recent_rate_limit_when_opted_in(tmp_path):
    proj = _mk_project(tmp_path)
    _seed_rate_limit_events(proj / ".cognitive-os" / "metrics", count=2, age_seconds=30)
    result = _run_hook(
        proj,
        env_extra={"COS_AUTO_REDIRECT_AGENT": "1"},
        stdin_payload=AGENT_INPUT,
    )
    assert result.returncode == 2, f"stdout={result.stdout} stderr={result.stderr}"
    parsed = parse_redirect_message(result.stderr)
    assert parsed is not None, f"unparseable stderr: {result.stderr!r}"
    # Either quota_pressure or rate_limit is acceptable — recent events
    # drive pressure above 0.7 via the stub, so quota_pressure is
    # actually the more likely reason code. Both are valid for this
    # scenario.
    assert parsed["reason"] in {"quota_pressure", "rate_limit"}
    assert parsed["pressure"] > 0.7


def test_hook_bypasses_when_ci_set(tmp_path):
    proj = _mk_project(tmp_path)
    _seed_rate_limit_events(proj / ".cognitive-os" / "metrics", count=3, age_seconds=30)
    result = _run_hook(
        proj,
        env_extra={"COS_AUTO_REDIRECT_AGENT": "1", "CI": "1"},
        stdin_payload=AGENT_INPUT,
    )
    assert result.returncode == 0
    assert "AGENT_REDIRECT" not in result.stderr


def test_hook_bypasses_when_pytest_current_test_set(tmp_path):
    proj = _mk_project(tmp_path)
    _seed_rate_limit_events(proj / ".cognitive-os" / "metrics", count=3, age_seconds=30)
    result = _run_hook(
        proj,
        env_extra={
            "COS_AUTO_REDIRECT_AGENT": "1",
            "PYTEST_CURRENT_TEST": "test_mod::test_x (call)",
        },
        stdin_payload=AGENT_INPUT,
    )
    assert result.returncode == 0
    assert "AGENT_REDIRECT" not in result.stderr


def test_hook_bypasses_when_hard_killswitch_set(tmp_path):
    proj = _mk_project(tmp_path)
    _seed_rate_limit_events(proj / ".cognitive-os" / "metrics", count=3, age_seconds=30)
    result = _run_hook(
        proj,
        env_extra={
            "COS_AUTO_REDIRECT_AGENT": "1",
            "COS_DISABLE_AGENT_REDIRECT": "1",
        },
        stdin_payload=AGENT_INPUT,
    )
    assert result.returncode == 0
    assert "AGENT_REDIRECT" not in result.stderr


def test_hook_noop_when_no_rate_limit_events(tmp_path):
    """Opt-in enabled but pressure is zero — should not block."""
    proj = _mk_project(tmp_path)
    # Note: no rate-limit events seeded.
    result = _run_hook(
        proj,
        env_extra={"COS_AUTO_REDIRECT_AGENT": "1"},
        stdin_payload=AGENT_INPUT,
    )
    assert result.returncode == 0
    assert "AGENT_REDIRECT" not in result.stderr


def test_hook_ignores_old_rate_limit_events(tmp_path):
    """Events older than the 5-min window must not trigger a block."""
    proj = _mk_project(tmp_path)
    _seed_rate_limit_events(proj / ".cognitive-os" / "metrics", count=5, age_seconds=3600)
    result = _run_hook(
        proj,
        env_extra={"COS_AUTO_REDIRECT_AGENT": "1"},
        stdin_payload=AGENT_INPUT,
    )
    assert result.returncode == 0, f"stderr={result.stderr}"
    assert "AGENT_REDIRECT" not in result.stderr


def test_hook_emits_jsonl_event_on_block(tmp_path):
    proj = _mk_project(tmp_path)
    _seed_rate_limit_events(proj / ".cognitive-os" / "metrics", count=2, age_seconds=30)
    result = _run_hook(
        proj,
        env_extra={"COS_AUTO_REDIRECT_AGENT": "1"},
        stdin_payload=AGENT_INPUT,
    )
    assert result.returncode == 2
    events_file = proj / ".cognitive-os" / "metrics" / "agent-redirect.jsonl"
    assert events_file.exists(), "hook did not write agent-redirect.jsonl"
    events = [json.loads(line) for line in events_file.read_text().splitlines() if line.strip()]
    assert len(events) >= 1
    last = events[-1]
    assert last["decision"] == "block"
    assert last["reason"] in {"quota_pressure", "rate_limit"}
    # pressure stringified but should be a valid float.
    float(last["pressure"])


def test_hook_emits_jsonl_event_on_bypass(tmp_path):
    proj = _mk_project(tmp_path)
    _seed_rate_limit_events(proj / ".cognitive-os" / "metrics", count=2, age_seconds=30)
    result = _run_hook(
        proj,
        env_extra={
            "COS_AUTO_REDIRECT_AGENT": "1",
            "COS_DISABLE_AGENT_REDIRECT": "1",
        },
        stdin_payload=AGENT_INPUT,
    )
    assert result.returncode == 0
    events_file = proj / ".cognitive-os" / "metrics" / "agent-redirect.jsonl"
    assert events_file.exists()
    events = [json.loads(line) for line in events_file.read_text().splitlines() if line.strip()]
    # Most recent event is the bypass.
    assert events[-1]["decision"] == "bypass"
    assert "killswitch" in events[-1]["reason"]


def test_hook_suggested_command_contains_original_prompt(tmp_path):
    """The SUGGESTED_COMMAND line must embed the original prompt shell-quoted."""
    proj = _mk_project(tmp_path)
    _seed_rate_limit_events(proj / ".cognitive-os" / "metrics", count=2, age_seconds=30)
    nasty_prompt = "do X && rm -rf / ; echo `pwd`"
    payload = json.dumps({"tool_name": "Agent", "tool_input": {"prompt": nasty_prompt}})
    result = _run_hook(
        proj,
        env_extra={"COS_AUTO_REDIRECT_AGENT": "1"},
        stdin_payload=payload,
    )
    assert result.returncode == 2, f"stderr={result.stderr}"
    parsed = parse_redirect_message(result.stderr)
    assert parsed is not None
    # Round-trip the command through shlex and verify the prompt survives.
    tokens = shlex.split(parsed["command"])
    idx = tokens.index("--task")
    assert tokens[idx + 1] == nasty_prompt
