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


def test_wrapper_logs_json_without_own_stderr_by_default(tmp_path: Path) -> None:
    hook = tmp_path / "sample-hook.sh"
    _write_hook(hook, "echo hook-out\n")
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(tmp_path)
    env.pop("COS_HOOK_TIMING_VERBOSE", None)
    env.pop("COS_HOOK_TIMING_FIFO", None)

    result = subprocess.run(
        ["bash", str(WRAPPER), "PostToolUse", str(hook)],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        timeout=5,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout == "hook-out\n"
    assert result.stderr == ""
    rows = (tmp_path / ".cognitive-os/metrics/hook-timing.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(rows) == 1
    row = json.loads(rows[0])
    assert row["event"] == "PostToolUse"
    assert row["hook"] == "sample-hook"


def test_wrapper_verbose_stderr_is_opt_in(tmp_path: Path) -> None:
    hook = tmp_path / "sample-hook.sh"
    _write_hook(hook, "exit 0\n")
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(tmp_path)
    env["COS_HOOK_TIMING_VERBOSE"] = "1"

    result = subprocess.run(
        ["bash", str(WRAPPER), "PreToolUse", str(hook)],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        timeout=5,
        check=False,
    )

    assert result.returncode == 0
    assert "[hook] sample-hook PreToolUse" in result.stderr


def test_wrapper_does_not_create_fifo_by_default(tmp_path: Path) -> None:
    hook = tmp_path / "sample-hook.sh"
    _write_hook(hook, "exit 0\n")
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(tmp_path)
    env.pop("COS_HOOK_TIMING_FIFO", None)

    result = subprocess.run(
        ["bash", str(WRAPPER), "PostToolUse", str(hook)],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        timeout=5,
        check=False,
    )

    assert result.returncode == 0
    assert not (tmp_path / ".cognitive-os/runtime/hook-stream.fifo").exists()
