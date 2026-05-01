"""Integration tests for ADR-104 startup circuit breaker and safe mode."""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
WRAPPER = REPO_ROOT / "scripts" / "hook-timing-wrapper.sh"
RECOVER = REPO_ROOT / "scripts" / "cos-startup-recover.sh"


def _make_project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    (project / ".cognitive-os" / "runtime").mkdir(parents=True)
    return project


def _make_hook(tmp_path: Path) -> tuple[Path, Path]:
    marker = tmp_path / "hook-runs.txt"
    hook = tmp_path / "fake-sessionstart-hook.sh"
    hook.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"printf 'ran\\n' >> {marker}\n"
        "cat >/dev/null\n"
        "printf 'diagnostic stdout'\n"
    )
    hook.chmod(0o755)
    return hook, marker


def _payload(project: Path) -> str:
    return json.dumps(
        {
            "hook_event_name": "SessionStart",
            "session_id": "main-session",
            "transcript_path": str(project / ".claude" / "projects" / "main.jsonl"),
            "source": "startup",
            "model": "claude-sonnet-4-6",
        }
    )


def _run(project: Path, hook: Path, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "COGNITIVE_OS_PROJECT_DIR": str(project),
        "COS_STARTUP_STORM_WINDOW_SECONDS": "20",
        "COS_STARTUP_SAFE_MODE_TTL_SECONDS": "300",
        **(extra_env or {}),
    }
    return subprocess.run(
        ["bash", str(WRAPPER), "SessionStart", str(hook)],
        input=_payload(project),
        text=True,
        capture_output=True,
        env=env,
        timeout=10,
    )


def _records(project: Path) -> list[dict[str, object]]:
    timing = project / ".cognitive-os" / "metrics" / "hook-timing.jsonl"
    return [json.loads(line) for line in timing.read_text().splitlines()]


def test_storm_detector_activates_safe_mode_and_skips_later_hooks(tmp_path: Path) -> None:
    project = _make_project(tmp_path)
    hook, marker = _make_hook(tmp_path)

    env = {"COS_STARTUP_STORM_THRESHOLD": "1"}
    first = _run(project, hook, env)
    second = _run(project, hook, env)

    assert first.returncode == 0
    assert second.returncode == 0
    assert first.stdout == ""  # SessionStart diagnostics are quarantined
    assert "diagnostic stdout" in first.stderr
    assert marker.read_text().splitlines() == ["ran"]

    safe_file = project / ".cognitive-os" / "runtime" / "startup-safe-mode.json"
    payload = json.loads(safe_file.read_text())
    assert payload["reason"] == "startup_storm"
    assert payload["count"] == 2

    recs = _records(project)
    assert recs[0]["safe_mode"] == 0
    assert recs[0]["skipped"] == 0
    assert recs[1]["safe_mode"] == 1
    assert recs[1]["skipped"] == 1
    assert recs[1]["skip_reason"] == "startup_storm"


def test_env_safe_mode_skips_sessionstart_immediately(tmp_path: Path) -> None:
    project = _make_project(tmp_path)
    hook, marker = _make_hook(tmp_path)

    result = _run(project, hook, {"COS_STARTUP_SAFE_MODE": "1"})

    assert result.returncode == 0
    assert not marker.exists()
    rec = _records(project)[-1]
    assert rec["safe_mode"] == 1
    assert rec["skipped"] == 1
    assert rec["skip_reason"] == "env_safe_mode"


def test_manual_disable_file_skips_sessionstart(tmp_path: Path) -> None:
    project = _make_project(tmp_path)
    hook, marker = _make_hook(tmp_path)
    disable = project / ".cognitive-os" / "runtime" / "disable-sessionstart-hooks"
    disable.write_text("operator requested\n")

    result = _run(project, hook)

    assert result.returncode == 0
    assert not marker.exists()
    rec = _records(project)[-1]
    assert rec["safe_mode"] == 1
    assert rec["skipped"] == 1
    assert rec["skip_reason"] == "manual_disable_file"


def test_expired_safe_mode_file_is_ignored(tmp_path: Path) -> None:
    project = _make_project(tmp_path)
    hook, marker = _make_hook(tmp_path)
    safe_file = project / ".cognitive-os" / "runtime" / "startup-safe-mode.json"
    safe_file.write_text(json.dumps({"expires_at": int(time.time()) - 1, "reason": "old"}))

    result = _run(project, hook)

    assert result.returncode == 0
    assert marker.read_text().splitlines() == ["ran"]
    rec = _records(project)[-1]
    assert rec["safe_mode"] == 0
    assert rec["skipped"] == 0
    assert not safe_file.exists(), "expired safe-mode file should be pruned"


def test_recovery_script_activates_bounded_safe_mode(tmp_path: Path) -> None:
    project = _make_project(tmp_path)
    hook, marker = _make_hook(tmp_path)

    env = {**os.environ, "COGNITIVE_OS_PROJECT_DIR": str(project), "COS_STARTUP_SAFE_MODE_TTL_SECONDS": "60"}
    recovery = subprocess.run(
        ["bash", str(RECOVER)],
        text=True,
        capture_output=True,
        env=env,
        timeout=10,
    )
    assert recovery.returncode == 0, recovery.stderr
    assert "COS startup recovery applied" in recovery.stdout

    safe_file = project / ".cognitive-os" / "runtime" / "startup-safe-mode.json"
    payload = json.loads(safe_file.read_text())
    assert payload["reason"] == "operator_recovery"
    assert payload["ttl_seconds"] == 60

    result = _run(project, hook)
    assert result.returncode == 0
    assert not marker.exists()
    rec = _records(project)[-1]
    assert rec["safe_mode"] == 1
    assert rec["skip_reason"] == "operator_recovery"
