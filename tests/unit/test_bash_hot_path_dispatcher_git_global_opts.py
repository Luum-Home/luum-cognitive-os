"""Dispatch behaviour of hooks/bash-hot-path-dispatcher.sh for `git` invocations
that carry GLOBAL OPTIONS between `git` and the subcommand.

`git -C <dir> commit`, `git --no-pager commit`, `git -c user.email=x commit` and
`git --git-dir=... commit` are all ordinary commits. The dispatcher used to
require literal adjacency between `git` and the subcommand, so every one of
those shapes walked past the entire commit battery (16 gates) and the git
boundary battery (7 gates) — 23 hooks, silently.

These tests execute the REAL dispatcher. They never grep the source for `-C`
or any other option: the dispatcher is copied into a throwaway tree whose
`hooks/` contains stub gates that append their own name to a log file, so what
is asserted is which gates the dispatcher actually invoked.

Point the suite at a different dispatcher (e.g. a pre-fix copy extracted with
`git show <rev>:hooks/bash-hot-path-dispatcher.sh`) via
`COS_TEST_DISPATCHER=/path/to/dispatcher.sh` to reproduce the old failure.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DISPATCHER = Path(
    os.environ.get(
        "COS_TEST_DISPATCHER", str(REPO_ROOT / "hooks" / "bash-hot-path-dispatcher.sh")
    )
)

# Gates the dispatcher runs behind `_is_git_commit`.
COMMIT_BATTERY = {
    "provenance-scan.sh",
    "git-commit-scope-guard.sh",
    "orchestrator-claim-gate.sh",
    "pre-commit-content-hash-dedupe.sh",
    "scope-marker-portability-gate.sh",
    "external-pattern-cleanroom-gate.sh",
    "adoption-freeze-gate.sh",
    "dependency-license-classifier.sh",
    "research-to-runtime-firewall.sh",
    "research-compliance-guard.sh",
    "spdx-header-required.sh",
    "external-cache-content-leak.sh",
    "attribution-completeness-validator.sh",
    "lib-symlink-divergence-detector.sh",
    "legal-review-required-on-runtime-import.sh",
    "pending-truth-staleness-gate.sh",
}

# Gates the dispatcher runs behind `_is_git_boundary`.
GIT_BOUNDARY_BATTERY = {
    "destructive-git-blocker.sh",
    "conflict-marker-guard.sh",
    "untracked-work-preservation-guard.sh",
    "direct-main-guard.sh",
    "branch-ownership-lock.sh",
    "cross-session-coordination-guard.sh",
    "agent-message-inbox-guard.sh",
}

# Runs on every Bash call regardless of command shape; useful as a liveness
# signal that the dispatcher ran at all rather than dying early.
ALWAYS = "orchestrator-skill-invocation-gate.sh"


@pytest.fixture(scope="module")
def lab(tmp_path_factory) -> Path:
    """Isolated hook tree: real dispatcher, stub gates that record invocation."""
    root = tmp_path_factory.mktemp("dispatch-lab")
    hooks = root / "hooks"
    hooks.mkdir()

    source = DISPATCHER.read_text(encoding="utf-8")
    shutil.copyfile(DISPATCHER, hooks / "bash-hot-path-dispatcher.sh")
    (hooks / "bash-hot-path-dispatcher.sh").chmod(0o755)

    referenced = set(re.findall(r"hooks/([a-z0-9-]+\.sh)", source))
    referenced.discard("bash-hot-path-dispatcher.sh")
    assert referenced, "dispatcher references no gates — wrong file?"
    for name in referenced:
        stub = hooks / name
        stub.write_text(
            '#!/usr/bin/env bash\ncat >/dev/null\n'
            f'echo "{name}" >> "$COS_DISPATCH_LOG"\nexit 0\n',
            encoding="utf-8",
        )
        stub.chmod(0o755)
    return root


def dispatched(lab: Path, command: str) -> set[str]:
    """Run the dispatcher on `command`; return the set of gates it invoked."""
    log = lab / "log.txt"
    log.write_text("", encoding="utf-8")
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    env = dict(os.environ, COS_DISPATCH_LOG=str(log))
    subprocess.run(
        ["bash", str(lab / "hooks" / "bash-hot-path-dispatcher.sh")],
        input=payload,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    return {line for line in log.read_text(encoding="utf-8").split("\n") if line}


GLOBAL_OPT_COMMITS = [
    'git -C /tmp/repo commit -m "x"',
    'git --no-pager commit -m "x"',
    'git -c user.email=a@b.c commit -m "x"',
    'git --git-dir=/tmp/repo/.git --work-tree=/tmp/repo commit -m "x"',
    "git -C /tmp/repo commit --amend --no-edit",
    'cd /tmp && git -C /tmp/repo commit -m "x"',
]


def test_plain_commit_dispatches_the_full_battery(lab):
    """Baseline: the shape that always worked must keep working."""
    got = dispatched(lab, 'git commit -m "x"')
    assert COMMIT_BATTERY <= got
    assert GIT_BOUNDARY_BATTERY <= got


@pytest.mark.parametrize("command", GLOBAL_OPT_COMMITS)
def test_global_option_commit_reaches_the_commit_battery(lab, command):
    """The hole: options between `git` and `commit` must not skip the gates."""
    got = dispatched(lab, command)
    missing = COMMIT_BATTERY - got
    assert not missing, f"{command!r} skipped commit gates: {sorted(missing)}"


@pytest.mark.parametrize("command", GLOBAL_OPT_COMMITS)
def test_global_option_commit_reaches_the_git_boundary_battery(lab, command):
    got = dispatched(lab, command)
    missing = GIT_BOUNDARY_BATTERY - got
    assert not missing, f"{command!r} skipped boundary gates: {sorted(missing)}"


def test_global_option_push_reaches_network_and_boundary_gates(lab):
    got = dispatched(lab, "git -C /tmp/repo push origin main")
    assert "network-egress-guard.sh" in got
    assert GIT_BOUNDARY_BATTERY <= got


def test_global_option_tag_reaches_the_release_guard(lab):
    got = dispatched(lab, "git -C /tmp/repo tag v1.2.3")
    assert "release-guard.sh" in got


# ── The reverse: widening the trigger must not turn the hot path into a funnel ─

NON_COMMIT_COMMANDS = [
    "ls -la",
    "echo hola",
    "git status",
    "git -C /tmp/repo status",
    "git --no-pager log --oneline -5",
    "python3 scripts/foo.py --git -x",
    'grep -rn "git commit" docs/',
]


@pytest.mark.parametrize("command", NON_COMMIT_COMMANDS)
def test_non_commit_commands_do_not_pull_in_the_battery(lab, command):
    """Read-only and unrelated commands stay on the one-gate hot path."""
    got = dispatched(lab, command)
    assert got == {ALWAYS}, f"{command!r} over-dispatched: {sorted(got - {ALWAYS})}"
