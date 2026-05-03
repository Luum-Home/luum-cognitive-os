"""Unit tests for hooks/destructive-git-blocker.sh — ADR-055b block elevation.

Verifies the block-by-default semantics introduced in ADR-055b (decision #6,
r5-stash-residue closure):

- Destructive git ops are BLOCKED in BOTH agent and user context
- Overrides: COS_ALLOW_DESTRUCTIVE_GIT=1 env, `--allow-destructive` inline flag
- Bypass contexts: CI=1, PYTEST_CURRENT_TEST, COS_GIT_BYPASS=1
- New ops covered: git branch -D, git rebase, git pull --rebase, protected branch writes
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HOOK = PROJECT_ROOT / "hooks" / "destructive-git-blocker.sh"

# Base env: scrub every variable the hook checks for bypass/override, so each
# test starts from a clean baseline and only re-adds what it needs.
SCRUB_VARS = (
    "CI",
    "PYTEST_CURRENT_TEST",
    "COS_GIT_BYPASS",
    "COS_ALLOW_DESTRUCTIVE_GIT",
    "CLAUDE_AGENT_ID",
    "COGNITIVE_OS_SESSION_ID",
    "ORCHESTRATOR_MODE",
)


def _run(
    command: str,
    tmp_path: Path,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
    env = os.environ.copy()
    for var in SCRUB_VARS:
        env.pop(var, None)
    env.update({
        "CLAUDE_PROJECT_DIR": str(tmp_path),
        "COGNITIVE_OS_PROJECT_DIR": str(tmp_path),
        "COGNITIVE_OS_HOOK_HEARTBEAT": "false",
    })
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )


# ---------------------------------------------------------------------------
# Destructive ops blocked in user context (ADR-055b elevation)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "command,expected_op_fragment",
    [
        ("git reset --hard HEAD~1", "git reset"),
        ("git reset --soft HEAD~1", "git reset"),
        ("git reset HEAD~1", "git reset"),
        ("git pull --rebase origin main", "git pull --rebase"),
        ("git rebase main", "git rebase"),
        ("git checkout -- src/foo.py", "git checkout --"),
        ("git checkout HEAD -- src/foo.py", "git checkout --"),
        ("git clean -fd", "git clean -f"),
        ("git clean -fdx", "git clean -f"),
        ("git branch -D feature-x", "git branch -D"),
        ("git stash pop", "git stash pop"),
        ("git stash drop", "git stash drop"),
        ("git stash apply", "git stash apply"),
        ("git rebase --abort", "git rebase"),
        ("git restore src/foo.py", "git restore"),
        ("git revert HEAD", "git revert"),
        ("git worktree add ../foo", "git worktree"),
        ("git worktree remove ../foo", "git worktree"),
        ("git worktree move ../foo ../bar", "git worktree"),
        ("git worktree prune", "git worktree"),
        ("git worktree repair", "git worktree"),
        ("git worktree lock ../foo", "git worktree"),
        ("git worktree unlock ../foo", "git worktree"),
    ],
)
def test_user_context_blocks_destructive_op(
    tmp_path: Path, command: str, expected_op_fragment: str
):
    """Every destructive op pattern is blocked (exit 2) in user context."""
    result = _run(command, tmp_path)
    assert result.returncode == 2, (
        f"expected block (exit 2) for `{command}`, got {result.returncode}\n"
        f"stderr={result.stderr}"
    )
    assert "BLOCKED" in result.stderr
    assert expected_op_fragment in result.stderr


# ---------------------------------------------------------------------------
# Override mechanisms
# ---------------------------------------------------------------------------


def test_env_override_allows_destructive_op(tmp_path: Path):
    """COS_ALLOW_DESTRUCTIVE_GIT=1 permits the command (exit 0)."""
    result = _run(
        "git reset --hard HEAD~1",
        tmp_path,
        extra_env={"COS_ALLOW_DESTRUCTIVE_GIT": "1"},
    )
    assert result.returncode == 0, result.stderr
    assert "OVERRIDE ACCEPTED" in result.stderr


def test_inline_flag_override_allows_destructive_op(tmp_path: Path):
    """`--allow-destructive` token in command permits (exit 0)."""
    result = _run("git reset --hard HEAD~1 --allow-destructive", tmp_path)
    assert result.returncode == 0, result.stderr
    assert "OVERRIDE ACCEPTED" in result.stderr


def test_inline_flag_override_anywhere_in_command(tmp_path: Path):
    """Flag is recognized as a whole token regardless of position."""
    result = _run("git --allow-destructive reset --hard HEAD~1", tmp_path)
    assert result.returncode == 0, result.stderr


def test_env_override_non_one_value_still_blocks(tmp_path: Path):
    """Only literal COS_ALLOW_DESTRUCTIVE_GIT=1 unlocks; other truthy strings block."""
    result = _run(
        "git reset --hard HEAD~1",
        tmp_path,
        extra_env={"COS_ALLOW_DESTRUCTIVE_GIT": "true"},
    )
    assert result.returncode == 2, (
        f"only literal '1' should override; got {result.returncode}\n{result.stderr}"
    )


# ---------------------------------------------------------------------------
# Bypass contexts (SO-internal — not user-initiated)
# ---------------------------------------------------------------------------


def test_ci_bypass_allows_destructive_op(tmp_path: Path):
    """CI=1 bypass lets CI jobs reset/checkout without override flags."""
    result = _run(
        "git reset --hard HEAD~1",
        tmp_path,
        extra_env={"CI": "1"},
    )
    assert result.returncode == 0, result.stderr


def test_ci_bypass_true_value_also_works(tmp_path: Path):
    """CI='true' (GitHub Actions default) also bypasses."""
    result = _run(
        "git reset --hard HEAD~1",
        tmp_path,
        extra_env={"CI": "true"},
    )
    assert result.returncode == 0, result.stderr


def test_pytest_bypass_allows_destructive_op(tmp_path: Path):
    """PYTEST_CURRENT_TEST set → bypass (tests may clean up state)."""
    result = _run(
        "git reset --hard HEAD~1",
        tmp_path,
        extra_env={"PYTEST_CURRENT_TEST": "some::test"},
    )
    assert result.returncode == 0, result.stderr


def test_cos_git_bypass_allows_destructive_op(tmp_path: Path):
    """COS_GIT_BYPASS=1 for reaper/watchdog/sandbox contexts."""
    result = _run(
        "git reset --hard HEAD~1",
        tmp_path,
        extra_env={"COS_GIT_BYPASS": "1"},
    )
    assert result.returncode == 0, result.stderr


# ---------------------------------------------------------------------------
# Safe ops and non-git commands pass through silently
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        "git status",
        "git diff",
        "git log --oneline -5",
        "git show HEAD",
        "git stash list",
        "git worktree list",
        "git worktree list --porcelain",
        "git branch --list",  # non-destructive (no -D)
        "ls -la",
        "pwd",
    ],
)
def test_safe_ops_pass_through(tmp_path: Path, command: str):
    """Safe commands exit 0 with no BLOCKED message."""
    result = _run(command, tmp_path)
    assert result.returncode == 0, (
        f"expected pass-through for `{command}`, got {result.returncode}\n"
        f"stderr={result.stderr}"
    )
    assert "BLOCKED" not in result.stderr


def test_commit_message_mentions_worktree_without_blocking(tmp_path: Path):
    """Semantic parsing must not treat commit prose as a git worktree op."""
    result = _run("git commit -m 'docs: mention git worktree remove guard'", tmp_path)
    assert result.returncode == 0, result.stderr
    assert "BLOCKED" not in result.stderr


def test_echoed_git_worktree_text_is_not_operator_intent(tmp_path: Path):
    """Substring-only matching must not block non-git commands containing git words."""
    result = _run("printf '%s\\n' 'git worktree remove ../stale'", tmp_path)
    assert result.returncode == 0, result.stderr
    assert "BLOCKED" not in result.stderr


# ---------------------------------------------------------------------------
# Override error-message contents (human-friendly guidance)
# ---------------------------------------------------------------------------


def test_block_message_includes_rationale(tmp_path: Path):
    result = _run("git stash pop", tmp_path)
    assert result.returncode == 2
    assert "Rationale:" in result.stderr
    # Specific rationale for stash ops mentions r5
    assert "r5" in result.stderr.lower() or "stash" in result.stderr.lower()


def test_block_message_includes_override_instructions(tmp_path: Path):
    result = _run("git reset --hard", tmp_path)
    assert result.returncode == 2
    assert "COS_ALLOW_DESTRUCTIVE_GIT" in result.stderr
    assert "--allow-destructive" in result.stderr


# ---------------------------------------------------------------------------
# JSONL audit trail
# ---------------------------------------------------------------------------


def test_user_context_block_is_logged(tmp_path: Path):
    result = _run("git stash pop", tmp_path)
    assert result.returncode == 2
    log = tmp_path / ".cognitive-os" / "metrics" / "git-op-blocks.jsonl"
    assert log.exists(), f"block log missing: {log}"
    lines = [l for l in log.read_text().splitlines() if l.strip()]
    entry = json.loads(lines[-1])
    assert entry["event"] == "blocked"
    assert entry["context"] == "user"


def test_override_is_logged_with_reason(tmp_path: Path):
    result = _run(
        "git reset --hard",
        tmp_path,
        extra_env={"COS_ALLOW_DESTRUCTIVE_GIT": "1"},
    )
    assert result.returncode == 0
    log = tmp_path / ".cognitive-os" / "metrics" / "git-op-blocks.jsonl"
    assert log.exists()
    lines = [l for l in log.read_text().splitlines() if l.strip()]
    entry = json.loads(lines[-1])
    assert entry["event"] == "override"
    assert entry["reason"] == "session_env"


def test_bypass_is_logged(tmp_path: Path):
    result = _run(
        "git reset --hard",
        tmp_path,
        extra_env={"CI": "1"},
    )
    assert result.returncode == 0
    log = tmp_path / ".cognitive-os" / "metrics" / "git-op-blocks.jsonl"
    assert log.exists()
    lines = [l for l in log.read_text().splitlines() if l.strip()]
    entry = json.loads(lines[-1])
    assert entry["event"] == "bypassed"
    assert entry["reason"] == "so_internal_context"




def _init_repo_on_branch(path: Path, branch: str = "main") -> None:
    subprocess.run(["git", "init", "-b", branch], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=path, check=True)
    (path / "README.md").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "seed"], cwd=path, check=True, capture_output=True, text=True)


def test_commit_on_main_is_blocked_until_session_branch(tmp_path: Path):
    _init_repo_on_branch(tmp_path, "main")
    result = _run("git commit -m change", tmp_path)
    assert result.returncode == 2, result.stderr
    assert "protected shared branch" in result.stderr or "session branch" in result.stderr


def test_push_on_master_is_blocked_until_session_branch(tmp_path: Path):
    _init_repo_on_branch(tmp_path, "master")
    result = _run("git push origin master", tmp_path)
    assert result.returncode == 2, result.stderr
    assert "session branch" in result.stderr


def test_commit_on_session_branch_is_allowed(tmp_path: Path):
    _init_repo_on_branch(tmp_path, "main")
    subprocess.run(["git", "switch", "-c", "session/test-work"], cwd=tmp_path, check=True, capture_output=True, text=True)
    result = _run("git commit -m change", tmp_path)
    assert result.returncode == 0, result.stderr


def test_main_branch_override_allows_commit(tmp_path: Path):
    _init_repo_on_branch(tmp_path, "main")
    result = _run("git commit -m change --allow-main-branch", tmp_path)
    assert result.returncode == 0, result.stderr
    assert "OVERRIDE ACCEPTED" in result.stderr

# ---------------------------------------------------------------------------
# ISSUE 1: Force-push blocking (git push --force / git push -f)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        "git push --force",
        "git push -f",
        "git push origin -f main",
        "git push origin main --force",
        "git push --force origin",
    ],
)
def test_force_push_is_blocked(tmp_path: Path, command: str):
    """git push --force and -f variants are blocked (exit 2) in user context."""
    result = _run(command, tmp_path)
    assert result.returncode == 2, (
        f"expected block (exit 2) for `{command}`, got {result.returncode}\n"
        f"stderr={result.stderr}"
    )
    assert "BLOCKED" in result.stderr
    assert "force" in result.stderr.lower()


@pytest.mark.parametrize(
    "command",
    [
        "git push --force-with-lease",
        "git push --force-with-lease=ref:abc123",
        "git push origin main",
        "git fetch -f",  # -f on non-push command
    ],
)
def test_force_push_safe_alternatives_pass_through(tmp_path: Path, command: str):
    """--force-with-lease and normal push are allowed; git fetch -f is not a push."""
    result = _run(command, tmp_path)
    assert result.returncode == 0, (
        f"expected pass-through for `{command}`, got {result.returncode}\n"
        f"stderr={result.stderr}"
    )
    assert "BLOCKED" not in result.stderr


def test_allow_force_push_flag_overrides_block(tmp_path: Path):
    """--allow-force-push inline flag bypasses the force-push block."""
    result = _run("git push --force --allow-force-push", tmp_path)
    assert result.returncode == 0, result.stderr
    assert "OVERRIDE ACCEPTED" in result.stderr


def test_force_push_block_message_suggests_lease(tmp_path: Path):
    """Block message for force-push suggests --force-with-lease as safer alternative."""
    result = _run("git push --force", tmp_path)
    assert result.returncode == 2
    assert "force-with-lease" in result.stderr


def test_force_push_block_is_logged(tmp_path: Path):
    """Force-push block is written to the JSONL audit log."""
    result = _run("git push -f", tmp_path)
    assert result.returncode == 2
    log = tmp_path / ".cognitive-os" / "metrics" / "git-op-blocks.jsonl"
    assert log.exists(), f"block log missing: {log}"
    lines = [ln for ln in log.read_text().splitlines() if ln.strip()]
    entry = json.loads(lines[-1])
    assert entry["event"] == "blocked"
    assert entry["context"] == "user"
    assert "force" in entry["op"].lower()


# ---------------------------------------------------------------------------
# ISSUE 2: Commit-message false-positive fix
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        'git commit -m "feat: documents git stash pop ops"',
        'git commit -m "fix: git reset --hard was previously broken"',
        'git commit -m "docs: explain git stash drop behavior"',
        "git commit -m 'chore: remove git restore usage from scripts'",
        'git commit --no-edit -m "refactor: replace git checkout -- with git restore"',
    ],
)
def test_commit_message_mentioning_destructive_op_is_not_blocked(
    tmp_path: Path, command: str
):
    """Destructive-op names mentioned inside -m '...' message bodies must NOT block."""
    result = _run(command, tmp_path)
    assert result.returncode == 0, (
        f"false-positive block for commit message: `{command}`\n"
        f"stderr={result.stderr}"
    )
    assert "BLOCKED" not in result.stderr


def test_genuine_destructive_op_after_commit_message_is_still_blocked(tmp_path: Path):
    """A real destructive op following a commit command is still caught (pipeline)."""
    command = 'git commit -m "chore: cleanup" && git stash pop'
    result = _run(command, tmp_path)
    assert result.returncode == 2, (
        f"expected block for piped stash pop, got {result.returncode}\n"
        f"stderr={result.stderr}"
    )
    assert "BLOCKED" in result.stderr


# ---------------------------------------------------------------------------
# ADR-116 P3.2: WIP-guard cascade protection
# ---------------------------------------------------------------------------

def _init_dirty_repo(path: Path) -> None:
    """Create a git repo with one committed file and one uncommitted modification."""
    subprocess.run(["git", "init", "-b", "main"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
    (path / "base.py").write_text("x = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "base.py"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "seed"], cwd=path, check=True, capture_output=True)
    # Leave an uncommitted change — simulates in-flight sub-agent edit
    (path / "base.py").write_text("x = 2\n", encoding="utf-8")


def _init_clean_repo(path: Path) -> None:
    """Create a git repo with no uncommitted changes."""
    subprocess.run(["git", "init", "-b", "main"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
    (path / "base.py").write_text("x = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "base.py"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "seed"], cwd=path, check=True, capture_output=True)


def test_pull_rebase_with_wip_is_blocked(tmp_path: Path) -> None:
    """git pull --rebase with WIP in working tree is blocked (WIP guard)."""
    _init_dirty_repo(tmp_path)
    result = _run("git pull --rebase origin main", tmp_path)
    assert result.returncode == 2, (
        f"expected WIP-guard block (exit 2), got {result.returncode}\n{result.stderr}"
    )
    assert "WIP GUARD BLOCKED" in result.stderr
    assert "base.py" in result.stderr


def test_pull_rebase_without_wip_falls_through_to_standard_block(tmp_path: Path) -> None:
    """git pull --rebase on a clean tree still hits the standard destructive-op block.

    The WIP guard does NOT make pull --rebase unconditionally safe; it only
    injects the WIP-specific diagnostics when WIP is present.  The standard
    block still fires because pull --rebase is in DESTRUCTIVE_PATTERN.
    """
    _init_clean_repo(tmp_path)
    result = _run("git pull --rebase origin main", tmp_path)
    # Must still be blocked — either by WIP guard (exit 2) or standard block (exit 2)
    assert result.returncode == 2, (
        f"expected block on clean tree, got {result.returncode}\n{result.stderr}"
    )
    assert "BLOCKED" in result.stderr
    # WIP-specific message should NOT appear because there is no WIP
    assert "WIP GUARD BLOCKED" not in result.stderr


def test_rebase_main_with_wip_is_blocked(tmp_path: Path) -> None:
    """git rebase main with WIP triggers the WIP guard."""
    _init_dirty_repo(tmp_path)
    result = _run("git rebase main", tmp_path)
    assert result.returncode == 2, (
        f"expected WIP-guard block (exit 2), got {result.returncode}\n{result.stderr}"
    )
    assert "WIP GUARD BLOCKED" in result.stderr


def test_fetch_reset_hard_chain_with_wip_is_blocked(tmp_path: Path) -> None:
    """git fetch && git reset --hard origin/main with WIP is blocked by WIP guard."""
    _init_dirty_repo(tmp_path)
    result = _run("git fetch origin && git reset --hard origin/main", tmp_path)
    assert result.returncode == 2, (
        f"expected WIP-guard block (exit 2), got {result.returncode}\n{result.stderr}"
    )
    assert "BLOCKED" in result.stderr


def test_today_incident_sequence_is_blocked(tmp_path: Path) -> None:
    """Exact today-incident: git pull --rebase origin main while orchestrator_verify.py is modified.

    Reflog evidence: HEAD@{1}: pull --rebase origin main (pick): fix(safety): ...
    The modified file simulates packages/verification-audit/lib/orchestrator_verify.py.
    """
    _init_dirty_repo(tmp_path)
    # Simulate the exact file from the incident
    wip_file = tmp_path / "packages" / "verification-audit" / "lib"
    wip_file.mkdir(parents=True)
    (wip_file / "orchestrator_verify.py").write_text(
        "# in-flight sub-agent edit\n", encoding="utf-8"
    )
    result = _run("git pull --rebase origin main", tmp_path)
    assert result.returncode == 2, (
        f"today-incident sequence must be blocked; got {result.returncode}\n{result.stderr}"
    )
    assert "WIP GUARD BLOCKED" in result.stderr


def test_wip_block_message_lists_recovery_options(tmp_path: Path) -> None:
    """WIP guard block message contains all three recovery paths."""
    _init_dirty_repo(tmp_path)
    result = _run("git pull --rebase origin main", tmp_path)
    assert result.returncode == 2
    stderr = result.stderr
    assert "git stash" in stderr, "should suggest stash path"
    assert "COS_ALLOW_RESET_OVER_WIP=1" in stderr, "should suggest bypass env var"
    assert "COS_AUTO_STASH_BEFORE_RESET=1" in stderr, "should mention auto-stash option"


def test_cos_allow_reset_over_wip_bypasses_wip_guard(tmp_path: Path) -> None:
    """COS_ALLOW_RESET_OVER_WIP=1 allows the op over WIP and logs bypass to JSONL."""
    _init_dirty_repo(tmp_path)
    result = _run(
        "git pull --rebase origin main",
        tmp_path,
        extra_env={"COS_ALLOW_RESET_OVER_WIP": "1"},
    )
    # Hook exits 0 (bypass accepted); the actual git command would then fail
    # because there is no remote, but the hook itself must allow it.
    assert result.returncode == 0, (
        f"expected bypass (exit 0), got {result.returncode}\n{result.stderr}"
    )
    assert "WIP-GUARD BYPASS ACCEPTED" in result.stderr
    # Bypass log must exist and contain a wip_guard_bypass entry
    bypass_log = tmp_path / ".cognitive-os" / "metrics" / "destructive-git-bypass.jsonl"
    assert bypass_log.exists(), f"bypass log missing: {bypass_log}"
    lines = [ln for ln in bypass_log.read_text().splitlines() if ln.strip()]
    assert lines, "bypass log must have at least one entry"
    entry = json.loads(lines[-1])
    assert entry["event"] == "wip_guard_bypass"
    assert entry["bypass_reason"] == "COS_ALLOW_RESET_OVER_WIP"
    assert "wip_files" in entry


def test_bypass_log_contains_wip_file_list(tmp_path: Path) -> None:
    """Bypass JSONL entry includes the WIP file list for forensic trail."""
    _init_dirty_repo(tmp_path)
    _run(
        "git pull --rebase origin main",
        tmp_path,
        extra_env={"COS_ALLOW_RESET_OVER_WIP": "1"},
    )
    bypass_log = tmp_path / ".cognitive-os" / "metrics" / "destructive-git-bypass.jsonl"
    entry = json.loads(bypass_log.read_text().splitlines()[-1])
    # wip_files must be a non-empty list
    assert isinstance(entry["wip_files"], list)
    assert len(entry["wip_files"]) >= 1


def test_wip_guard_block_is_logged_to_blocks_jsonl(tmp_path: Path) -> None:
    """WIP-guard block is written to the standard git-op-blocks.jsonl with reason=wip_guard."""
    _init_dirty_repo(tmp_path)
    result = _run("git rebase main", tmp_path)
    assert result.returncode == 2
    log = tmp_path / ".cognitive-os" / "metrics" / "git-op-blocks.jsonl"
    assert log.exists(), f"blocks log missing: {log}"
    lines = [ln for ln in log.read_text().splitlines() if ln.strip()]
    entry = json.loads(lines[-1])
    assert entry["event"] == "blocked"
    assert entry.get("reason") == "wip_guard"
