# SCOPE: os-only
"""Portability proof for cos_lib/orchestrator_verify.py.

``orchestrator_verify`` backs ``hooks/claim-validator.sh`` (SCOPE: both), a
consumer-facing PostToolUse hook on Agent. This proof pins that the module
imports and its primary entry point (``verify_all`` / ``format_report``) works
against an arbitrary consumer project directory — never anything that assumes
the Cognitive OS source repo layout (e.g. its own ``manifests/`` or ADR
corpus). The config files it checks (``.claude/settings.json``,
``cognitive-os.yaml``, ``manifests/hook-quality.yaml``, ...) are read
relative to the caller-supplied ``project_root`` and are simply absent (not
required) in a project that hasn't created them.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "cos_lib/orchestrator_verify.py"


def test_orchestrator_verify_imports_from_arbitrary_project_root(tmp_path: Path, monkeypatch) -> None:
    """Falsification probe: library import must not depend on process cwd."""
    monkeypatch.chdir(tmp_path)
    sys.path.insert(0, str(REPO_ROOT))
    spec = importlib.util.spec_from_file_location("portability_orchestrator_verify", ARTIFACT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)


def test_verify_all_works_against_arbitrary_consumer_project(tmp_path: Path) -> None:
    """Falsification probe: exercise the real entry point in a throwaway project.

    Builds a minimal consumer project (not the OS source repo) with a target
    file present but no config references to it, then confirms a "wired"
    claim about that file is correctly reported as FAILED because the
    bilateral reference check finds no config entry -- proving the checker
    operates purely off the supplied ``project_root`` rather than any
    baked-in OS-repo path.
    """
    project_dir = tmp_path / "consumer-project"
    (project_dir / "hooks").mkdir(parents=True)
    (project_dir / "hooks" / "example-hook.sh").write_text("#!/usr/bin/env bash\necho hi\n")

    script = (
        "import sys; sys.path.insert(0, %r)\n"
        "from cos_lib.orchestrator_verify import verify_all, format_report\n"
        "output = 'The hook hooks/example-hook.sh has been wired into the pipeline.'\n"
        "outcomes = verify_all(output, project_root=%r)\n"
        "print(len(outcomes))\n"
        "print(outcomes[0].verified)\n"
        "print(format_report(outcomes))\n"
    ) % (str(REPO_ROOT), str(project_dir))

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=project_dir,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert lines[0] == "1"
    assert lines[1] == "False"
    assert "FAIL" in result.stdout
