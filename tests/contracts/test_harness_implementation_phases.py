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
    assert qwen_phase["implemented_harnesses"] == ["kimi-code", "qwen-code"]
    assert qwen_phase["candidate_harnesses"] == ["windsurf"]


def test_implemented_harnesses_have_projection_commands_and_limitations() -> None:
    manifest = yaml.safe_load(HARNESS.read_text())
    implemented = [item for item in manifest["harnesses"] if item["status"] == "implemented"]

    ids = {item["id"] for item in implemented}
    assert {"claude", "codex", "opencode", "vscode-copilot", "cursor", "qwen-code", "kimi-code", "shell-ci"} <= ids
    for item in implemented:
        assert item.get("default_command"), item["id"]
        assert item.get("proof") not in {None, "none"}, item["id"]
        assert item.get("limitations"), item["id"]


def test_structural_harnesses_do_not_claim_runtime_support() -> None:
    manifest = yaml.safe_load(HARNESS.read_text())
    structural_ids = {
        "cursor",
        "opencode",
        "vscode-copilot",
        "qwen-code",
        "kimi-code",
        "shell-ci",
    }

    by_id = {item["id"]: item for item in manifest["harnesses"]}
    for harness_id in structural_ids:
        item = by_id[harness_id]
        assert item["status"] == "implemented", harness_id
        assert item["proof_level"] == "structural", harness_id
        limitation_text = " ".join(item.get("limitations", [])).lower()
        assert "structural" in limitation_text, harness_id
        assert "runtime" in limitation_text, harness_id
        assert (
            "no native cos lifecycle hook parity" in limitation_text
            or "not native cos lifecycle hooks" in limitation_text
            or "syntax proof only" in limitation_text
        ), harness_id


def test_native_lifecycle_harnesses_are_explicitly_labeled() -> None:
    manifest = yaml.safe_load(HARNESS.read_text())
    by_id = {item["id"]: item for item in manifest["harnesses"]}

    assert by_id["claude"]["proof_level"] == "native-lifecycle"
    assert by_id["codex"]["proof_level"] == "native-lifecycle"
