"""Documentation contract for the cross-harness transparency status."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


pytestmark = pytest.mark.contract

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOC = PROJECT_ROOT / "docs" / "04-Concepts" / "architecture" / "harness-transparency-status.md"


def test_harness_transparency_status_doc_is_linked_from_entrypoints() -> None:
    assert "architecture/harness-transparency-status.md" in (
        PROJECT_ROOT / "docs" / "00-MOCs" / "entrypoints" / "README.md"
    ).read_text()
    assert "Harness transparency status is documented honestly" in (
        PROJECT_ROOT / "docs" / "08-References" / "business" / "master-plan-checklist.md"
    ).read_text()


def test_harness_transparency_status_states_honest_boundary() -> None:
    content = " ".join(DOC.read_text().split())

    required_phrases = [
        "Developers get automatic session-memory protection and fallback persistence",
        "Full transparent cross-harness operation",
        "still requires canonical hook projection",
        "canonical hook projection",
        "portable skill execution",
        "harness-neutral sub-agent spawning",
        "A shell hook cannot directly invoke the in-process MCP tool",
        "not as a claim that shell hooks can call in-process MCP tools directly",
    ]

    for phrase in required_phrases:
        assert phrase in content


def test_harness_transparency_status_maps_adr_064_surfaces() -> None:
    content = DOC.read_text()

    for phrase in [
        "Surface 2 — Canonical hook projection",
        "Surface 3 — Portable skill execution",
        "Surface 4 — Harness-neutral sub-agent spawning",
        ".cognitive-os/plans/architecture/adr-064-implementation-plan.md",
        ".claude/settings.json",
        ".codex/hooks.json",
        "cos-skill run <name>",
        "cos-agent spawn --task",
    ]:
        assert phrase in content

    assert (
        PROJECT_ROOT
        / ".cognitive-os"
        / "plans"
        / "architecture"
        / "adr-064-implementation-plan.md"
    ).exists()


def test_harness_transparency_status_points_to_real_memory_components() -> None:
    content = DOC.read_text()
    components = [
        "hooks/engram-daemon-launcher.sh",
        "hooks/session-init.sh",
        "hooks/session-resume.sh",
        "hooks/user-prompt-capture.sh",
        "hooks/session-learning.sh",
        "hooks/git-context-capture.sh",
        "hooks/session-changelog.sh",
        "hooks/engram-crystallize-on-session-end.sh",
        "scripts/cos-doctor-memory-lifecycle.sh",
        "scripts/cos-doctor-tools.sh",
    ]

    for component in components:
        assert component in content
        assert (PROJECT_ROOT / component).exists(), component


def test_documented_codex_memory_proof_path_executes() -> None:
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
