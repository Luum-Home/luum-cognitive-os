# SCOPE: os-only
"""Portability proofs for hooks/_lib/push-collision-check.sh — ADR-116 P4.2.

These tests invoke the shell lib against a temporary, non-SO git repository to
confirm that collision-detection logic does not depend on any luum-agent-os
runtime state, paths, or environment variables present only inside the SO.

Three proofs:
  1. No-collision → exit 0 in a foreign repo (lib is transparent when clean).
  2. Warn mode → exit 0 even when the Python script emits a WARN collision.
  3. Block mode → exit 2 when the Python script emits a BLOCK collision.

The lib is invoked by sourcing it in a bash subprocess and calling
run_push_collision_check directly, so the test is fully harness-agnostic.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from textwrap import dedent

REPO_ROOT = Path(__file__).resolve().parents[3]
LIB = REPO_ROOT / "hooks" / "_lib" / "push-collision-check.sh"
DETECT_SCRIPT = REPO_ROOT / "scripts" / "push_collision_detect.py"

SCRUB_VARS = (
    "CI",
    "PYTEST_CURRENT_TEST",
    "COS_PUSH_COLLISION_MODE",
    "COGNITIVE_OS_SESSION_ID",
    "ORCHESTRATOR_MODE",
)


def _base_env(project: Path) -> dict[str, str]:
    env = os.environ.copy()
    for var in SCRUB_VARS:
        env.pop(var, None)
    env.update(
        {
            "CLAUDE_PROJECT_DIR": str(project),
            "COGNITIVE_OS_PROJECT_DIR": str(project),
            "COGNITIVE_OS_HOOK_HEARTBEAT": "false",
        }
    )
    return env


def _init_repo(path: Path) -> None:
    """Initialise a minimal git repo with one commit and an origin remote stub."""
    subprocess.run(["git", "init", "-b", "main"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
    (path / "seed.txt").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "add", "seed.txt"], cwd=path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "initial commit"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    # Add a fake origin remote so git log origin/main doesn't error out
    origin_dir = path / "_origin"
    origin_dir.mkdir()
    subprocess.run(
        ["git", "clone", "--bare", str(path), str(origin_dir)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "remote", "add", "origin", str(origin_dir)],
        cwd=path,
        check=True,
    )
    subprocess.run(["git", "fetch", "origin"], cwd=path, check=True, capture_output=True)


def _run_lib(
    project: Path,
    mode: str | None = None,
    stub_detect_exit: int | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run run_push_collision_check via a bash wrapper.

    If stub_detect_exit is given, stub the Python detect script to exit with
    that code (bypassing real git operations for portability).
    """
    env = _base_env(project)
    if mode is not None:
        env["COS_PUSH_COLLISION_MODE"] = mode

    # Build stub script if requested
    stub_path = None
    if stub_detect_exit is not None:
        stub_path = project / "_stub_detect.py"
        stub_path.write_text(
            dedent(
                f"""\
                #!/usr/bin/env python3
                import sys
                if stub_detect_exit != 0:
                    print("push-collision-check: [WARN] Subject collision detected (exact match): "
                          "stub stub stub", file=sys.stderr)
                sys.exit({stub_detect_exit})
                """
            ),
            encoding="utf-8",
        )

    # Build a small bash driver that sources the lib and calls run_push_collision_check
    # We override the script location when stubbing.
    if stub_path is not None:
        # Patch the script resolution inside run_push_collision_check by placing
        # the stub at the expected path inside the foreign repo.
        scripts_dir = project / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        stub_dest = scripts_dir / "push_collision_detect.py"
        stub_dest.write_text(stub_path.read_text(encoding="utf-8"), encoding="utf-8")

    driver = dedent(
        f"""\
        #!/usr/bin/env bash
        set -uo pipefail
        source '{LIB}'
        run_push_collision_check '{project}'
        """
    )
    result = subprocess.run(
        ["bash", "-c", driver],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
    return result


# ---------------------------------------------------------------------------
# Proof 1: No collision → exit 0 in a foreign repo
# ---------------------------------------------------------------------------


def test_no_collision_exits_0_in_foreign_repo(tmp_path: Path) -> None:
    """Portability proof: lib exits 0 when no subject collision is detected."""
    _init_repo(tmp_path)
    # Stub detect script exits 0 (no collision)
    result = _run_lib(tmp_path, mode="warn", stub_detect_exit=0)
    assert result.returncode == 0, (
        f"portability: expected exit 0 (no collision); got {result.returncode}\n"
        f"stderr: {result.stderr}\nstdout: {result.stdout}"
    )


# ---------------------------------------------------------------------------
# Proof 2: Warn mode → exit 0 even with collision
# ---------------------------------------------------------------------------


def test_warn_mode_exits_0_on_collision_in_foreign_repo(tmp_path: Path) -> None:
    """Portability proof: warn mode exits 0 even when detect script signals collision."""
    _init_repo(tmp_path)
    # Stub detect script exits 1 (simulates collision warning output via stderr)
    result = _run_lib(tmp_path, mode="warn", stub_detect_exit=1)
    assert result.returncode == 0, (
        f"portability: warn mode must exit 0 in foreign repo; got {result.returncode}\n"
        f"stderr: {result.stderr}"
    )


# ---------------------------------------------------------------------------
# Proof 3: Block mode → exit 2 when detect script returns collision
# ---------------------------------------------------------------------------


def test_block_mode_exits_2_on_collision_in_foreign_repo(tmp_path: Path) -> None:
    """Portability proof: block mode exits 2 when detect script exits 2."""
    _init_repo(tmp_path)
    # Stub detect script exits 2 (block-level collision)
    result = _run_lib(tmp_path, mode="block", stub_detect_exit=2)
    assert result.returncode == 2, (
        f"portability: block mode must exit 2 on collision in foreign repo; "
        f"got {result.returncode}\nstderr: {result.stderr}"
    )
