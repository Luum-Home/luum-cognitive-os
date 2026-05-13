# SCOPE: os-only
"""Portability proofs for scripts/push_collision_detect.py — ADR-116 P4.2.

These tests run the CLI against a temporary, non-SO git repository to confirm
that the Python collision detector does not depend on any luum-agent-os runtime
state (no SO-specific env vars, no project-local config).

Three proofs:
  1. No unpushed commits → exit 0 (transparent in a clean repo).
  2. Falsification: below-threshold subject similarity → no collision flagged.
  3. Warn-mode exits 0 even when subjects collide (both in warn default mode).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DETECT_SCRIPT = REPO_ROOT / "scripts" / "push_collision_detect.py"

SCRUB_VARS = (
    "CI",
    "PYTEST_CURRENT_TEST",
    "COS_PUSH_COLLISION_MODE",
    "COGNITIVE_OS_SESSION_ID",
    "ORCHESTRATOR_MODE",
    "COGNITIVE_OS_PROJECT_DIR",
    "CODEX_PROJECT_DIR",
    "CLAUDE_PROJECT_DIR",
)


def _base_env(project: Path) -> dict[str, str]:
    env = os.environ.copy()
    for var in SCRUB_VARS:
        env.pop(var, None)
    # Provide a clean project dir pointing to the temp repo, not the SO
    env["COGNITIVE_OS_PROJECT_DIR"] = str(project)
    return env


def _init_repo_with_origin(path: Path) -> None:
    """Create a minimal git repo with a real origin remote."""
    origin_dir = path / "_origin"
    subprocess.run(["git", "init", "-b", "main", str(origin_dir)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(origin_dir), "config", "user.email", "test@x.com"], check=True)
    subprocess.run(["git", "-C", str(origin_dir), "config", "user.name", "Test"], check=True)
    (origin_dir / "seed.txt").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(origin_dir), "add", "seed.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(origin_dir), "commit", "-m", "seed"],
        check=True,
        capture_output=True,
    )

    subprocess.run(["git", "clone", str(origin_dir), str(path / "repo")], check=True, capture_output=True)
    repo = path / "repo"
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@x.com"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
    return repo  # type: ignore[return-value]


def _run_detect(
    project: Path,
    extra_args: list[str] | None = None,
    mode: str | None = None,
) -> subprocess.CompletedProcess[str]:
    env = _base_env(project)
    if mode is not None:
        env["COS_PUSH_COLLISION_MODE"] = mode
    args = [
        sys.executable,
        str(DETECT_SCRIPT),
        "--project-dir",
        str(project),
        "--upstream",
        "origin/main",
        "--since",
        "24 hours ago",
    ] + (extra_args or [])
    return subprocess.run(args, capture_output=True, text=True, env=env, timeout=30)


# ---------------------------------------------------------------------------
# Proof 1: No unpushed commits → exit 0
# ---------------------------------------------------------------------------


def test_clean_repo_exits_0(tmp_path: Path) -> None:
    """Portability: no unpushed commits → script exits 0 in a foreign repo."""
    repo = _init_repo_with_origin(tmp_path)
    # repo is in sync with origin — no commits ahead
    result = _run_detect(repo)
    assert result.returncode == 0, (
        f"portability: expected exit 0 (clean repo); got {result.returncode}\n"
        f"stderr: {result.stderr}\nstdout: {result.stdout}"
    )
    assert "PASS" in result.stdout


# ---------------------------------------------------------------------------
# Proof 2: Falsification — below-threshold subjects produce no collision
# ---------------------------------------------------------------------------


def test_below_threshold_no_collision(tmp_path: Path) -> None:
    """Portability falsification: dissimilar subjects must NOT be flagged."""
    repo = _init_repo_with_origin(tmp_path)
    # Make a local commit with a totally different subject from anything in origin
    (repo / "new.txt").write_text("new\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "new.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "feat: completely unique subject xyz987"],
        cwd=str(repo),
        check=True,
        capture_output=True,
    )
    # origin only has "seed" commit — not at all similar to "feat: completely unique..."
    result = _run_detect(repo)
    assert result.returncode == 0, (
        f"falsification: dissimilar subjects must not be flagged; "
        f"got {result.returncode}\nstderr: {result.stderr}"
    )
    # Must not mention a collision
    assert "collision" not in result.stderr.lower(), (
        f"falsification: no collision keyword expected in stderr; got: {result.stderr}"
    )


# ---------------------------------------------------------------------------
# Proof 3: Warn mode exits 0 even on collisions
# ---------------------------------------------------------------------------


def test_warn_mode_exits_0(tmp_path: Path) -> None:
    """Portability: warn mode must always exit 0 in a foreign repo (no blocking)."""
    repo = _init_repo_with_origin(tmp_path)
    # Make a local commit whose subject exactly matches the origin's seed commit
    # Note: origin has "seed" commit — our commit uses a near-identical short subject
    (repo / "extra.txt").write_text("extra\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "extra.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "seed"],
        cwd=str(repo),
        check=True,
        capture_output=True,
    )
    # Whether or not a collision is found, warn mode must exit 0
    result = _run_detect(repo, mode="warn")
    assert result.returncode == 0, (
        f"portability: warn mode must exit 0 even with subject collision in foreign repo; "
        f"got {result.returncode}\nstderr: {result.stderr}"
    )
