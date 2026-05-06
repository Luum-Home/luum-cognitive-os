from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / "hooks" / "cosd-auth-guard.sh"


def _run_hook(tmp_path: Path, payload: dict, env_extra: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(tmp_path)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env,
        timeout=10,
    )


def test_hook_blocks_remote_launch_without_token(tmp_path: Path) -> None:
    result = _run_hook(
        tmp_path,
        {"tool_name": "Bash", "tool_input": {"command": "scripts/cosd serve --host 0.0.0.0 --allow-remote"}},
    )
    assert result.returncode == 2
    assert "COSD AUTH GUARD" in result.stderr
    audit = tmp_path / ".cognitive-os" / "metrics" / "cosd-auth-guard.jsonl"
    assert audit.exists()
    assert "token" in audit.read_text(encoding="utf-8")


def test_hook_allows_secure_remote_launch(tmp_path: Path) -> None:
    result = _run_hook(
        tmp_path,
        {
            "tool_name": "Bash",
            "tool_input": {
                "command": "scripts/cosd serve --host 0.0.0.0 --allow-remote --token-file /run/cosd/token"
            },
        },
    )
    assert result.returncode == 0, result.stderr


def test_hook_blocks_unapproved_cosd_config_edit(tmp_path: Path) -> None:
    result = _run_hook(
        tmp_path,
        {"tool_name": "Write", "tool_input": {"file_path": "infra/cosd/systemd/cosd.service"}},
    )
    assert result.returncode == 2
    assert "config edit" in result.stderr


def test_hook_allows_approved_cosd_config_edit(tmp_path: Path) -> None:
    result = _run_hook(
        tmp_path,
        {"tool_name": "Write", "tool_input": {"file_path": "infra/cosd/systemd/cosd.service"}},
        {"COS_ALLOW_COSD_AUTH_CONFIG_WRITE": "1"},
    )
    assert result.returncode == 0, result.stderr
