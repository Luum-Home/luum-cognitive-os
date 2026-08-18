# SCOPE: os-only
"""Paired portability proof for rules/codebase-memory-directive.md.

The rule is ``SCOPE: both``: it travels into consumer projects, so the gate
command it documents has to work there too. The previous version of this proof
tried to *execute* the Markdown file with ``--help`` and could never pass; it
proved nothing except that a scaffold template had been applied blindly.

What is actually falsifiable here: the rule names one gate script and one
exit-code contract (0 READY / 1 NOT_READY / 2 ERROR). This proof runs that gate
from a foreign project root and checks the contract holds there.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "rules/codebase-memory-directive.md"
GATE = REPO_ROOT / "scripts/check_codebase_memory_readiness.py"

EXIT_BY_STATE = {"READY": 0, "NOT_READY": 1}


def _load_health():
    path = REPO_ROOT / "scripts" / "primitive_scope_health.py"
    spec = importlib.util.spec_from_file_location("scope_health_codebase_memory", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_carries_no_absolute_source_path() -> None:
    """A rule that names this checkout cannot travel to a consumer project."""
    health = _load_health()
    assert not health.SOURCE_PATH_RE.search(ARTIFACT.read_text(encoding="utf-8"))


def test_documented_gate_script_exists() -> None:
    text = ARTIFACT.read_text(encoding="utf-8")
    assert "scripts/check_codebase_memory_readiness.py" in text
    assert GATE.exists()


def test_runs_from_arbitrary_project_root(tmp_path: Path) -> None:
    """The documented gate must honour its exit-code contract from a foreign cwd."""
    result = subprocess.run(
        [sys.executable, str(GATE), "--json"],
        cwd=str(tmp_path),
        text=True,
        capture_output=True,
        timeout=25,
        check=False,
    )
    assert result.returncode in (0, 1, 2), result.stderr

    if result.returncode == 2:  # ERROR path: no JSON contract to check
        return

    payload = json.loads(result.stdout)
    state = payload["state"]
    assert state in EXIT_BY_STATE, state
    assert result.returncode == EXIT_BY_STATE[state], (
        f"rule documents {state} -> {EXIT_BY_STATE[state]}, gate returned {result.returncode}"
    )


def test_rule_text_survives_relocation(tmp_path: Path) -> None:
    """Falsification probe: the directive must read the same at a foreign root."""
    relocated = tmp_path / "rules" / ARTIFACT.name
    relocated.parent.mkdir(parents=True)
    relocated.write_text(ARTIFACT.read_text(encoding="utf-8"), encoding="utf-8")

    text = relocated.read_text(encoding="utf-8")
    assert "SCOPE: both" in text
    assert "0 READY / 1 NOT_READY / 2 ERROR" in text
