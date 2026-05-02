"""Documentation contracts for Cognitive OS harness engineering doctrine."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest


pytestmark = pytest.mark.contract

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOC = PROJECT_ROOT / "docs" / "architecture" / "harness-engineering.md"


def test_harness_engineering_doc_is_linked_from_docs_index() -> None:
    assert DOC.exists()
    assert "architecture/harness-engineering.md" in (PROJECT_ROOT / "docs" / "README.md").read_text()


def test_harness_engineering_doc_maps_real_components() -> None:
    content = DOC.read_text()
    components = [
        "AGENTS.md",
        "cognitive-os.yaml",
        "rules/RULES-COMPACT.md",
        ".codex/project-index.md",
        "hooks/session-init.sh",
        "hooks/auto-verify.sh",
        "hooks/session-learning.sh",
        "bin/cos-agent",
        "bin/cos-skill",
        "scripts/cos_sprint.py",
        "scripts/cos-doctor-harness.sh",
        "scripts/measure_harness_profiles.py",
        "manifests/harness-profiles.yaml",
    ]
    for component in components:
        assert component in content, component
        assert (PROJECT_ROOT / component).exists(), component


def test_harness_engineering_commands_execute() -> None:
    env = os.environ.copy()
    env["COGNITIVE_OS_HARNESS"] = "codex"
    env["CODEX_PROJECT_DIR"] = str(PROJECT_ROOT)

    doctor = subprocess.run(
        ["bash", str(PROJECT_ROOT / "scripts" / "cos"), "init-check", "--json"],
        cwd=str(PROJECT_ROOT),
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert doctor.returncode == 0, doctor.stderr + doctor.stdout
    doctor_payload = json.loads(doctor.stdout)
    assert doctor_payload["issues"] == 0
    assert doctor_payload["mode"] == "init-check"

    direct_doctor = subprocess.run(
        ["bash", str(PROJECT_ROOT / "bin" / "cognitive-os.sh"), "doctor", "harness", "--json"],
        cwd=str(PROJECT_ROOT),
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert direct_doctor.returncode == 0, direct_doctor.stderr + direct_doctor.stdout
    assert json.loads(direct_doctor.stdout)["issues"] == 0

    measure = subprocess.run(
        ["bash", str(PROJECT_ROOT / "scripts" / "cos"), "measure", "harness-profiles", "--json"],
        cwd=str(PROJECT_ROOT),
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert measure.returncode == 0, measure.stderr + measure.stdout
    payload = json.loads(measure.stdout)
    assert payload["minimal"]["hook_count"] == 3
    assert payload["comparison"]["max_full_hook_count"] >= payload["minimal"]["hook_count"]
