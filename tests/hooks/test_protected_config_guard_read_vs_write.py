"""Read-versus-write regression suite for hooks/protected-config-write-guard.sh.

Companion to test_protected_config_write_guard.py, which asks whether every way
of writing a protected path is caught. This file asks the other half of the same
question, on the shapes that actually occurred: does ordinary read-only work, and
ordinary authoring of a NON-protected file, survive the guard?

The cases are not invented. They were harvested from this project's own Claude
Code transcripts by replaying every Bash command whose tool_result carried the
guard's block banner as a harness error, and then classifying each by what it
really does. Three families came out of that pass, and each is pinned below:

  FP-1  an interpreter that only READS a protected file. `open(` counted as a
        write wherever the substring appeared, so `json.load(open(SETTINGS))`
        was read as writing to SETTINGS. Largest single family.
  FP-2  a heredoc whose owner was misread. `mkdir -p d && cat > d/r.md <<MD`
        resolved the LINE to mkdir instead of the SEGMENT to cat, so the prose
        of a report was scanned as a program and every protected path it
        mentioned became a write.
  FP-3  `tee docs/r.md <<MD`. tee copies stdin to its own arguments and never
        interprets it, so its heredoc is data.

The same pass turned up two FALSE NEGATIVES, which matter more than any of the
above and are pinned here too:

  FN-1  process substitution was never analysed at all, so
        `diff <(sed -i s/a/b/ hooks/x.sh) f` rewrote a protected file behind a
        command word that is a reader.
  FN-2  the heredoc-owner bug ran in both directions: `cat f && python3 <<PY`
        resolved to cat, so a real program was filed as inert data.

Every case runs the real hook against a real harness payload and asserts on the
exit code. The guard judges the command, it never runs it, so nothing here
touches disk.
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

# A protected path that does not exist on disk.
PROTECTED = "hooks/zzz-guard-probe.sh"
PROTECTED_DIR = "hooks/_lib"
SETTINGS = ".claude/settings.json"
SCRATCH_DOC = "/tmp/zzz-guard-report.md"

BLOCK = 2
ALLOW = 0


def _run(command: str) -> int:
    env = {
        "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
        "HOME": os.environ.get("HOME", ""),
        "CLAUDE_PROJECT_DIR": str(REPO),
    }
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


# --------------------------------------------------------------------------
# Must NOT block: reading a protected path, or writing somewhere else.
# --------------------------------------------------------------------------
READ_ONLY: list[tuple[str, str]] = [
    # The shapes named in the brief. All of these already passed before the
    # 2026-08-19 fix; they are kept so a future widening cannot lose them.
    ("grep-with-parens-in-pattern", f'grep -rln "context_budget_filter_json()" {PROTECTED_DIR}/'),
    ("grep", f"grep -n foo {PROTECTED}"),
    ("cat", f"cat {PROTECTED}"),
    ("sed-print", f"sed -n '1,50p' {PROTECTED}"),
    ("head", f"head -20 {PROTECTED}"),
    ("wc", f"wc -l {PROTECTED}"),
    ("ls", f"ls -la {PROTECTED_DIR}"),
    ("find", "find hooks -name '*.sh'"),
    ("git-diff", f"git diff -- {PROTECTED}"),
    ("git-log", f"git log --oneline -- {PROTECTED}"),
    ("mention-writing-elsewhere", f'echo "{PROTECTED_DIR}" > /tmp/nota.txt'),
    # Resolved 2026-08-20 by the `-c` fix (96367406e): `python3 -c` now gets its
    # program parsed the way a heredoc always was, so a read-only program is
    # read as one. Moved out of CONSERVATIVE_OVERBLOCKS in the same commit that
    # observed it, per that list's own contract; the write shapes it could have
    # let through are pinned in REAL_WRITES above.
    (
        "dash-c-read-only",
        f"python3 -c \"import json; print(len(json.load(open('{SETTINGS}'))))\"",
    ),
    # cp FROM a protected path writes to its second operand, which is scratch.
    ("cp-from-protected-to-scratch", f"cp {PROTECTED} /tmp/zzz-copy.sh"),
    ("command-substitution-reader", f"n=$(wc -c < {PROTECTED}); echo $n"),
    ("process-substitution-reader", f"diff <(cat {PROTECTED}) <(cat {PROTECTED})"),
    ("process-substitution-arg", f"grep foo <(cat {PROTECTED})"),
    ("nested-substitution-in-string", f'echo "$(head -1 {PROTECTED})"'),
    # FP-1: an interpreter that only reads.
    (
        "heredoc-open-default-mode",
        f"python3 - <<'PY'\nimport json\nd=json.load(open('{SETTINGS}'))\nprint(list(d))\nPY",
    ),
    (
        "heredoc-open-mode-r",
        f"python3 - <<'PY'\nprint(open('{SETTINGS}', 'r').read())\nPY",
    ),
    (
        "heredoc-open-mode-rb",
        f"python3 - <<'PY'\nprint(len(open('{SETTINGS}', 'rb').read()))\nPY",
    ),
    (
        "heredoc-open-encoding-kwarg",
        f"python3 - <<'PY'\nprint(open('{SETTINGS}', encoding='utf-8').read())\nPY",
    ),
    (
        "heredoc-open-nested-call-arg",
        "python3 - <<'PY'\nimport os\n"
        f"print(open(os.path.join('hooks', 'x.sh')).read())\nPY",
    ),
    # FP-2 / FP-3: authoring a NON-protected document that mentions protected paths.
    (
        "heredoc-report-after-mkdir",
        f"mkdir -p /tmp/zzz-rep && cat > {SCRATCH_DOC} <<'MD'\n"
        f"We had to mkdir and chmod under {PROTECTED_DIR} today.\nMD",
    ),
    (
        "heredoc-report-via-tee",
        f"tee {SCRATCH_DOC} > /dev/null <<'MD'\n"
        f"Run mkdir on {PROTECTED_DIR} and touch {PROTECTED}.\nMD",
    ),
    (
        "heredoc-report-via-cat",
        f"cat > {SCRATCH_DOC} <<'MD'\nchmod +x {PROTECTED}\nMD",
    ),
]


# --------------------------------------------------------------------------
# Must block: a real write reaching a protected path.
# --------------------------------------------------------------------------
REAL_WRITES: list[tuple[str, str]] = [
    ("sed-i", f"sed -i 's/a/b/' {PROTECTED}"),
    ("sed-i-suffix", f"sed -i.bak 's/a/b/' {PROTECTED}"),
    ("redirect-truncate", f"echo x > {PROTECTED}"),
    ("redirect-append", f"echo x >> {PROTECTED}"),
    ("read-protected-write-protected", f"cat {PROTECTED} > hooks/zzz-guard-out.sh"),
    ("cp", f"cp /tmp/zzz-src hooks/zzz-guard-out.sh"),
    ("mv", f"mv /tmp/zzz-src hooks/zzz-guard-out.sh"),
    ("rm", f"rm -f {PROTECTED}"),
    ("tee", f"tee {PROTECTED}"),
    ("tee-with-heredoc", f"tee {PROTECTED} <<'EOF'\nx\nEOF"),
    ("heredoc-into-protected", f"cat > {PROTECTED} <<'EOF'\n#!/bin/bash\nEOF"),
    (
        "heredoc-into-protected-after-mkdir",
        f"mkdir -p /tmp/zzz-rep && cat > {PROTECTED} <<'EOF'\nx\nEOF",
    ),
    ("chmod", f"chmod +x {PROTECTED}"),
    ("truncate", f"truncate -s 0 {PROTECTED}"),
    ("awk-inplace", f"awk -i inplace '{{print}}' {PROTECTED}"),
    ("yq-inplace", f"yq -i '.a=1' {SETTINGS}"),
    ("git-apply", "git apply /tmp/zzz.patch"),
    ("patch-stdin", "patch -p1 < /tmp/zzz.patch"),
    # The mode analysis must not become a way through.
    (
        "heredoc-open-mode-w",
        f"python3 - <<'PY'\nopen('{PROTECTED}','w').write('x')\nPY",
    ),
    (
        "heredoc-open-mode-a",
        f"python3 - <<'PY'\nf=open('{PROTECTED}', 'a')\nf.write('x')\nPY",
    ),
    (
        "heredoc-open-mode-r-plus",
        f"python3 - <<'PY'\nf=open('{PROTECTED}', 'r+')\nf.write('x')\nPY",
    ),
    (
        "heredoc-open-mode-is-a-variable",
        f"python3 - <<'PY'\nm='w'\nopen('{PROTECTED}', m).write('x')\nPY",
    ),
    (
        "heredoc-open-mode-kwarg-w",
        f"python3 - <<'PY'\nopen('{PROTECTED}', mode='w').write('x')\nPY",
    ),
    (
        "heredoc-os-open-flags",
        f"python3 - <<'PY'\nimport os\nos.open('{PROTECTED}', os.O_WRONLY)\nPY",
    ),
    (
        "heredoc-write-text",
        f"python3 - <<'PY'\nfrom pathlib import Path\nPath('{PROTECTED}').write_text('x')\nPY",
    ),
    ("bash-c-redirect", f'bash -c "echo x > {PROTECTED}"'),
    # FN-1: a writer hidden inside a process substitution.
    ("procsub-runs-sed-i", f"diff <(sed -i 's/a/b/' {PROTECTED}) /dev/null"),
    ("procsub-runs-tee", f"cat <(tee {PROTECTED})"),
    # FN-2: the heredoc owner is the segment, so a program stays a program.
    (
        "heredoc-owner-is-second-segment",
        f"cat /etc/hostname && python3 <<'PY'\nopen('{PROTECTED}','w').write('x')\nPY",
    ),
    # The fence for the 2026-08-20 widening: `-c` was taught to be read like a
    # heredoc, so every write shape reachable through `-c` is pinned here. If a
    # future widening trades these away, it fails here and not in a transcript.
    ("dash-c-open-mode-w", f"python3 -c \"open('{PROTECTED}','w').write('x')\""),
    (
        "dash-c-write-text",
        f"python3 -c \"import pathlib; pathlib.Path('{PROTECTED}').write_text('x')\"",
    ),
    (
        "dash-c-os-open-flags",
        f"python3 -c \"import os; os.open('{PROTECTED}', os.O_WRONLY)\"",
    ),
    # cp reads its first operand and writes its second: the direction matters.
    ("cp-into-protected", f"cp /tmp/zzz-copy.sh {PROTECTED}"),
]


@pytest.mark.parametrize(
    "command", [c for _, c in READ_ONLY], ids=[n for n, _ in READ_ONLY]
)
def test_read_only_work_is_not_blocked(command: str) -> None:
    assert _run(command) == ALLOW, f"guard blocked read-only work: {command}"


@pytest.mark.parametrize(
    "command", [c for _, c in REAL_WRITES], ids=[n for n, _ in REAL_WRITES]
)
def test_real_writes_to_protected_paths_stay_blocked(command: str) -> None:
    assert _run(command) == BLOCK, f"protected write slipped through: {command}"


# --------------------------------------------------------------------------
# Known conservative over-blocks, asserted as the guard's CURRENT contract.
#
# These are read-only in fact and blocked in practice. They are pinned rather
# than skipped so the cost is visible and any change to it is deliberate: a
# future fix flips the assertion here instead of quietly widening the guard.
#
# `python3 -c "<program>"` gets its program as an argument rather than on stdin,
# and the segment scan reads every protected path in that argument as an
# operand. Making it symmetric with the heredoc path means trusting
# body_can_write -- a denylist of write primitives, which the guard's own author
# called unwinnable -- through a second syntax. That is a decision about the
# false-positive / false-negative trade, and it belongs to the operator, not to
# the agent that noticed it. Measured 2026-08-19: this family accounted for
# roughly a quarter of the read-only blocks in the session transcripts.
# --------------------------------------------------------------------------
CONSERVATIVE_OVERBLOCKS: list[tuple[str, str]] = [
    # A command word the guard cannot see inside. The script's argument is a
    # string to the guard, and any protected path in it reads as an operand.
    # Resolving this means executing or resolving the helper, which the guard
    # must never do -- so this one is expected to stay.
    (
        "helper-script-with-protected-arg",
        f"/tmp/zzz-helper.sh 'grep -rn foo {PROTECTED_DIR}/'",
    ),
]


@pytest.mark.parametrize(
    "command",
    [c for _, c in CONSERVATIVE_OVERBLOCKS],
    ids=[n for n, _ in CONSERVATIVE_OVERBLOCKS],
)
def test_known_conservative_overblocks_still_block(command: str) -> None:
    """Pins the residual cost so it stays visible and cannot drift unnoticed."""
    assert _run(command) == BLOCK, (
        "this over-block was resolved; move the case into READ_ONLY and record "
        f"the operator decision that allowed it: {command}"
    )
