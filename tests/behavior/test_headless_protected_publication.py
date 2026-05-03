"""Behavior tests for ADR-091 headless protected-publication proof path."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts" / "cos_headless_publication.py"
WRAPPER = PROJECT_ROOT / "scripts" / "cos-headless-publication"


def run_checker(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(SCRIPT), *args, "--json"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def payload(result: subprocess.CompletedProcess[str]) -> dict:
    assert result.stdout, result.stderr
    return json.loads(result.stdout)


def test_headless_direct_main_publication_is_blocked() -> None:
    result = run_checker(
        "--branch",
        "feature/repair-123",
        "--actor-mode",
        "headless",
        "--publication-target",
        "main",
    )

    data = payload(result)
    assert result.returncode == 2
    assert data["decision"] == "block"
    assert data["allowed"] is False
    assert "unattended headless workers" in data["reason"]
    assert set(data["required_landing_modes"]) == {"human_approved", "merge_queue"}


def test_headless_feature_branch_output_is_allowed_as_branch_publication() -> None:
    result = run_checker(
        "--branch",
        "feature/repair-123",
        "--actor-mode",
        "headless",
        "--publication-target",
        "branch",
    )

    data = payload(result)
    assert result.returncode == 0
    assert data["decision"] == "allow"
    assert data["allowed"] is True
    assert "patch or non-protected branch" in data["reason"]


def test_headless_patch_output_is_allowed_without_direct_main_publication() -> None:
    result = run_checker(
        "--branch",
        "feature/repair-123",
        "--actor-mode",
        "headless",
        "--publication-target",
        "patch",
    )

    data = payload(result)
    assert result.returncode == 0
    assert data["decision"] == "allow"
    assert data["allowed"] is True


def test_headless_main_with_merge_queue_is_allowed() -> None:
    result = run_checker(
        "--branch",
        "feature/repair-123",
        "--actor-mode",
        "headless",
        "--publication-target",
        "main",
        "--landing-mode",
        "merge_queue",
    )

    data = payload(result)
    assert result.returncode == 0
    assert data["decision"] == "allow"
    assert data["allowed"] is True
    assert data["landing_mode"] == "merge_queue"
    assert "protected landing mode" in data["reason"]


def test_headless_main_with_human_approval_is_allowed() -> None:
    result = run_checker(
        "--branch",
        "feature/repair-123",
        "--actor-mode",
        "headless",
        "--publication-target",
        "master",
        "--landing-mode",
        "human_approved",
    )

    data = payload(result)
    assert result.returncode == 0
    assert data["decision"] == "allow"
    assert data["allowed"] is True
    assert data["landing_mode"] == "human_approved"


def test_interactive_operator_main_is_warn_allowed_by_local_semantics() -> None:
    result = run_checker(
        "--branch",
        "main",
        "--actor-mode",
        "interactive",
        "--publication-target",
        "main",
    )

    data = payload(result)
    assert result.returncode == 0
    assert data["decision"] == "warn"
    assert data["allowed"] is True
    assert "existing local semantics" in data["reason"]
    assert "remote branch protection" in data["recommendation"]


def test_wrapper_invokes_checker() -> None:
    result = subprocess.run(
        [
            str(WRAPPER),
            "--branch",
            "feature/repair-123",
            "--actor-mode",
            "headless",
            "--publication-target",
            "main",
            "--landing-mode",
            "merge_queue",
            "--json",
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    data = payload(result)
    assert result.returncode == 0
    assert data["decision"] == "allow"
