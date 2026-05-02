# SCOPE: both
"""Portability probes for scripts/cos_concurrent_status.py.

These tests execute the CLI against non-SO temporary projects so the read-only
status composer proves it does not depend on repository-local runtime state.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CLI = REPO_ROOT / "scripts" / "cos_concurrent_status.py"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_cli(project: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(CLI), "--project-dir", str(project), *extra],
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )


def test_empty_non_so_project_emits_json(tmp_path: Path) -> None:
    result = run_cli(tmp_path)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["project_dir"] == str(tmp_path.resolve())
    assert payload["locks"] == {"edit": [], "git_index": [], "plan": [], "resource": []}


def test_compact_output_is_single_line_json(tmp_path: Path) -> None:
    result = run_cli(tmp_path, "--compact")
    assert result.returncode == 0, result.stderr
    assert "\n" not in result.stdout.strip()
    assert json.loads(result.stdout)["active_sessions"] == []


def test_detects_projection_gap_from_consumer_project(tmp_path: Path) -> None:
    write(tmp_path / ".claude/settings.json", "hooks/orchestrator-claim-gate.sh")
    write(tmp_path / ".codex/hooks.json", "")
    write(tmp_path / "cognitive-os.yaml", "hooks/orchestrator-claim-gate.sh")
    write(tmp_path / "scripts/_lib/settings-driver-claude-code.sh", "")
    result = run_cli(tmp_path)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert any(item["code"] == "projection_incomplete" for item in payload["findings"])


def test_collects_consumer_runtime_locks(tmp_path: Path) -> None:
    write(tmp_path / ".cognitive-os/runtime/git-index.lock/meta.json", '{"session_id":"s1"}')
    result = run_cli(tmp_path)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["locks"]["git_index"][0]["session_id"] == "s1"


def test_falsification_unknown_flag_fails_instead_of_rubber_stamping(tmp_path: Path) -> None:
    result = run_cli(tmp_path, "--definitely-not-a-real-flag")
    assert result.returncode != 0
    assert "unrecognized arguments" in result.stderr
