from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "cos-test-laptop-bg"


def run_script(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        [str(SCRIPT), *args],
        cwd=ROOT,
        env=merged_env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_help_documents_background_contract() -> None:
    result = run_script("--help")
    assert result.returncode == 0
    assert "Defaults to: bash -lc 'make test-laptop'" in result.stdout
    assert "COS_TEST_BG_LOG_DIR" in result.stdout


def test_dry_run_json_returns_command_and_log_without_pid(tmp_path: Path) -> None:
    result = run_script("--json", "--dry-run", "--log-dir", str(tmp_path), "--", "echo", "ok")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "dry-run"
    assert payload["pid"] is None
    assert payload["command"] == "echo ok"
    assert str(tmp_path) in payload["log"]
    assert not (tmp_path / "latest.pid").exists()


def test_background_command_writes_log_and_pid(tmp_path: Path) -> None:
    result = run_script("--json", "--log-dir", str(tmp_path), "--", "bash", "-lc", "echo bg-ok")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "started"
    assert isinstance(payload["pid"], int)
    log = Path(payload["log"])
    for _ in range(30):
        if log.exists() and "exit_code=" in log.read_text(errors="replace"):
            break
        time.sleep(0.1)
    log_text = log.read_text(errors="replace")
    assert "bg-ok" in log_text
    assert "exit_code=0" in log_text
    assert (tmp_path / "latest.pid").read_text().strip().isdigit()
    assert (tmp_path / "latest.log").exists()
