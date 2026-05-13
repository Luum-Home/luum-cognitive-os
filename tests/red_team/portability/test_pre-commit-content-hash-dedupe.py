# SCOPE: os-only
# scope: both
"""Portability proofs for scripts/precommit_content_hash.py — P4.1 (ADR-116).

These tests verify the content-hash dedupe primitive works correctly in
arbitrary environments (no Cognitive OS runtime required).

Run with:
    python3 -m pytest "tests/red_team/portability/test_pre-commit-content-hash-dedupe.py" -v
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

import scripts.precommit_content_hash as dedupe  # noqa: E402


# ---------------------------------------------------------------------------
# Proof 1: module runs in an arbitrary temp directory without COS stack
# ---------------------------------------------------------------------------

def test_off_mode_exits_zero_without_git_calls(tmp_path: Path) -> None:
    """COS_DEDUPE_MODE=off must return 0 without touching git or event bus.

    This proves portability: the off-switch works even when there is no
    .cognitive-os directory, no origin remote, and no event bus file.
    """
    with patch.object(dedupe, "get_staged_patch_id") as mock_staged:
        result = dedupe.check(mode="off", repo_root=tmp_path)

    assert result == 0, "off mode must always return 0"
    mock_staged.assert_not_called()


# ---------------------------------------------------------------------------
# Proof 2: JSONL event is written to a user-supplied bus_path (no COS anchor)
# ---------------------------------------------------------------------------

def test_emit_writes_valid_jsonl_to_arbitrary_path(tmp_path: Path) -> None:
    """event_bus.emit is invoked and produces valid JSONL at any path.

    Proves the primitive does not require a .cognitive-os directory anchor.
    """
    bus_file = tmp_path / "subdir" / "events.jsonl"

    # Simulate a collision without git by patching the two git-calling helpers
    with (
        patch.object(dedupe, "get_staged_patch_id", return_value="porttest-pid"),
        patch.object(dedupe, "get_origin_patch_ids", return_value={"porttest-pid": "porttest-sha"}),
    ):
        dedupe.check(mode="warn", repo_root=tmp_path, bus_path=bus_file)

    assert bus_file.exists(), "events.jsonl must exist after collision"

    raw_lines = [ln for ln in bus_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert raw_lines, "at least one JSONL line expected"

    for line in raw_lines:
        event = json.loads(line)  # raises on invalid JSON — that is the proof
        assert "event_type" in event
        assert "ts" in event
        assert "payload" in event


# ---------------------------------------------------------------------------
# Proof 3: CLI is invokable as a subprocess in any working directory
# ---------------------------------------------------------------------------

def test_cli_subprocess_off_mode_exits_zero(tmp_path: Path) -> None:
    """scripts/precommit_content_hash.py can be invoked as a standalone CLI.

    Runs the script as a subprocess with COS_DEDUPE_MODE=off so no git
    commands are issued, confirming it is a self-contained portable tool.
    """
    script = REPO_ROOT / "scripts" / "precommit_content_hash.py"
    assert script.exists(), f"Script missing: {script}"

    env = {"COS_DEDUPE_MODE": "off", "PATH": "/usr/bin:/bin"}
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, (
        f"Expected exit 0 in off mode, got {result.returncode}\n"
        f"stderr: {result.stderr}"
    )
