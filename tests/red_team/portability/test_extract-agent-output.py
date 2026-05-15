# SCOPE: os-only
"""Portability proof for scripts/extract-agent-output.sh."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "scripts/extract-agent-output.sh"


def test_extract_agent_output_runs_from_arbitrary_project_root(tmp_path: Path) -> None:
    """Falsification probe: script must not depend on OS repo cwd for safe invocation."""
    output = tmp_path / "agent.output.jsonl"
    output.write_text(
        '{"type":"assistant","message":{"content":[{"type":"text","text":"hello"}]}}\n',
        encoding="utf-8",
    )
    result = subprocess.run(
        ["bash", str(ARTIFACT), str(output)],
        text=True,
        capture_output=True,
        cwd=tmp_path,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "hello" in result.stdout


def test_extract_agent_output_has_passing_scope_contract() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/primitive_scope_classifier.py",
            "--project-dir",
            ".",
            "--paths",
            "scripts/extract-agent-output.sh",
            "--fail-contradictions",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert '"by_effective_scope": {"both": 1}' in result.stdout
