"""Fidelity-preserving adapter compiler contracts."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from lib.adapter_compile import compile_adapter

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_adapter_compile_dry_run_preserves_fidelity_without_native_writes(tmp_path: Path) -> None:
    receipt = compile_adapter(root=REPO_ROOT, harness="cursor", output_dir=tmp_path, dry_run=True)

    assert receipt["schema_version"] == "cos-adapter-compile.v1"
    assert receipt["status"] == "planned"
    assert receipt["harness"] == "cursor"
    assert receipt["proof_level"] == "structural"
    assert receipt["native_file_emission"] is False
    assert receipt["projection_driver"] == "scripts/cos_init.py"
    assert ".cursor/rules/cognitive-os.mdc" in receipt["settings_paths"]
    assert receipt["fidelity_summary"]["structural-advisory"] >= 1
    assert receipt["enforcement_claims"] == 0
    assert not (tmp_path / ".cursor").exists()


def test_adapter_compile_emits_native_files_via_governed_driver(tmp_path: Path) -> None:
    receipt = compile_adapter(root=REPO_ROOT, harness="cursor", output_dir=tmp_path, dry_run=False)

    assert receipt["status"] == "compiled"
    assert receipt["native_file_emission"] is True
    assert ".cursor/rules/cognitive-os.mdc" in receipt["emitted_paths"]
    assert ".cursor/mcp.json" in receipt["emitted_paths"]
    assert (tmp_path / ".cursor/rules/cognitive-os.mdc").is_file()
    assert "alwaysApply: true" in (tmp_path / ".cursor/rules/cognitive-os.mdc").read_text()
    install_meta = json.loads((tmp_path / ".cognitive-os/install-meta.json").read_text())
    assert install_meta["harness"] == "cursor"


def test_cos_adapters_compile_cli_outputs_receipt(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            str(REPO_ROOT / "scripts" / "cos-adapters"),
            "--project-dir",
            str(REPO_ROOT),
            "compile",
            "vscode-copilot",
            "--output",
            str(tmp_path),
            "--dry-run",
            "--json",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    receipt = json.loads(result.stdout)
    assert receipt["schema_version"] == "cos-adapter-compile.v1"
    assert receipt["harness"] == "vscode-copilot"
    assert receipt["status"] == "planned"
    assert receipt["native_file_emission"] is False
    assert ".github/copilot-instructions.md" in receipt["settings_paths"]


def test_adapter_compile_emits_agents_md_universal_target(tmp_path: Path) -> None:
    receipt = compile_adapter(root=REPO_ROOT, harness="agents-md", output_dir=tmp_path, dry_run=False)

    assert receipt["status"] == "compiled"
    assert receipt["harness"] == "agents-md"
    assert receipt["native_file_emission"] is True
    assert "AGENTS.md" in receipt["emitted_paths"]
    assert receipt["fidelity_summary"]["structural-advisory"] >= 1
    assert receipt["enforcement_claims"] == 0
    agents = (tmp_path / "AGENTS.md").read_text()
    assert "COGNITIVE_OS_AGENTS_MD_START" in agents
    assert "Cognitive OS for AGENTS.md-native tools" in agents
    install_meta = json.loads((tmp_path / ".cognitive-os/install-meta.json").read_text())
    assert install_meta["harness"] == "agents-md"
