from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
PHASES = REPO_ROOT / "manifests" / "harness-implementation-phases.yaml"
HARNESS = REPO_ROOT / "manifests" / "harness-projection.yaml"


def test_harness_phase_manifest_tracks_implemented_structural_harnesses() -> None:
    phases = yaml.safe_load(PHASES.read_text())
    structural = phases["phases"]["structural-instruction-harnesses"]

    assert structural["status"] == "in_progress"
    assert {"opencode", "vscode-copilot", "cursor"} <= set(structural["implemented_harnesses"])
    assert "acc_default_full_projection_counts" in structural["acceptance"]

    shell_ci = phases["phases"]["shell-ci-formal-harness"]
    assert shell_ci["status"] == "done"
    assert shell_ci["implemented_harnesses"] == ["shell-ci"]

    qwen_phase = phases["phases"]["qwen-windsurf-kimi-structural"]
    assert qwen_phase["status"] == "in_progress"
    assert qwen_phase["implemented_harnesses"] == ["qwen-code"]


def test_implemented_harnesses_have_projection_commands_and_limitations() -> None:
    manifest = yaml.safe_load(HARNESS.read_text())
    implemented = [item for item in manifest["harnesses"] if item["status"] == "implemented"]

    ids = {item["id"] for item in implemented}
    assert {"claude", "codex", "opencode", "vscode-copilot", "cursor", "qwen-code", "shell-ci"} <= ids
    for item in implemented:
        assert item.get("default_command"), item["id"]
        assert item.get("proof") not in {None, "none"}, item["id"]
        assert item.get("limitations"), item["id"]
