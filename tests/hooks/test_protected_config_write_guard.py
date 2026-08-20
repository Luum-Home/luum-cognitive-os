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
        # --- pairs for the 2026-08-20 relaxations ---------------------------
        # Each of these has a twin in LEGIT_OPS with the SAME syntactic shape
        # and a read where this one has a write. The pair is the whole point:
        # an exemption that also lets the write through is a hole, not a fix.
        #
        # A substitution body carrying a parenthesis is now lifted and judged.
        # Lifting must judge it, not excuse it.
        ("substitution-with-parens", f"L=$(sed -i '' 's/a()/b/' {target})"),
        (
            "procsub-with-parens",
            f"diff <(sed -i '' 's/a()/b/' {target}) /dev/null",
        ),
        # A string constant that IS a path stays a destination even when it is
        # only bound to a name -- program_write_candidates resolves no binding,
        # so it cannot know the name is never written, and refuses.
        (
            "heredoc-path-in-a-variable",
            "python3 - <<'PY'\nfrom pathlib import Path\n"
            f"p = '{target}'\nPath(p).write_text('x')\nPY",
        ),
        # A constant handed to a call is a destination whatever the call does.
        (
            "heredoc-subprocess-argv",
            "python3 - <<'PY'\nimport subprocess\n"
            f"subprocess.run(['cp', '{SRC}', '{target}'])\nPY",
        ),
        (
            "heredoc-open-for-write",
            f"python3 - <<'PY'\nopen('{target}', 'w').write('x')\nPY",
        ),
        # A program that does not parse is one whose string constants cannot be
        # classified, so every protected token in it stays a destination. The
        # write primitive is what makes this case reach that branch at all: a
        # body with no write primitive is cleared upstream by body_can_write,
        # and rightly so, since a program that does not compile never runs.
        # Two valid programs concatenated by strip_heredocs are the real
        # unparseable case, and this is its minimal stand-in.
        (
            "heredoc-unparseable-program",
            "python3 - <<'PY'\nthis is not python (\n"
            f"Path('{target}').write_text('x')\nPY",
        ),
        # Delegated writes: relaxing -c on the strength of "no write primitive"
        # would clear both of these, which is why handing the work to another
        # process counts as a write.
        (
            "python-c-os-system",
            f"python3 -c \"import os; os.system('cp {SRC} {target}')\"",
        ),
        (
            "python-c-subprocess",
            "python3 -c \"import subprocess; "
            f"subprocess.run(['cp', '{SRC}', '{target}'])\"",
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
    # --- twins of the 2026-08-20 write forms ------------------------------
    # Same syntactic shape as the entries added to _write_forms, with a read
    # where those have a write. Both halves must hold: these pass, those block.
    #
    # A substitution body carrying a parenthesis. The old regex body was
    # [^()]*, so nothing was lifted, `L=$(grep` read as an assignment, and the
    # next word -- `-n` -- became the command word. Measured 2026-08-20: this
    # is the shape that blocked a plain grep over the guard itself.
    (
        "substitution-body-with-parens",
        f"L=$(grep -n 'body_can_write()' {PROTECTED} | head -1 | cut -d: -f1)",
    ),
    ("substitution-body-plain", f"n=$(wc -c < {PROTECTED})"),
    ("procsub-read-with-parens", f"diff <(grep -c 'f()' {PROTECTED}) /dev/null"),
    ("arith-substitution", f'sed -n "$((1)),$((1+5))p" {PROTECTED}'),
    # The most recurrent legitimate shape in this repo: rewrite a file under
    # tests/ whose new text quotes a protected path. The path lives in a
    # content blob -- never a call argument, never a path on its own -- so it
    # is not a destination. Measured 2026-08-20: 8 of the 19 live blocks.
    (
        "heredoc-writes-elsewhere-mentioning-protected",
        "python3 - <<'PY'\nimport pathlib\n"
        "p = pathlib.Path('tests/unit/test_zzz.py')\n"
        "s = p.read_text()\n"
        f"nuevo = '''se documenta {PROTECTED} en la prosa'''\n"
        "p.write_text(s + nuevo)\nPY",
    ),
    (
        "python-c-reads-settings",
        f"python3 -c \"import json; json.load(open('{SETTINGS}'))\"",
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


def test_json_unicode_escape_does_not_evade_the_prefilter() -> None:
    """The fast path matches the raw payload; jq decodes it afterwards.

    A path spelled with a JSON \\u escape must not slip past the prefilter,
    because the analyzer downstream would have seen the decoded path.
    """
    command = f"cp {SRC} {PROTECTED}"
    plain = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    escaped = plain.replace("hooks", "\\u0068ooks", 1)
    assert json.loads(escaped)["tool_input"]["command"] == command
    proc = subprocess.run(
        ["bash", str(HOOK)],
        input=escaped,
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


# --- Patch appliers ---------------------------------------------------------
# `git apply x.patch` names one path in its text -- the patch -- and writes paths
# that appear nowhere in the command. Every case below runs the real hook on a
# real patch file; the guard reads the patch, so the patch has to exist.

HOOKS_PATCH = (
    f"--- a/{PROTECTED}\n+++ b/{PROTECTED}\n@@ -1 +1 @@\n-old\n+new\n"
)
DOCS_PATCH = "--- a/docs/zzz-probe.md\n+++ b/docs/zzz-probe.md\n@@ -1 +1 @@\n-old\n+new\n"
TESTS_PATCH = (
    "--- a/tests/zzz_probe.py\n+++ b/tests/zzz_probe.py\n@@ -1 +1 @@\n-old\n+new\n"
)
MIXED_PATCH = DOCS_PATCH + HOOKS_PATCH
DELETE_PATCH = f"--- a/{PROTECTED}\n+++ /dev/null\n@@ -1 +0,0 @@\n-old\n"
RENAME_PATCH = (
    "diff --git a/hooks/zzz-old.sh b/hooks/zzz-new.sh\n"
    "similarity index 100%\nrename from hooks/zzz-old.sh\nrename to hooks/zzz-new.sh\n"
)
P0_PATCH = f"--- {PROTECTED}\n+++ {PROTECTED}\n@@ -1 +1 @@\n-old\n+new\n"
NOT_A_PATCH = f"notes about {PROTECTED} and how it works\n"


@pytest.fixture
def patchfile(tmp_path):
    def make(text: str, name: str = "probe.patch") -> str:
        f = tmp_path / name
        f.write_text(text)
        return str(f)

    return make


PATCH_BLOCKS = [
    ("git-apply", HOOKS_PATCH, "git apply {p}"),
    ("git-apply-p0", P0_PATCH, "git apply -p0 {p}"),
    ("git-apply-reverse", HOOKS_PATCH, "git apply -R {p}"),
    ("git-apply-reverse-long", HOOKS_PATCH, "git apply --reverse {p}"),
    ("git-apply-stdin-redirect", HOOKS_PATCH, "git apply < {p}"),
    ("git-apply-dash", HOOKS_PATCH, "git apply - < {p}"),
    ("git-apply-3way", HOOKS_PATCH, "git apply -3 --whitespace=fix {p}"),
    ("git-am", HOOKS_PATCH, "git am {p}"),
    ("patch-stdin", HOOKS_PATCH, "patch -p1 < {p}"),
    ("patch-stdin-no-flags", HOOKS_PATCH, "patch < {p}"),
    ("patch-input-flag", HOOKS_PATCH, "patch -i {p}"),
    ("patch-input-longopt", HOOKS_PATCH, "patch --input={p}"),
    ("deletion-names-victim-on-the-minus-side", DELETE_PATCH, "git apply {p}"),
    ("rename-has-no-hunk", RENAME_PATCH, "git apply {p}"),
    ("mixed-docs-and-hooks", MIXED_PATCH, "git apply {p}"),
    ("wrapped-in-sudo", HOOKS_PATCH, "sudo git apply {p}"),
    ("second-segment", HOOKS_PATCH, "cd /tmp && git apply {p}"),
]


@pytest.mark.parametrize(
    "text,template",
    [(t, c) for _, t, c in PATCH_BLOCKS],
    ids=[n for n, _, _ in PATCH_BLOCKS],
)
def test_patch_writing_a_protected_path_is_blocked(patchfile, text, template) -> None:
    assert _run(template.format(p=patchfile(text))) == BLOCK


@pytest.mark.parametrize(
    "text,template",
    [(t, c) for _, t, c in PATCH_BLOCKS],
    ids=[n for n, _, _ in PATCH_BLOCKS],
)
def test_patch_writes_pass_with_approval(patchfile, text, template) -> None:
    assert _run(template.format(p=patchfile(text)), approve=True) == ALLOW


PATCH_ALLOWS = [
    ("docs-only", DOCS_PATCH, "git apply {p}"),
    ("tests-only", TESTS_PATCH, "git apply {p}"),
    ("docs-only-am", DOCS_PATCH, "git am {p}"),
    ("docs-only-stdin", DOCS_PATCH, "patch -p1 < {p}"),
    # Decision, pinned: --check parses the patch and reports whether it would
    # apply. It writes nothing -- not the tree, not the index -- and it is the
    # question an operator asks BEFORE requesting approval. Blocking the
    # rehearsal is how a guard gets switched off.
    ("git-apply-check", HOOKS_PATCH, "git apply --check {p}"),
    ("git-apply-check-reverse", HOOKS_PATCH, "git apply --check -R {p}"),
    # `patch ORIGINAL patchfile` writes ORIGINAL and nothing else, and ORIGINAL
    # is a word in the command, judged by the ordinary path.
    ("patch-explicit-original", HOOKS_PATCH, f"patch {SCRATCH} {{p}}"),
]


@pytest.mark.parametrize(
    "text,template",
    [(t, c) for _, t, c in PATCH_ALLOWS],
    ids=[n for n, _, _ in PATCH_ALLOWS],
)
def test_patches_outside_the_policy_still_apply(patchfile, text, template) -> None:
    assert _run(template.format(p=patchfile(text))) == ALLOW


def test_missing_patch_file_is_blocked(tmp_path) -> None:
    assert _run(f"git apply {tmp_path}/does-not-exist.patch") == BLOCK


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads unreadable files")
def test_unreadable_patch_file_is_blocked(patchfile) -> None:
    p = patchfile(DOCS_PATCH)
    os.chmod(p, 0o000)
    try:
        assert _run(f"git apply {p}") == BLOCK
    finally:
        os.chmod(p, 0o600)


def test_text_that_is_not_a_unified_diff_is_blocked(patchfile) -> None:
    assert _run(f"git apply {patchfile(NOT_A_PATCH, 'notes.txt')}") == BLOCK


@pytest.mark.parametrize(
    "command",
    [
        "cat /tmp/zzz.patch | git apply",
        "curl -s https://example.invalid/x.patch | git apply -p1",
        "git apply",
        "cat /tmp/zzz.patch | patch -p1",
    ],
    ids=["pipe", "curl-pipe", "bare", "pipe-to-patch"],
)
def test_patch_source_that_cannot_be_read_is_blocked(command: str) -> None:
    """Fail closed: content that is not on disk cannot be inspected."""
    assert _run(command) == BLOCK


def test_heredoc_patch_is_read_as_a_patch(tmp_path) -> None:
    blocked = "git apply - <<'EOF'\n" + HOOKS_PATCH + "EOF"
    allowed = "git apply - <<'EOF'\n" + DOCS_PATCH + "EOF"
    assert _run(blocked) == BLOCK
    assert _run(allowed) == ALLOW


def test_block_message_names_the_path_from_inside_the_patch(patchfile) -> None:
    """The operator has to see WHICH protected path the patch would write."""
    proc = subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(
            {
                "tool_name": "Bash",
                "tool_input": {"command": f"git apply {patchfile(HOOKS_PATCH)}"},
            }
        ),
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
    assert PROTECTED in proc.stderr


def test_guard_still_parses_under_bash_3_2(tmp_path) -> None:
    """macOS ships bash 3.2, and it parses heredoc bodies inside `$( )`.

    A modern `bash -n` reports this file clean while 3.2 dies on an apostrophe
    in a python comment, so the syntax check has to name the old interpreter.
    """
    if not Path("/bin/bash").exists():
        pytest.skip("no /bin/bash")
    proc = subprocess.run(
        ["/bin/bash", "-n", str(HOOK)], capture_output=True, text=True, check=False
    )
    assert proc.returncode == 0, proc.stderr
