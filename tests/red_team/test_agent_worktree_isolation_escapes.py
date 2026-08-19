# SCOPE: os-only
"""Red-team proofs for the ADR-223 worktree-per-write-agent isolation boundary.

Three escapes were checked against our own mechanism on 2026-08-19. Two of them
are pinned here as *known-open* gaps (they need a registered blocking hook, which
lives outside this module); the third is closed by
`cos_lib.agent_lifecycle.prepare_agent_worktree` and is proven closed here.

Report: docs/06-Daily/reports/aislamiento-worktree-vs-nativo-2026-08-19.md
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from cos_lib.agent_lifecycle import AgentLifecycleError, prepare_agent_worktree  # noqa: E402


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env.update({"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
                "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid"})
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, env=env)


@pytest.fixture()
def operator_repo(tmp_path: Path) -> Path:
    """A stand-in operator checkout with one commit on a non-protected branch."""
    repo = tmp_path / "operator"
    repo.mkdir()
    _git(["init", "-q", "-b", "fixturebase", "."], repo)
    (repo / "OPERATOR_FILE.txt").write_text("operator content\n", encoding="utf-8")
    _git(["add", "-A"], repo)
    _git(["commit", "-qm", "seed"], repo)
    return repo


# --------------------------------------------------------------------------
# Escape 1 — git redirected into the operator checkout from the agent worktree.
# PINNED AS OPEN. When this test starts failing, the gap was closed: replace the
# assertion with the blocking expectation instead of relaxing it.
# --------------------------------------------------------------------------
def test_git_c_redirect_into_operator_checkout_is_currently_unguarded(operator_repo: Path, tmp_path: Path) -> None:
    agent_wt = tmp_path / "agent-wt"
    assert _git(["worktree", "add", "-q", str(agent_wt), "-b", "agent/task"], operator_repo).returncode == 0

    # A write issued from the agent worktree, redirected at the operator checkout.
    (operator_repo / "ESCAPED.txt").write_text("written from the agent worktree\n", encoding="utf-8")
    assert _git(["-C", str(operator_repo), "add", "ESCAPED.txt"], agent_wt).returncode == 0
    assert _git(["-C", str(operator_repo), "commit", "-qm", "escaped"], agent_wt).returncode == 0
    assert "escaped" in _git(["log", "--oneline", "-1"], operator_repo).stdout

    # The primitive nominally responsible for this refuses nothing: it always
    # exits 0 and emits no deny decision.
    enforcer = REPO_ROOT / "hooks" / "agent-bash-cwd-enforcer.sh"
    payload = json.dumps({"tool_name": "Bash",
                          "tool_input": {"command": f"git -C {operator_repo} commit -m x"}})
    proc = subprocess.run(["bash", str(enforcer)], input=payload, capture_output=True, text=True,
                          cwd=str(agent_wt), env={**os.environ, "CLAUDE_PROJECT_DIR": str(operator_repo)})
    assert proc.returncode == 0
    assert "deny" not in proc.stdout


def test_cwd_enforcer_is_not_projected_as_an_active_claude_code_hook() -> None:
    """The guard is declared but shipped disabled, so nothing enforces at runtime."""
    settings = json.loads((REPO_ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert "agent-bash-cwd-enforcer" not in json.dumps(settings["hooks"])


# --------------------------------------------------------------------------
# Escape 2 — symlinked worktree target. CLOSED.
# --------------------------------------------------------------------------
def test_symlinked_worktree_target_pointing_at_operator_checkout_is_refused(operator_repo: Path, tmp_path: Path) -> None:
    root = tmp_path / "wt-root"
    root.mkdir()
    (root / "evil-task").symlink_to(operator_repo)

    with pytest.raises(AgentLifecycleError) as excinfo:
        prepare_agent_worktree(operator_repo, task_id="evil-task", session_id="s1", worktree_root=root)
    assert "symlink" in str(excinfo.value)


def test_worktree_target_resolving_inside_the_operator_checkout_is_refused(operator_repo: Path, tmp_path: Path) -> None:
    root = tmp_path / "wt-root"
    root.mkdir()
    (root / "inside").symlink_to(operator_repo / "nested")

    with pytest.raises(AgentLifecycleError) as excinfo:
        prepare_agent_worktree(operator_repo, task_id="inside", session_id="s1", worktree_root=root)
    assert "symlink" in str(excinfo.value)


def test_worktree_root_nested_in_the_operator_checkout_is_refused(operator_repo: Path) -> None:
    with pytest.raises(AgentLifecycleError) as excinfo:
        prepare_agent_worktree(operator_repo, task_id="t1", session_id="s1",
                               worktree_root=operator_repo / "sub" / "wts")
    assert "inside the operator checkout" in str(excinfo.value)


def test_legitimate_worktree_preparation_still_succeeds(operator_repo: Path, tmp_path: Path) -> None:
    """Guard must not be a blanket refusal: the happy path keeps working."""
    record = prepare_agent_worktree(operator_repo, task_id="honest task",
                                    session_id="s1", worktree_root=tmp_path / "wt-root")
    target = Path(record.worktree_path)
    assert record.created is True
    assert target.is_dir() and not target.is_symlink()
    assert (target / "OPERATOR_FILE.txt").exists()
    assert record.branch.startswith("codex/agent/")
