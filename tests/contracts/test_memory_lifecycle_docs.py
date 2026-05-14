"""Documentation contracts for the memory lifecycle map."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


pytestmark = pytest.mark.contract

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOC = PROJECT_ROOT / "docs" / "04-Concepts" / "architecture" / "memory-lifecycle.md"


def test_memory_lifecycle_doc_is_linked_from_easy_entrypoints() -> None:
    rel = "docs/04-Concepts/architecture/memory-lifecycle.md"
    docs_rel = "architecture/memory-lifecycle.md"

    assert docs_rel in (PROJECT_ROOT / "docs" / "00-MOCs" / "entrypoints" / "README.md").read_text()
    assert rel in (PROJECT_ROOT / "AGENTS.md").read_text()


def test_memory_lifecycle_doc_maps_real_components() -> None:
    content = DOC.read_text()
    components = [
        "hooks/user-prompt-capture.sh",
        "hooks/pre-compaction-flush.sh",
        "hooks/session-learning.sh",
        "hooks/git-context-capture.sh",
        "hooks/session-changelog.sh",
        "hooks/engram-crystallize-on-session-end.sh",
        "hooks/session-resume.sh",
        "hooks/engram-daemon-launcher.sh",
        "lib/memory_retriever.py",
        "lib/engram_client.py",
        "lib/safe_engram.py",
        "lib/memory_scanner.py",
        "lib/anchored_summarizer.py",
        "scripts/cos-doctor-memory-lifecycle.sh",
        "scripts/cos-doctor-tools.sh",
    ]

    for component in components:
        assert component in content, component
        assert (PROJECT_ROOT / component).exists(), component


def test_memory_lifecycle_doc_points_to_executable_evidence() -> None:
    content = DOC.read_text()

    assert "PASS memory lifecycle doctor passed" in content
    assert "What \"Automatic\" Means" in content
    assert "Shell hooks cannot directly call" in content
    assert "mem_session_summary" in content
    assert "developers do not manually run memory hooks" in content
    assert "tests/contracts/test_memory_lifecycle_portability.py" in content
    assert "tests/behavior/test_cos_doctor_tools.py" in content


def test_documented_memory_lifecycle_command_executes_under_codex_env() -> None:
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
