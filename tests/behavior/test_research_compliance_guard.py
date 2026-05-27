from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / "hooks" / "research-compliance-guard.sh"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def _init_repo(repo: Path) -> Path:
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    return repo


def _run_hook(repo: Path) -> subprocess.CompletedProcess[str]:
    payload = json.dumps({"tool_input": {"command": "git commit -m test"}})
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(repo)
    return subprocess.run(
        ["bash", str(HOOK)],
        input=payload,
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


@pytest.mark.behavior
def test_research_compliance_guard_blocks_unbounded_proprietary_research(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    review = repo / "docs" / "02-research" / "tool-review.md"
    review.parent.mkdir(parents=True)
    review.write_text(
        "# Tool Review\n\nThe upstream project is proprietary and all rights reserved.\n",
        encoding="utf-8",
    )
    _git(repo, "add", str(review.relative_to(repo)))

    result = _run_hook(repo)

    assert result.returncode == 1
    assert "conceptual-only/no-reuse/clean-room boundary" in result.stderr


@pytest.mark.behavior
def test_research_compliance_guard_allows_conceptual_only_research_review(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    review = repo / "docs" / "02-research" / "tool-review.md"
    review.parent.mkdir(parents=True)
    review.write_text(
        "# Tool Review\n\nThe upstream project is proprietary and all rights reserved. "
        "Use as conceptual research only; clean-room implementation required; no reuse.\n",
        encoding="utf-8",
    )
    _git(repo, "add", str(review.relative_to(repo)))

    result = _run_hook(repo)

    assert result.returncode == 0, result.stderr


@pytest.mark.behavior
def test_research_compliance_guard_blocks_runtime_research_path_reference(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    source = repo / "scripts" / "build.py"
    source.parent.mkdir(parents=True)
    source.write_text('SOURCE = ".research/HireIQ"\n', encoding="utf-8")
    _git(repo, "add", str(source.relative_to(repo)))

    result = _run_hook(repo)

    assert result.returncode == 1
    assert "runtime code references research-only source/cache paths" in result.stderr
