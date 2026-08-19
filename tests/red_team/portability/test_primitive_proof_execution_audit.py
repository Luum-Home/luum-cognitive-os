#!/usr/bin/env python3
# SCOPE: os-only
"""Portability proof for scripts/primitive_proof_execution_audit.py.

Executes the artifact as a subprocess from a foreign cwd and asserts it audits
the project it is POINTED AT (--project-dir), not the cwd it happens to run in.
Falsification probe: a synthetic mini-project with no manifests must not inherit
this repo's registry.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "scripts" / "primitive_proof_execution_audit.py"


def _run(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("COGNITIVE_OS_PROJECT_DIR", None)
    env.pop("CLAUDE_PROJECT_DIR", None)
    return subprocess.run(
        [sys.executable, str(ARTIFACT), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        env=env,
        timeout=300,
    )


def test_audits_the_pointed_project_from_a_foreign_cwd(tmp_path: Path) -> None:
    """Run from an unrelated cwd; --project-dir decides what gets audited."""
    result = _run(tmp_path, "--project-dir", str(REPO_ROOT))
    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)
    assert summary["total"] > 1000, summary
    assert summary["rows_without_execution"] >= 0
    assert set(summary["by_execution_class"]) <= {
        "executes", "not-executed", "non-executable-artifact", "missing-test", "no-test",
    }
    assert str(REPO_ROOT) not in json.dumps(summary["by_execution_class"])


def test_empty_project_yields_empty_population_finding(tmp_path: Path) -> None:
    """Falsification probe: a project with no registry must NOT come back green."""
    (tmp_path / "manifests").mkdir()
    result = _run(tmp_path, "--project-dir", str(tmp_path), "--strict")
    assert result.returncode == 1, (result.returncode, result.stdout, result.stderr)
    summary = json.loads(result.stdout)
    assert summary["total"] == 0, summary
    assert "proof-execution-empty-population" in summary["findings_by_code"], summary
