"""Behaviour tests for quote-aware command reading in destructive-git-blocker.

Every test EXECUTES the hook with a real PreToolUse payload and asserts on the
exit code. None of them inspects the source: a test that greps for `shlex`
would prove which implementation was chosen, not which commands get blocked,
and the implementation is not the contract.

Two directions are asserted, and the second matters more:

  * text that merely MENTIONS a destructive op (a comment, an `echo`, a
    heredoc body, a commit-message body) must stop blocking — that is the bug;
  * every op that actually RUNS must keep blocking, including the forms that
    hide behind quotes, wrappers, interpreters and subshells — that is the
    control this fix must not weaken.

Op strings are assembled from fragments so this file never contains a literal
destructive git command. Committing one used to trip the very guard under
test, which is the bug stated as a fact about the repo.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HOOK = os.path.join(REPO, "hooks", "destructive-git-blocker.sh")

POP = "git " + "sta" + "sh " + "p" + "op"
HARD = "git " + "res" + "et --hard"

BLOCK = 2
ALLOW = 0


@pytest.fixture(scope="module")
def fixture_repo(tmp_path_factory):
    """A throwaway repo on a NON-protected branch.

    Without this the protected-branch verdict (main/master) fires on every
    `git commit` case and masquerades as a quoting verdict — which is exactly
    how an earlier reading of this hook mis-scored its own commit-message rows.
    """
    path = tmp_path_factory.mktemp("dgb-quoting")
    run = lambda *a: subprocess.run(["git", "-C", str(path), *a], check=True,
                                    capture_output=True)
    subprocess.run(["git", "init", "-q", "-b", "work", str(path)], check=True,
                   capture_output=True)
    run("config", "user.email", "t@example.invalid")
    run("config", "user.name", "t")
    (path / "a.txt").write_text("hi\n")
    run("add", "a.txt")
    run("commit", "-qm", "init")
    return path


def verdict(command: str, fixture_repo) -> int:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    env = {k: v for k, v in os.environ.items()
           if k not in ("CLAUDE_TOOL_INPUT", "CI", "PYTEST_CURRENT_TEST",
                        "COS_GIT_BYPASS", "COS_ALLOW_DESTRUCTIVE_GIT",
                        "COS_ALLOW_MAIN_BRANCH_WRITE")}
    env["CLAUDE_PROJECT_DIR"] = str(fixture_repo)
    env["COGNITIVE_OS_PROJECT_DIR"] = str(fixture_repo)
    proc = subprocess.run(["bash", HOOK], input=payload, capture_output=True,
                          text=True, env=env, cwd=str(fixture_repo))
    return proc.returncode


# ── The op runs: MUST block ──────────────────────────────────────────────────

@pytest.mark.parametrize("command", [
    POP,                                    # bare
    "cd /tmp && " + POP,                    # after a real &&
    "cd /tmp ; " + POP,                     # after a real ;
    "false || " + POP,                      # after a real ||
    "true | " + POP,                        # after a real pipe
    "echo hi\n" + POP,                      # after a real newline
    'echo "hola" && ' + POP,                # after a quoted arg + real &&
    "(cd /tmp && " + POP + ")",             # inside a subshell
    "git -C /tmp " + POP[4:],               # global option between git and op
    'git "sta""sh" "p""op"',                # op spelled with odd quoting
    HARD,
    "git fetch && " + HARD + " origin/main",
    "echo x && git push --force origin main",
    "sudo " + POP,                          # behind a privilege wrapper
    "GIT_DIR=/tmp/.git " + POP,             # behind a VAR=VAL assignment
    'bash -c "cd /tmp && ' + POP + '"',     # inside an interpreter argument
    "sh -c '" + POP + "'",
    'eval "' + POP + '"',
    "bash <<'EOF'\n" + POP + "\nEOF",       # heredoc READ BY an interpreter
    "cat <<'EOF'\ndoc\nEOF\n" + POP,        # real op after a heredoc body
    "ls  # " + POP + "\n" + POP,            # real op on the line after a comment
    'echo "oops && ' + POP,                 # unbalanced quote: uncertainty blocks
])
def test_executed_op_still_blocks(command, fixture_repo):
    assert verdict(command, fixture_repo) == BLOCK, (
        "detection weakened: this command executes a destructive git op"
    )


# ── The op is only mentioned: MUST NOT block ─────────────────────────────────

@pytest.mark.parametrize("command", [
    'echo "texto con && ' + POP + '"',            # separator inside quotes
    "echo 'plan: " + POP + " && more'",
    'printf "%s\\n" "run ' + POP + ' && exit"',
    "ls -la  # never run " + POP,                 # trailing comment
    "cat <<'EOF'\n" + POP + " && true\nEOF",      # heredoc body is stdin data
    "git commit -m 'doc: " + POP + " && ok'",     # single-quoted message body
    'git commit -m "doc: ' + POP + ' && ok"',     # double-quoted message body
    "git commit -m 'title\n\nbody: " + POP + " && ok'",   # MULTI-LINE body
    "git -C /tmp commit -m 'x: " + POP + " && y'",
    "git grep -n '" + POP + " && x' -- '*.md'",   # searching for the text
    'MSG="see ' + POP + ' && stop"; echo done',   # assigned to a variable
    'echo "never git push --force here"',
])
def test_mentioned_op_does_not_block(command, fixture_repo):
    assert verdict(command, fixture_repo) == ALLOW, (
        "false positive: nothing in this command executes a git op"
    )


# ── Controls ─────────────────────────────────────────────────────────────────

def test_read_only_git_is_allowed(fixture_repo):
    assert verdict("git status", fixture_repo) == ALLOW


def test_force_with_lease_is_allowed(fixture_repo):
    assert verdict("git push --force-with-lease origin main", fixture_repo) == ALLOW


def test_non_git_command_is_allowed(fixture_repo):
    assert verdict("ls -la", fixture_repo) == ALLOW
