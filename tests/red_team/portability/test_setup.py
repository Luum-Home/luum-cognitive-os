from __future__ import annotations

import subprocess
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]


def test_setup_is_protected_bootstrap_surface() -> None:
    script = ROOT / "scripts" / "setup.sh"
    text = script.read_text(encoding="utf-8")

    assert "# SCOPE: both" in text

    manifest = yaml.safe_load((ROOT / "manifests" / "primitive-readiness-protected-install-surfaces.yaml").read_text(encoding="utf-8"))
    setup_row = next(item for item in manifest["scripts"] if item["path"] == "scripts/setup.sh")
    assert setup_row["surface"] == "bootstrap"


def test_setup_script_is_shell_parseable_without_running_installers() -> None:
    result = subprocess.run(
        ["bash", "-n", "scripts/setup.sh"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
