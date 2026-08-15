"""Contract tests for the stdout/stderr byte accounting in hook-timing-wrapper.sh.

hook-timing.jsonl used to record how long a hook took and whether it failed, but
never how much text it pushed into the model context — the second half of the
per-tool-call cost. The wrapper now records stdout_bytes and stderr_bytes.

The wrapper sits on the hot path of every tool call (21 hooks per Bash call in
this repo), so the properties pinned here are the ones that would break every
hook in every session if the measurement regressed: stdout must come out byte
for byte, stderr must still reach stderr, exit codes must survive, and the
measurement must be switchable off.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WRAPPER = ROOT / "scripts" / "hook-timing-wrapper.sh"


def _write_hook(path: Path, body: str) -> None:
    path.write_text("#!/usr/bin/env bash\n" + body, encoding="utf-8")
    path.chmod(0o755)


def _run(tmp_path: Path, event: str, hook: Path, *args: str, **env_extra: str):
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(tmp_path)
    env.pop("COS_HOOK_TIMING_VERBOSE", None)
    env.pop("COS_HOOK_TIMING_FIFO", None)
    env.update(env_extra)
    return subprocess.run(
        ["bash", str(WRAPPER), event, str(hook), *args],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )


def _rows(tmp_path: Path) -> list[dict]:
    path = tmp_path / ".cognitive-os/metrics/hook-timing.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_records_exact_stdout_and_stderr_byte_counts(tmp_path: Path) -> None:
    hook = tmp_path / "chatty-hook.sh"
    _write_hook(hook, "printf 'abcde\\n'\nprintf 'xy\\n' >&2\n")

    result = _run(tmp_path, "PostToolUse", hook)

    assert result.returncode == 0
    assert result.stdout == "abcde\n"
    assert result.stderr == "xy\n"
    row = _rows(tmp_path)[0]
    assert row["stdout_bytes"] == 6
    assert row["stderr_bytes"] == 3


def test_silent_hook_records_zero_without_inventing_output(tmp_path: Path) -> None:
    hook = tmp_path / "silent-hook.sh"
    _write_hook(hook, "exit 0\n")

    result = _run(tmp_path, "PostToolUse", hook)

    assert result.stdout == ""
    assert result.stderr == ""
    row = _rows(tmp_path)[0]
    assert row["stdout_bytes"] == 0
    assert row["stderr_bytes"] == 0


def test_stdout_passthrough_is_byte_exact_for_large_payloads(tmp_path: Path) -> None:
    """PreToolUse additionalContext is a JSON protocol — one lost byte breaks it."""
    hook = tmp_path / "big-hook.sh"
    _write_hook(hook, "for i in $(seq 500); do printf 'line %s with padding\\n' \"$i\"; done\n")

    result = _run(tmp_path, "PreToolUse", hook)

    expected = "".join(f"line {i} with padding\n" for i in range(1, 501))
    assert result.stdout == expected
    row = _rows(tmp_path)[0]
    assert row["stdout_bytes"] == len(expected.encode("utf-8"))


def test_trailing_newline_is_preserved_and_absence_too(tmp_path: Path) -> None:
    no_newline = tmp_path / "nonewline-hook.sh"
    _write_hook(no_newline, "printf 'no-trailing-newline'\n")
    result = _run(tmp_path, "PreToolUse", no_newline)
    assert result.stdout == "no-trailing-newline"
    assert _rows(tmp_path)[0]["stdout_bytes"] == 19


def test_multibyte_output_is_counted_in_bytes_not_characters(tmp_path: Path) -> None:
    hook = tmp_path / "utf8-hook.sh"
    _write_hook(hook, "printf 'ñé\\n'\n")

    result = _run(tmp_path, "PostToolUse", hook)

    assert result.stdout == "ñé\n"
    # 2 two-byte code points + newline = 5 bytes, not 3 characters.
    assert _rows(tmp_path)[0]["stdout_bytes"] == 5


def test_exit_code_and_args_survive_the_capture(tmp_path: Path) -> None:
    hook = tmp_path / "blocking-hook.sh"
    _write_hook(hook, 'echo "ARGS=$*"\necho blocked >&2\nexit 2\n')

    result = _run(tmp_path, "PreToolUse", hook, "alpha", "beta")

    assert result.returncode == 2
    assert result.stdout == "ARGS=alpha beta\n"
    assert "blocked" in result.stderr
    row = _rows(tmp_path)[0]
    assert row["exit_code"] == 2
    assert row["execution_status"] == "error"
    assert row["stdout_bytes"] == 16


def test_stdin_is_still_replayed_to_the_hook(tmp_path: Path) -> None:
    hook = tmp_path / "echo-stdin-hook.sh"
    _write_hook(hook, "cat\n")
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(tmp_path)

    result = subprocess.run(
        ["bash", str(WRAPPER), "PostToolUse", str(hook)],
        cwd=tmp_path,
        env=env,
        input='{"tool_name":"Bash"}',
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )

    assert result.stdout == '{"tool_name":"Bash"}'
    assert _rows(tmp_path)[0]["stdout_bytes"] == 20


def test_measurement_killswitch_degrades_to_passthrough(tmp_path: Path) -> None:
    hook = tmp_path / "chatty-hook.sh"
    _write_hook(hook, "printf 'abcde\\n'\n")

    result = _run(tmp_path, "PostToolUse", hook, COS_HOOK_IO_MEASURE_DISABLE="1")

    assert result.stdout == "abcde\n"
    row = _rows(tmp_path)[0]
    assert row["stdout_bytes"] == 0
    assert row["stderr_bytes"] == 0


def test_skipped_invocations_still_carry_the_fields(tmp_path: Path) -> None:
    """SessionStart in safe mode never runs the hook; the schema must stay stable."""
    hook = tmp_path / "startup-hook.sh"
    _write_hook(hook, "echo should-not-run\n")

    result = _run(tmp_path, "SessionStart", hook, COS_DISABLE_SESSIONSTART_HOOKS="1")

    assert result.returncode == 0
    assert "should-not-run" not in result.stdout
    row = _rows(tmp_path)[0]
    assert row["skipped"] == 1
    assert row["stdout_bytes"] == 0
    assert row["stderr_bytes"] == 0


def test_no_temp_files_are_left_behind(tmp_path: Path) -> None:
    hook = tmp_path / "chatty-hook.sh"
    _write_hook(hook, "printf 'abcde\\n'\n")
    tmpdir = tmp_path / "tmp"
    tmpdir.mkdir()

    _run(tmp_path, "PostToolUse", hook, TMPDIR=str(tmpdir))

    assert list(tmpdir.iterdir()) == []
