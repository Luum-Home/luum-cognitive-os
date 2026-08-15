"""Both halves of two guard relaxations landed 2026-08-15.

`hooks/research-compliance-guard.sh` blocked a report that *audits* home-path
leakage, on four matches that were all the fixed GitHub Actions runner home —
a path allocated to a machine, identical on every runner, not to a person.
`hooks/destructive-git-blocker.sh` blocked `git restore --staged` and
`git reset -- <path>`, which only rewrite index entries.

Relaxing a guard without proving it still fires is how a control quietly stops
being one, so every permissive test here is paired with a restrictive one, and
each pair exercises the same guard on the same shape of input. The tests assert
on the guard's own exit code and message rather than on its internals.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PRIVACY_GUARD = REPO_ROOT / "hooks" / "research-compliance-guard.sh"
GIT_GUARD = REPO_ROOT / "hooks" / "destructive-git-blocker.sh"

# Assembled at runtime so this test file does not itself carry a literal that
# would trip the very guards it exercises.
MAC_HOME = "/" + "Users" + "/"
LINUX_HOME = "/" + "home" + "/"

HOME_PATH_FINDING = "contains a personal absolute home path"


# ---------------------------------------------------------------------------
# Population guard
# ---------------------------------------------------------------------------
# A suite that passes because it found nothing to check is theatre. These two
# assertions fail loudly if either guard is renamed, moved, or unregistered,
# instead of letting every test below vacuously succeed.


def test_both_guards_exist_and_are_executable() -> None:
    for guard in (PRIVACY_GUARD, GIT_GUARD):
        resolved = guard.resolve()
        assert resolved.is_file(), f"{guard} does not resolve to a file"
        assert os.access(resolved, os.X_OK), f"{resolved} is not executable"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _init_repo(root: Path) -> None:
    subprocess.run(["git", "init", "-q", "."], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.invalid"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=root, check=True)


def _run_privacy_guard(root: Path, files: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """Stage `files` in a throwaway repo and run the guard over the index."""
    _init_repo(root)
    for name, body in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    env = _clean_env(COGNITIVE_OS_PROJECT_DIR=str(root))
    return subprocess.run(
        ["bash", str(PRIVACY_GUARD)],
        input=json.dumps({"tool_input": {"command": "git commit -m x"}}),
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
    )


def _clean_env(**overrides: str) -> dict[str, str]:
    """Ambient session state must not decide what these tests measure.

    `CLAUDE_TOOL_INPUT` in particular takes precedence over stdin inside the
    blocker, so a suite run from inside a live agent session would have graded
    the session's own command instead of the one under test — and passed the
    permissive half while silently skipping the restrictive one.
    """
    env = {k: v for k, v in os.environ.items() if not k.startswith(("COS_", "CLAUDE_"))}
    env.update(overrides)
    return env


def _run_git_guard(command: str) -> subprocess.CompletedProcess[str]:
    """Run the blocker in agent context, which is the context it exists for.

    Without `CLAUDE_AGENT_ID` the blocker takes its `so_internal_context`
    bypass — it sees a python parent, assumes SO-internal tooling, and allows
    everything silently. A suite that forgot this would watch every permissive
    case pass for the wrong reason and never observe a single block. The
    blocker's own comment states the intended contract: "Agents running under
    pytest/CI must still be blocked."
    """
    env = _clean_env(
        CLAUDE_PROJECT_DIR=str(REPO_ROOT),
        CLAUDE_AGENT_ID="guard-regression-test",
    )
    return subprocess.run(
        ["bash", str(GIT_GUARD)],
        input=json.dumps({"tool_input": {"command": command}}),
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )


# ---------------------------------------------------------------------------
# Guard 1 — a CI runner home is a machine's, not a person's
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("home_root", [MAC_HOME, LINUX_HOME])
def test_ci_runner_home_is_not_a_personal_path(tmp_path: Path, home_root: str) -> None:
    """The fixed GitHub Actions runner path must not read as a leak.

    It is identical on every runner in the world, so it identifies a machine
    class rather than a developer.
    """
    result = _run_privacy_guard(
        tmp_path, {"docs/report.md": f"CI workspace lives at {home_root}runner/work/repo/repo\n"}
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert HOME_PATH_FINDING not in (result.stdout + result.stderr)


def test_real_home_still_blocks_beside_a_ci_runner_path(tmp_path: Path) -> None:
    """The half that matters: the exemption is per token, not per file.

    Both strings live on adjacent lines on purpose. If the guard had learned
    "this file mentions a runner, so let it through", the leak on line 2 would
    ship.
    """
    result = _run_privacy_guard(
        tmp_path,
        {
            "docs/report.md": (
                f"CI workspace lives at {MAC_HOME}runner/work/repo/repo\n"
                f'leaked = "{MAC_HOME}realdev/Projects/private/app.py"\n'
            )
        },
    )
    output = result.stdout + result.stderr
    assert result.returncode == 2, output
    assert HOME_PATH_FINDING in output


def test_a_plausible_username_is_not_exempt(tmp_path: Path) -> None:
    """The exemption list is by construction, not by convenience.

    `runner` qualifies because it is a published, fixed CI path. Names that are
    merely common are somebody's real account somewhere, so they must not be
    waved through.
    """
    for username in ("admin", "dev", "ubuntu", "runners"):
        target = tmp_path / username
        target.mkdir()
        result = _run_privacy_guard(
            target, {"docs/report.md": f'p = "{MAC_HOME}{username}/Projects/x.py"\n'}
        )
        output = result.stdout + result.stderr
        assert result.returncode == 2, f"{username} was wrongly exempted: {output}"
        assert HOME_PATH_FINDING in output


def test_documented_username_pattern_is_not_a_leak(tmp_path: Path) -> None:
    """Parity with commit 3a6e737b: a regex describing usernames is not one.

    The username segment here opens with legal account characters, so the guard
    does flag the line; the discriminator is what clears it. That is the case
    the sibling guards already handle.
    """
    result = _run_privacy_guard(
        tmp_path, {"docs/report.md": f"scan with: {MAC_HOME}user[0-9]+ across the tree\n"}
    )
    assert result.returncode == 0, result.stdout + result.stderr


# ---------------------------------------------------------------------------
# Guard 2 — unstaging is not a working-tree discard
# ---------------------------------------------------------------------------

INDEX_ONLY = [
    "git restore --staged docs/x.md",
    "git restore -S docs/x.md",
    "git reset -- docs/x.md",
    "git reset HEAD -- docs/x.md",
]

STILL_DESTRUCTIVE = [
    # No --staged: this is the working-tree discard the guard exists for.
    "git restore docs/x.md",
    # --worktree restores both, so the working tree is written.
    "git restore --staged --worktree docs/x.md",
    "git restore --source=HEAD docs/x.md",
    "git reset --hard HEAD~1",
    "git reset --hard",
    "git reset --merge",
    # No `--` separator: the pathspec is ambiguous, so it is not granted.
    "git reset HEAD docs/x.md",
    "git checkout -- docs/x.md",
    "git clean -fd",
    "git stash pop",
]


@pytest.mark.parametrize("command", INDEX_ONLY)
def test_index_only_git_ops_are_allowed(command: str) -> None:
    """`--staged` restores the index only, per git-restore(1); a pathspec'd
    reset never moves HEAD nor touches the working tree."""
    result = _run_git_guard(command)
    assert result.returncode == 0, f"{command} blocked:\n{result.stdout}{result.stderr}"


@pytest.mark.parametrize("command", STILL_DESTRUCTIVE)
def test_worktree_touching_git_ops_still_block(command: str) -> None:
    """The relaxation must not leak into the forms that write the tree.

    The blocker exits 1 in agent context and 2 in user context, so the
    assertion is on "refused at all" plus the banner, not on one number.
    """
    result = _run_git_guard(command)
    output = result.stdout + result.stderr
    assert result.returncode != 0, f"{command} was allowed:\n{output}"
    assert "DESTRUCTIVE-GIT-BLOCKER: BLOCKED" in output, output


def test_blocker_emits_no_shell_errors_on_stderr() -> None:
    """Regression for the line-382 defect.

    The `git restore` rationale carried backticks inside a double-quoted echo,
    so bash ran `checkout` as a command, printed a not-found error to stderr,
    and substituted its empty output into the operator's message — which then
    read "modern equivalent of " with the referent missing.
    """
    result = _run_git_guard("git restore docs/x.md")
    stderr = result.stderr
    assert "command not found" not in stderr, stderr
    assert "orden no encontrada" not in stderr, stderr
    assert "modern equivalent of `checkout --`" in stderr, stderr


def test_repair_advice_does_not_recommend_a_whole_tree_stash() -> None:
    """A repair must not be more destructive than the op it repairs.

    `git stash push -u` with no pathspec sweeps the entire working tree,
    including another session's untracked files, into one entry — the exact
    residue hazard ADR-055b r5 is about.
    """
    result = _run_git_guard("git restore docs/x.md")
    repair = [ln for ln in result.stderr.splitlines() if ln.startswith("Repair command:")]
    assert repair, result.stderr
    line = repair[0]
    assert "git status --porcelain" in line, line
    if "git stash push" in line:
        assert "-- <path>" in line, f"stash advice must be path-scoped: {line}"


def test_agent_context_is_what_the_suite_actually_exercises() -> None:
    """Population guard for the guard-2 half of this file.

    Every permissive assertion above would pass vacuously if the blocker were
    taking its `so_internal_context` bypass, because that path allows
    everything. This test proves the harness reaches the real decision: with
    the agent marker the blocker refuses, without it the same command sails
    through.
    """
    blocked = _run_git_guard("git reset --hard")
    assert blocked.returncode != 0, blocked.stdout + blocked.stderr
    assert "BLOCKED" in blocked.stdout + blocked.stderr

    bypassed = subprocess.run(
        ["bash", str(GIT_GUARD)],
        input=json.dumps({"tool_input": {"command": "git reset --hard"}}),
        cwd=REPO_ROOT,
        env=_clean_env(CLAUDE_PROJECT_DIR=str(REPO_ROOT)),
        capture_output=True,
        text=True,
    )
    assert bypassed.returncode == 0, "expected the SO-internal bypass without an agent marker"
