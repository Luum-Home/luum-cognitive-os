# SCOPE: os-only
"""Portability proof for hooks/protected-config-write-guard.sh."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "hooks/protected-config-write-guard.sh"


def test_protected_config_write_guard_passes_unrelated_tool_from_arbitrary_project_root(tmp_path: Path) -> None:
    """Falsification probe: hook must not depend on OS repo cwd for passthrough input."""
    payload = {"tool_name": "Read", "tool_input": {"file_path": str(tmp_path / "probe.txt")}}
    env = os.environ.copy()
    env.update({
        "COGNITIVE_OS_PROJECT_DIR": str(tmp_path),
        "CODEX_PROJECT_DIR": str(tmp_path),
        "CLAUDE_PROJECT_DIR": str(tmp_path),
        "COS_METRICS_DIR": str(tmp_path / ".cognitive-os" / "metrics"),
        "COS_PRIVATE_MODE": "0",
    })
    result = subprocess.run(
        ["bash", str(ARTIFACT)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=tmp_path,
        env=env,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def _run_guard(tmp_path: Path, payload: dict[str, object]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update({
        "COGNITIVE_OS_PROJECT_DIR": str(tmp_path),
        "CODEX_PROJECT_DIR": str(tmp_path),
        "CLAUDE_PROJECT_DIR": str(tmp_path),
        "COS_METRICS_DIR": str(tmp_path / ".cognitive-os" / "metrics"),
        "COS_PRIVATE_MODE": "0",
    })
    manifests = tmp_path / "manifests"
    manifests.mkdir(parents=True, exist_ok=True)
    (manifests / "protected-config-write-policy.yaml").write_text(
        (REPO_ROOT / "manifests" / "protected-config-write-policy.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return subprocess.run(
        ["bash", str(ARTIFACT)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=tmp_path,
        env=env,
        timeout=20,
        check=False,
    )


def test_protected_config_write_guard_blocks_control_plane_settings(tmp_path: Path) -> None:
    """ADR-320: protected-config guard blocks control-plane config paths."""
    payload = {"tool_name": "Write", "tool_input": {"file_path": ".claude/settings.json"}}
    result = _run_guard(tmp_path, payload)

    assert result.returncode == 2
    assert ".claude/settings.json" in result.stderr


def test_protected_config_write_guard_does_not_claim_env_file_policy(tmp_path: Path) -> None:
    """ADR-320: .env is not in protected-config policy unless a future ADR adds it."""
    payload = {"tool_name": "Write", "tool_input": {"file_path": ".env"}}
    result = _run_guard(tmp_path, payload)

    assert result.returncode == 0, result.stderr


def test_protected_config_write_guard_blocks_bash_redirect_to_control_plane(tmp_path: Path) -> None:
    payload = {"tool_name": "Bash", "tool_input": {"command": "printf bad > .claude/settings.json"}}
    result = _run_guard(tmp_path, payload)

    assert result.returncode == 2
    assert ".claude/settings.json" in result.stderr


def test_protected_config_write_guard_blocks_bash_python_write_text(tmp_path: Path) -> None:
    command = "python3 - <<'PY'\nfrom pathlib import Path\nPath('hooks/new.sh').write_text('x')\nPY"
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
    result = _run_guard(tmp_path, payload)

    assert result.returncode == 2
    assert "hooks/new.sh" in result.stderr


def test_protected_config_write_guard_allows_bash_read_only_control_plane(tmp_path: Path) -> None:
    payload = {"tool_name": "Bash", "tool_input": {"command": "cat .claude/settings.json || true"}}
    result = _run_guard(tmp_path, payload)

    assert result.returncode == 0, result.stderr
