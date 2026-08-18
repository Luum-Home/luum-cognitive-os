"""Behavioural mutation test for hooks/protected-config-write-guard.sh.

Every case here runs the real hook with a real harness payload and asserts on the
exit code. Nothing asserts that a given string appears in the guard's source: a
guard that merely *mentions* `sed` is not a guard that *stops* `sed`.

Four directions, all of which must hold at once:
  1. every known way of writing a protected path is blocked;
  2. reading a protected path keeps working (a guard that blocks `cat` gets
     switched off within a week, which is worse than the hole it closed);
  3. the human-approval env var still waves everything through;
  4. the same write forms against a non-protected path are untouched.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
HOOK = Path(
    os.environ.get("COS_GUARD_UNDER_TEST")
    or REPO / "hooks" / "protected-config-write-guard.sh"
)
APPROVAL_ENV = "COS_ALLOW_PROTECTED_CONFIG_WRITE"

# A protected path that does not exist: the guard judges the command, it never
# runs it, so nothing on disk is touched by this suite.
PROTECTED = "hooks/zzz-guard-probe.sh"
PROTECTED_DIR = "hooks/"
SETTINGS = ".claude/settings.json"
SCRATCH = "/tmp/zzz-guard-probe.sh"
SRC = "/tmp/zzz-guard-src"

BLOCK = 2
ALLOW = 0


def _run(command: str, *, approve: bool = False) -> int:
    env = {
        "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
        "HOME": os.environ.get("HOME", ""),
        "CLAUDE_PROJECT_DIR": str(REPO),
    }
    if approve:
        env[APPROVAL_ENV] = "1"
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
    proc = subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        cwd=str(REPO),
        check=False,
    )
    return proc.returncode


def _write_forms(target: str) -> list[tuple[str, str]]:
    """Ways to modify `target`.

    The first four are the only ones the guard caught before the 2026-08-16 fix;
    everything after `redirect-clobber` used to pass.
    """
    delete_verb = "rm"
    return [
        ("redirect-trunc", f"echo x > {target}"),
        ("redirect-append", f"echo x >> {target}"),
        ("tee", f"echo x | tee {target}"),
        ("python-open-w", f"python3 -c \"open('{target}','w').write(1)\""),
        ("redirect-clobber", f"echo x >| {target}"),
        ("sed-i-empty", f"sed -i '' 's/a/b/' {target}"),
        ("sed-i-suffix", f"sed -i.bak 's/a/b/' {target}"),
        ("sed-i-longopt", f"sed --in-place 's/a/b/' {target}"),
        ("perl-pi", f"perl -pi -e 's/a/b/' {target}"),
        ("awk-inplace", f"awk -i inplace '{{print}}' {target}"),
        ("cp", f"cp {SRC} {target}"),
        ("mv", f"mv {SRC} {target}"),
        ("install", f"install -m 755 {SRC} {target}"),
        ("truncate", f"truncate -s 0 {target}"),
        ("ed", f"ed -s {target}"),
        # Beyond the originally measured set. The point of failing closed is
        # that none of these needed a new rule to be covered.
        ("sponge", f"cat {SRC} | sponge {target}"),
        ("dd", f"dd if={SRC} of={target}"),
        ("rsync", f"rsync -a {SRC} {target}"),
        ("patch", f"patch {target} {SRC}"),
        ("ln-sf", f"ln -sf {SRC} {target}"),
        ("chmod", f"chmod 777 {target}"),
        ("delete", f"{delete_verb} -f {target}"),
        ("git-checkout", f"git checkout -- {target}"),
        ("git-restore", f"git restore {target}"),
        ("git-rm", f"git {delete_verb} {target}"),
        ("ex", f"ex -s {target}"),
        ("vim-es", f"vim -es {target}"),
        ("emacs-batch", f"emacs --batch {target}"),
        ("sort-o", f"sort -o {target} {SRC}"),
        ("tee-append", f"echo x | tee -a {target}"),
        ("fd-redirect", f"echo x 2> {target}"),
        ("quoted-redirect", f'echo x > "{target}"'),
        ("interpreter-arg", f"python3 {SRC} {target}"),
        ("bash-c", f'bash -c "cp {SRC} {target}"'),
        ("sudo-wrapped", f"sudo cp {SRC} {target}"),
        ("env-assignment", f"FOO=1 cp {SRC} {target}"),
        ("if-wrapped", f"if cp {SRC} {target}; then echo ok; fi"),
        ("xargs-wrapped", f"echo a | xargs truncate -s 0 {target}"),
        ("busybox-sed", f"busybox sed -i s/a/b/ {target}"),
        # A heredoc fed to an interpreter is not data, it is the program.
        (
            "heredoc-to-interpreter",
            "python3 - <<'PY'\nfrom pathlib import Path\n"
            f"Path('{target}').write_text('x')\nPY",
        ),
    ]


WRITE_IDS = [name for name, _ in _write_forms(PROTECTED)]
PROTECTED_WRITES = [cmd for _, cmd in _write_forms(PROTECTED)]
SCRATCH_WRITES = [cmd for _, cmd in _write_forms(SCRATCH)]

# Reading a protected path, and ordinary work that merely mentions one. Any of
# these blocking would turn the guard into something people route around.
LEGIT_OPS: list[tuple[str, str]] = [
    ("cat", f"cat {PROTECTED}"),
    ("grep", f"grep -n foo {PROTECTED}"),
    ("grep-recursive", f"grep -rn foo {PROTECTED_DIR}"),
    ("grep-pattern-with-write-verb", f'grep -rn "sed -i" {PROTECTED_DIR}'),
    ("head", f"head -5 {PROTECTED}"),
    ("tail", f"tail -20 {PROTECTED}"),
    ("sed-print", f"sed -n '1,5p' {PROTECTED}"),
    ("awk-read", f"awk '{{print $1}}' {PROTECTED}"),
    ("wc", f"wc -l {PROTECTED}"),
    ("ls", f"ls -la {PROTECTED}"),
    ("stat", f"stat {PROTECTED}"),
    ("basename", f"basename {PROTECTED}"),
    ("readlink", f"readlink -f {PROTECTED}"),
    ("diff", f"diff {PROTECTED} {SRC}"),
    ("shasum", f"shasum -a 256 {PROTECTED}"),
    ("bash-syntax-check", f"bash -n {PROTECTED}"),
    ("shellcheck", f"shellcheck {PROTECTED}"),
    ("find", f'find {PROTECTED_DIR} -name "*.sh"'),
    ("git-log", f"git log --oneline -- {PROTECTED}"),
    ("git-diff", f"git diff -- {PROTECTED}"),
    ("git-status", f"git status --short {PROTECTED}"),
    ("git-add", f"git add {PROTECTED}"),
    ("git-commit", f'git commit --only -m "fix guard" -- {PROTECTED}'),
    ("git-show-blob", f"git show HEAD:{PROTECTED}"),
    ("git-global-option", f"git --no-pager diff -- {PROTECTED}"),
    ("git-grep", f"git grep -n foo -- {PROTECTED_DIR}"),
    ("jq-settings", f"jq '.hooks' {SETTINGS}"),
    ("sed-print-settings", f"sed -n '1,20p' {SETTINGS}"),
    ("cd-then-read", f"cd {PROTECTED_DIR} && ls"),
    ("pipe-read", f"cat {PROTECTED} | grep -c foo"),
    ("quoted-pipe-in-arg", f'cat {PROTECTED} | grep -c "a|b"'),
    ("echo-mention", f'echo "see {PROTECTED} for details"'),
    ("bare-word-not-a-path", "pytest -k hooks"),
    ("test-dir-is-not-hooks", "python3 -m pytest tests/hooks/test_x.py -q"),
    ("for-loop-enumeration", f'for f in {PROTECTED_DIR}*.sh; do bash -n "$f"; done'),
    (
        "heredoc-body-is-data",
        f"cat > /tmp/out.md <<'MD'\ncp {SRC} {PROTECTED}\ntee {PROTECTED}\nMD",
    ),
]


@pytest.mark.parametrize("command", PROTECTED_WRITES, ids=WRITE_IDS)
def test_write_forms_against_protected_path_are_blocked(command: str) -> None:
    assert _run(command) == BLOCK, f"protected write slipped through: {command}"


@pytest.mark.parametrize(
    "command", [cmd for _, cmd in LEGIT_OPS], ids=[n for n, _ in LEGIT_OPS]
)
def test_reads_and_ordinary_work_are_not_blocked(command: str) -> None:
    assert _run(command) == ALLOW, f"guard blocked legitimate work: {command}"


@pytest.mark.parametrize("command", PROTECTED_WRITES, ids=WRITE_IDS)
def test_approval_env_still_waves_everything_through(command: str) -> None:
    assert _run(command, approve=True) == ALLOW, f"approval env ignored: {command}"


@pytest.mark.parametrize("command", SCRATCH_WRITES, ids=WRITE_IDS)
def test_non_protected_paths_are_untouched(command: str) -> None:
    assert _run(command) == ALLOW, f"guard over-reached outside the policy: {command}"


def test_write_into_protected_directory_is_blocked() -> None:
    """A destination naming only the directory still lands inside the tree."""
    assert _run(f"cp {SRC} {PROTECTED_DIR}") == BLOCK


@pytest.mark.parametrize(
    "payload",
    [
        {"tool_name": "Write", "tool_input": {"file_path": PROTECTED, "content": "x"}},
        {
            "tool_name": "Edit",
            "tool_input": {
                "file_path": PROTECTED,
                "old_string": "a",
                "new_string": "b",
            },
        },
        {"tool_name": "MultiEdit", "tool_input": {"edits": [{"file_path": PROTECTED}]}},
    ],
    ids=["Write", "Edit", "MultiEdit"],
)
def test_dedicated_write_tools_stay_blocked(payload: dict) -> None:
    proc = subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={
            "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
            "HOME": os.environ.get("HOME", ""),
            "CLAUDE_PROJECT_DIR": str(REPO),
        },
        cwd=str(REPO),
        check=False,
    )
    assert proc.returncode == BLOCK
    assert "PROTECTED CONFIG WRITE GUARD" in proc.stderr
