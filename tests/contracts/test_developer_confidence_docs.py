"""Documentation contract for Cognitive OS developer-confidence positioning."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


pytestmark = pytest.mark.contract

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOC = PROJECT_ROOT / "docs" / "business" / "developer-confidence.md"


def test_developer_confidence_doc_is_linked_from_product_entrypoints() -> None:
    assert "business/developer-confidence.md" in (
        PROJECT_ROOT / "docs" / "README.md"
    ).read_text()
    assert "developer-confidence.md" in (
        PROJECT_ROOT / "docs" / "business" / "product-messaging.md"
    ).read_text()


def test_developer_confidence_doc_states_dx_and_safety_contract() -> None:
    content = DOC.read_text()

    required = [
        "Cognitive OS makes AI-assisted development easier to trust.",
        "memory between sessions",
        "pending-task recovery",
        "security and safety checks",
        "verifiable doctors",
        "less dependence on one vendor or harness",
        "Simple by default, rigorous when needed.",
    ]

    for phrase in required:
        assert phrase in content


def test_developer_confidence_doc_has_lightweight_default_and_maturity_modes() -> None:
    content = DOC.read_text()

    for phrase in [
        "New Projects",
        "Active Development Projects",
        "Mature or Production Projects",
        "memory lifecycle",
        "host doctor",
        "minimal hooks",
        "basic security checks",
        "changelog and session learning",
    ]:
        assert phrase in content


def test_developer_confidence_doc_points_to_real_proof_paths() -> None:
    content = DOC.read_text()
    paths = [
        "scripts/cos-doctor-memory-lifecycle.sh",
        "scripts/cos-doctor-tools.sh",
        "docs/manual-tests/first-run-onboarding.md",
        "docs/manual-tests/proof-paths.md",
        "docs/business/master-plan-checklist.md",
    ]

    for path in paths:
        assert path in content
        assert (PROJECT_ROOT / path).exists(), path


def test_developer_confidence_proof_path_executes_memory_doctor() -> None:
    env = os.environ.copy()
    env.pop("CLAUDE_PROJECT_DIR", None)
    env["COGNITIVE_OS_HARNESS"] = "codex"
    env["CODEX_PROJECT_DIR"] = str(PROJECT_ROOT)

    result = subprocess.run(
        [
            "bash",
            str(PROJECT_ROOT / "scripts" / "cos-doctor-memory-lifecycle.sh"),
            "--harness",
            "codex",
            "--skip-engram-start",
        ],
        cwd=str(PROJECT_ROOT),
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert "PASS session-resume detects and recovers pending tasks" in result.stdout
    assert "PASS session-changelog saves resumable changelog" in result.stdout
    assert "Result: PASS" in result.stdout
