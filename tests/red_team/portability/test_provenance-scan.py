# SCOPE: os-only
"""Portability proof for provenance scan shell surfaces."""

from __future__ import annotations

import os
import sys
import shutil
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
WRAPPER = REPO_ROOT / "scripts" / "provenance-scan"
HOOK = REPO_ROOT / "hooks" / "provenance-scan.sh"
SCANNER = REPO_ROOT / "scripts" / "provenance_scan.py"
POLICY = REPO_ROOT / "manifests" / "provenance-scan.yaml"


def _install_scanner(project: Path) -> Path:
    bin_dir = project / ".cognitive-os" / "bin"
    bin_dir.mkdir(parents=True)
    shutil.copy2(WRAPPER, bin_dir / "provenance-scan")
    shutil.copy2(SCANNER, bin_dir / "provenance_scan.py")
    shutil.copy2(POLICY, project / ".cognitive-os" / "provenance-scan.yaml")
    (bin_dir / "provenance-scan").chmod(0o755)
    return bin_dir / "provenance-scan"


def test_installed_wrapper_runs_from_adopted_repo_without_source_scripts(tmp_path: Path) -> None:
    project = tmp_path / "consumer"
    project.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=project, check=True)
    wrapper = _install_scanner(project)
    (project / "README.md").write_text("portable\n", encoding="utf-8")

    env = os.environ.copy()
    env["PYTHON"] = sys.executable
    result = subprocess.run(
        [str(wrapper), "--json", "README.md"],
        cwd=project,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=20,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert '"status": "pass"' in result.stdout


def test_hook_prefers_project_local_scanner_and_policy(tmp_path: Path) -> None:
    project = tmp_path / "consumer"
    hooks_dir = project / "hooks"
    hooks_dir.mkdir(parents=True)
    shutil.copy2(HOOK, hooks_dir / "provenance-scan.sh")
    (hooks_dir / "provenance-scan.sh").chmod(0o755)
    _install_scanner(project)
    subprocess.run(["git", "init", "-q"], cwd=project, check=True)
    (project / "README.md").write_text("portable\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=project, check=True)
    env = os.environ.copy()
    env.update({"COGNITIVE_OS_PROJECT_DIR": str(project), "PYTHON": sys.executable})

    result = subprocess.run(
        ["bash", str(hooks_dir / "provenance-scan.sh")],
        cwd=project,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=20,
    )

    assert result.returncode == 0, result.stderr + result.stdout
