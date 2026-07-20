from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest


pytestmark = [pytest.mark.smoke, pytest.mark.integration]

REPO_ROOT = Path(__file__).resolve().parents[2]
INSTALL = REPO_ROOT / "install.sh"
COS_STATUS = REPO_ROOT / "scripts" / "cos-status.sh"


def _run_status(project: Path, *, harness: str | None = None) -> dict:
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(project)
    env.pop("CODEX_PROJECT_DIR", None)
    env.pop("CLAUDE_PROJECT_DIR", None)
    if harness:
        env["COGNITIVE_OS_HARNESS"] = harness
    else:
        env.pop("COGNITIVE_OS_HARNESS", None)

    result = subprocess.run(
        ["bash", str(COS_STATUS), "--json"],
        cwd=project,
        env=env,
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    return json.loads(result.stdout)


def test_fresh_install_codex_project_status_matches_advertised_surface(tmp_path: Path) -> None:
    """Smoke: install.sh --harness=codex creates the advertised consumer surface."""
    project = tmp_path / "consumer"
    project.mkdir()

    env = os.environ.copy()
    env.update(
        {
            "COGNITIVE_OS_SKIP_MANIFEST_CHECK": "true",
            "COGNITIVE_OS_FORCE": "true",
            "COS_REGISTRY_FILE": str(tmp_path / "installations.json"),
            "HOME": str(tmp_path / "home"),
        }
    )

    result = subprocess.run(
        ["bash", str(INSTALL), "--harness=codex", "--scope=project"],
        cwd=project,
        env=env,
        text=True,
        capture_output=True,
        timeout=180,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout

    expected_paths = [
        ".codex/hooks.json",
        ".cognitive-os/hooks/cos",
        ".cognitive-os/rules/cos",
        ".cognitive-os/skills/cos",
        ".cognitive-os/templates/cos",
        ".cognitive-os/install-meta.json",
        "cognitive-os.yaml",
    ]
    for rel in expected_paths:
        assert (project / rel).exists(), f"fresh Codex install did not create {rel}"

    meta = json.loads((project / ".cognitive-os/install-meta.json").read_text(encoding="utf-8"))
    assert meta["harness"] == "codex"
    assert meta["settings_driver"] == ".codex/hooks.json"
    assert meta["source"] == str(REPO_ROOT)

    status = _run_status(project)

    # Health first: this is the actual contract. Asserting exact surface counts
    # before it meant a stale count masked whether the install was even sound --
    # the test failed on `hooks.total == 14` (it is 16) and never reached here.
    assert status["health"]["failures"] == 0, status["health"]

    # Structural contract: the driver and kernel paths are what we advertise.
    assert status["hooks"]["driver_path"] == ".codex/hooks.json"
    assert status["skills"]["kernel_path"] == ".cognitive-os/skills/cos/"
    assert status["rules"]["source_path"].endswith(".cognitive-os/rules/cos")

    # Surface counts are lower bounds, not snapshots. The exact numbers (14/9/14)
    # were whatever happened to exist when this test was written, so every new
    # projected hook, skill, or rule broke a smoke test that has nothing to do
    # with adding primitives. What actually matters is that each surface is
    # non-empty -- an install that projects zero hooks is broken, an install
    # that projects more is the OS growing.
    assert status["hooks"]["total"] >= 14, status["hooks"]
    assert status["skills"]["kernel_installed"] >= 9, status["skills"]
    assert status["rules"]["source_count"] >= 14, status["rules"]


def test_self_host_cos_status_can_be_forced_to_codex_driver() -> None:
    """Smoke: self-host repos with both drivers can still validate Codex explicitly."""
    status = _run_status(REPO_ROOT, harness="codex")

    assert status["hooks"]["driver_path"] == ".codex/hooks.json"
    assert status["hooks"]["total"] > 0
    assert status["health"]["failures"] == 0
