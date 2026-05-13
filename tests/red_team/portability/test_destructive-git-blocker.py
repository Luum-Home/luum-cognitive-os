# SCOPE: os-only
"""Portability probes for hooks/destructive-git-blocker.sh — ADR-116 P3.2 WIP guard.

These tests run the hook against a temporary, non-SO git repository to prove that
the WIP-guard logic does not depend on any repository-local runtime state from the
luum-agent-os project itself.

Paired with: hooks/destructive-git-blocker.sh  (# SCOPE: os-only)
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
HOOK = REPO_ROOT / "hooks" / "destructive-git-blocker.sh"

SCRUB_VARS = (
    "CI",
    "PYTEST_CURRENT_TEST",
    "COS_GIT_BYPASS",
    "COS_ALLOW_DESTRUCTIVE_GIT",
    "COS_ALLOW_RESET_OVER_WIP",
    "COS_AUTO_STASH_BEFORE_RESET",
    "CLAUDE_AGENT_ID",
    "COGNITIVE_OS_SESSION_ID",
    "ORCHESTRATOR_MODE",
)


def _run(
    command: str,
    project: Path,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
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
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )


def _init_repo(path: Path) -> None:
    """Initialise a minimal git repo with one committed file."""
    subprocess.run(["git", "init", "-b", "main"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
    (path / "seed.txt").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "add", "seed.txt"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "seed"], cwd=path, check=True, capture_output=True)


def _dirty(path: Path) -> None:
    """Leave an uncommitted modification so _has_wip() returns true."""
    (path / "seed.txt").write_text("dirty\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Portability: WIP guard blocks in a non-SO project
# ---------------------------------------------------------------------------


def test_pull_rebase_with_wip_blocked_in_foreign_repo(tmp_path: Path) -> None:
    """WIP guard blocks git pull --rebase in a project with no SO runtime state."""
    _init_repo(tmp_path)
    _dirty(tmp_path)
    result = _run("git pull --rebase origin main", tmp_path)
    assert result.returncode == 2, (
        f"portability: expected WIP-guard block in foreign repo; got {result.returncode}\n"
        f"{result.stderr}"
    )
    assert "WIP GUARD BLOCKED" in result.stderr


def test_rebase_with_wip_blocked_in_foreign_repo(tmp_path: Path) -> None:
    """WIP guard blocks git rebase in a project with no SO runtime state."""
    _init_repo(tmp_path)
    _dirty(tmp_path)
    result = _run("git rebase main", tmp_path)
    assert result.returncode == 2, (
        f"portability: expected WIP-guard block in foreign repo; got {result.returncode}\n"
        f"{result.stderr}"
    )
    assert "WIP GUARD BLOCKED" in result.stderr


def test_fetch_reset_chain_with_wip_blocked_in_foreign_repo(tmp_path: Path) -> None:
    """fetch+reset --hard chain with WIP is blocked in a foreign repo."""
    _init_repo(tmp_path)
    _dirty(tmp_path)
    result = _run("git fetch origin && git reset --hard origin/main", tmp_path)
    assert result.returncode == 2, (
        f"portability: expected block for fetch+reset chain; got {result.returncode}\n"
        f"{result.stderr}"
    )
    assert "BLOCKED" in result.stderr


def test_pull_rebase_clean_tree_standard_block_in_foreign_repo(tmp_path: Path) -> None:
    """On a clean tree, pull --rebase still hits the standard destructive-op block."""
    _init_repo(tmp_path)
    result = _run("git pull --rebase origin main", tmp_path)
    assert result.returncode == 2, (
        f"portability: clean-tree pull --rebase must still be blocked; got {result.returncode}\n"
        f"{result.stderr}"
    )
    assert "BLOCKED" in result.stderr
    # Standard block path — WIP-guard-specific message should NOT appear
    assert "WIP GUARD BLOCKED" not in result.stderr


def test_cos_allow_reset_over_wip_bypass_and_log_in_foreign_repo(tmp_path: Path) -> None:
    """COS_ALLOW_RESET_OVER_WIP=1 bypass is accepted and logged in a foreign repo."""
    _init_repo(tmp_path)
    _dirty(tmp_path)
    result = _run(
        "git pull --rebase origin main",
        tmp_path,
        extra_env={"COS_ALLOW_RESET_OVER_WIP": "1"},
    )
    assert result.returncode == 0, (
        f"portability: expected bypass exit 0; got {result.returncode}\n{result.stderr}"
    )
    assert "WIP-GUARD BYPASS ACCEPTED" in result.stderr
    bypass_log = tmp_path / ".cognitive-os" / "metrics" / "destructive-git-bypass.jsonl"
    assert bypass_log.exists(), "bypass log must be created in foreign project"
    entry = json.loads(bypass_log.read_text().splitlines()[-1])
    assert entry["event"] == "wip_guard_bypass"
    assert entry["bypass_reason"] == "COS_ALLOW_RESET_OVER_WIP"
    assert isinstance(entry.get("wip_files"), list)
    assert len(entry["wip_files"]) >= 1


# ---------------------------------------------------------------------------
# Falsification: WIP-guard bypass must NOT silently succeed without the env var
# ---------------------------------------------------------------------------


def test_falsification_wip_guard_not_bypassed_without_env_var(tmp_path: Path) -> None:
    """Without COS_ALLOW_RESET_OVER_WIP the WIP guard must block, not allow."""
    _init_repo(tmp_path)
    _dirty(tmp_path)
    result = _run("git pull --rebase origin main", tmp_path)
    assert result.returncode != 0, (
        "falsification: WIP guard must NOT allow pull --rebase without bypass env var"
    )
    bypass_log = tmp_path / ".cognitive-os" / "metrics" / "destructive-git-bypass.jsonl"
    assert not bypass_log.exists(), (
        "falsification: bypass log must NOT be created when block fires"
    )
