"""Behavior tests for the opt-in Engram → Obsidian Stop hook."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

REPO = Path(__file__).resolve().parents[2]
HOOK = REPO / "hooks" / "engram-obsidian-export-on-stop.sh"


def test_obsidian_export_stop_hook_is_noop_without_vault(tmp_path: Path) -> None:
    env = {
        **os.environ,
        "COGNITIVE_OS_PROJECT_DIR": str(REPO),
        "COGNITIVE_OS_HOOK_HEARTBEAT": "false",
    }
    env.pop("COS_OBSIDIAN_VAULT", None)

    result = subprocess.run([str(HOOK)], cwd=tmp_path, env=env, text=True, capture_output=True, check=False)

    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""


def test_obsidian_export_stop_hook_documents_opt_in_gate() -> None:
    text = HOOK.read_text(encoding="utf-8")

    assert "COS_OBSIDIAN_VAULT" in text
    assert "--write" in text
    assert "exit 0" in text
