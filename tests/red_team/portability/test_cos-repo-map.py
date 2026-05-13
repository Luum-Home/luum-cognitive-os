# SCOPE: os-only
"""Portability probes for scripts/cos-repo-map.

Bilateral assertion: invoking the script via python3 on any harness with
a query argument produces JSON on stdout containing the repo-map packet
schema (versioned), governance buckets, and a budget block.

Falsification probes:
  - Missing required positional 'query' must exit non-zero (argparse).
  - Token budget passed via --max-tokens must be honored within reasonable
    overshoot (a stub ignoring the flag would fail).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "cos-repo-map"


def _seed_synth_project(root: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "t@e.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=root, check=True)
    (root / "hooks").mkdir()
    (root / "hooks" / "alpha.sh").write_text("#!/bin/sh\necho alpha\n")
    (root / "module.py").write_text("def helper():\n    return 1\n")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "seed"], cwd=root, check=True, capture_output=True
    )


def test_cos_repo_map_runs_and_returns_versioned_packet(tmp_path: Path) -> None:
    """Bilateral: script returns a versioned repo-map packet on any harness."""
    _seed_synth_project(tmp_path)
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "helper",
            "--project-dir",
            str(tmp_path),
            "--max-tokens",
            "400",
        ],
        text=True,
        capture_output=True,
        check=True,
        timeout=30,
    )
    payload = json.loads(result.stdout)
    assert payload["schema_version"]
    assert payload["query"] == "helper"
    assert "governance" in payload
    assert payload["budget"]["max_tokens"] == 400


def test_cos_repo_map_requires_query_argument() -> None:
    """Falsification: argparse must reject invocation with no positional query."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    assert result.returncode != 0, (
        "falsification: missing query must produce non-zero exit"
    )


def test_cos_repo_map_honors_max_tokens_flag(tmp_path: Path) -> None:
    """Falsification: --max-tokens must constrain budget (stub would ignore)."""
    _seed_synth_project(tmp_path)
    # Add many extra files so the budget bites.
    for i in range(40):
        (tmp_path / f"extra_{i}.py").write_text(f"def fn_{i}():\n    pass\n")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "extras"], cwd=tmp_path, check=True, capture_output=True
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "fn",
            "--project-dir",
            str(tmp_path),
            "--max-tokens",
            "120",
        ],
        text=True,
        capture_output=True,
        check=True,
        timeout=30,
    )
    payload = json.loads(result.stdout)
    budget = payload["budget"]
    used = budget.get("used_tokens", budget.get("estimated_tokens"))
    assert used is not None, f"budget block missing token counter: {budget}"
    assert used <= 400, (
        f"falsification: --max-tokens 120 ignored (used={used})"
    )
