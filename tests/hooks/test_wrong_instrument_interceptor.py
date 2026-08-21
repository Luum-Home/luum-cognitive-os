"""wrong-instrument-interceptor: behavioural gate.

The hook exists because a warning in prose lost to a `grep -c` that returns a
number in four seconds. So this file measures the two things that decide whether
the hook survives contact with a real session:

  * does it fire on the witness case that produced a published false negative
  * does it stay silent on legitimate traffic (false-positive rate)

Assertions about reachability are derived by parsing
`hooks/bash-hot-path-dispatcher.sh` directly -- a DIFFERENT source than the
`cos_lib.hook_registration_audit` the hook itself consults. A gate written from
the same model as the code it guards inherits the model's errors and blesses
them; two independent parsers disagreeing is a finding, not noise.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

# The hook is staged under a runbook until a human promotes it into hooks/**
# (that tree is a protected glob; see the staging README). Resolve either home so
# this file keeps testing the same artifact across the promotion.
_CANDIDATES = (
    REPO / "hooks" / "wrong-instrument-interceptor.sh",
    REPO
    / "docs/05-Methodology/runbooks/wrong-instrument-interceptor-staging"
    / "wrong-instrument-interceptor.sh",
)
_OVERRIDE = os.environ.get("COS_WII_HOOK_PATH")
HOOK = (
    Path(_OVERRIDE)
    if _OVERRIDE
    else next((p for p in _CANDIDATES if p.is_file()), None)
)

pytestmark = pytest.mark.skipif(
    HOOK is None, reason="wrong-instrument-interceptor.sh not present in either home"
)


def run_hook(command: str, tool_name: str = "Bash", **env_extra: str):
    """Feed the hook a PostToolUse payload; return (exit_code, parsed_json_or_None)."""
    payload = json.dumps({"tool_name": tool_name, "tool_input": {"command": command}})
    env = dict(os.environ)
    env["COGNITIVE_OS_PROJECT_DIR"] = str(REPO)
    env.pop("DISABLE_HOOK_WRONG_INSTRUMENT_INTERCEPTOR", None)
    env.pop("COS_DISABLE_WRONG_INSTRUMENT_INTERCEPTOR", None)
    env.update(env_extra)
    proc = subprocess.run(
        ["bash", str(HOOK)],
        input=payload,
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )
    out = proc.stdout.strip()
    if not out:
        return proc.returncode, None
    return proc.returncode, json.loads(out)


def context_of(parsed) -> str:
    return parsed["hookSpecificOutput"]["additionalContext"]


# --------------------------------------------------------------------------
# Independent oracle: which hooks does the dispatcher actually fan out to?
# --------------------------------------------------------------------------
def dispatcher_children() -> set[str]:
    text = (REPO / "hooks" / "bash-hot-path-dispatcher.sh").read_text(encoding="utf-8")
    # Only the quoted "hooks/<name>.sh" arguments handed to _run_gate/_run_many.
    body = "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("#")
    )
    return set(re.findall(r'"hooks/([a-z0-9-]+)\.sh"', body))


def test_dispatcher_oracle_is_not_empty():
    """A probe that returns the same thing on both branches of the counterfactual
    is broken. If this parse yields nothing, every reachability assertion below
    would pass vacuously."""
    children = dispatcher_children()
    assert len(children) >= 20, f"dispatcher parse yielded only {len(children)} names"
    assert "symlink-mutation-guard" in children


# --------------------------------------------------------------------------
# The witness case
# --------------------------------------------------------------------------
def test_fires_on_the_witness_case():
    """2026-08-20: three readers in a row ran this exact shape and published
    'not registered' about a hook that runs on every `rm`/`mv`/`ln`."""
    rc, parsed = run_hook("grep -c 'symlink-mutation-guard' .claude/settings.json")
    assert rc == 0, "the interceptor must never block"
    assert parsed is not None, "witness case did not fire"
    ctx = context_of(parsed)
    assert "symlink-mutation-guard: REACHABLE" in ctx
    assert "hot-path-dispatcher" in ctx
    # The message must be the executable command, not a description of it.
    assert ".venv/bin/python3 scripts/audit_hook_registration.py" in ctx


def test_witness_verdict_agrees_with_the_independent_oracle():
    _, parsed = run_hook("grep -c 'symlink-mutation-guard' .claude/settings.json")
    ctx = context_of(parsed)
    assert ("symlink-mutation-guard" in dispatcher_children()) == (
        "hot-path-dispatcher" in ctx
    )


def test_second_historical_witness_adoption_freeze_gate():
    """docs/06-Daily/reports/adopt-verdicts-freeze-link-2026-08-15.md line 127
    published `grep -c 'adoption-freeze-gate' .claude/settings.json  # -> 0`.
    Same trap, five days earlier, same false conclusion available."""
    _, parsed = run_hook("grep -c 'adoption-freeze-gate' .claude/settings.json")
    assert parsed is not None
    assert "adoption-freeze-gate: REACHABLE" in context_of(parsed)


TRUE_POSITIVES = [
    "grep -c 'symlink-mutation-guard' .claude/settings.json",
    "grep -c 'adoption-freeze-gate' .claude/settings.json",
    'rg "destructive-rm-blocker" .claude/settings.json',
    'grep -q "spdx-header-required" .claude/settings.json && echo yes || echo no',
    "cat .claude/settings.json | grep provenance-scan",
    "grep -n 'release-guard' cognitive-os.yaml",
    "grep -c network-egress-guard .codex/hooks.json",
    "grep -rn 'direct-main-guard' .claude/settings.json .codex/hooks.json",
]


@pytest.mark.parametrize("cmd", TRUE_POSITIVES)
def test_true_positives_fire(cmd):
    rc, parsed = run_hook(cmd)
    assert rc == 0
    assert parsed is not None, f"should have fired: {cmd}"
    assert "WRONG-INSTRUMENT INTERCEPT" in context_of(parsed)


# --------------------------------------------------------------------------
# Precision. An interceptor with false positives gets unregistered in a week,
# and an unregistered control is worth less than the prose it replaced.
# --------------------------------------------------------------------------
LEGITIMATE = [
    # Reading settings.json for anything that is not a hook-registration question
    "grep -n 'PreToolUse' scripts/_lib/settings-driver-claude-code.sh",
    "grep -c 'hooks/' .claude/settings.json",
    "grep -n 'model' .claude/settings.json",
    "grep -A3 'statusLine' .claude/settings.json",
    "grep -n 'env' .claude/settings.json",
    "grep -n 'permissions' .claude/settings.json",
    "jq '.hooks.PreToolUse' .claude/settings.json",
    "cat .claude/settings.json | head -40",
    "ls -la .claude/settings.json",
    "python3 -c \"import json; json.load(open('.claude/settings.json'))\"",
    "git diff .claude/settings.json | grep '^+'",
    "grep -rn 'harness' cognitive-os.yaml",
    "rg 'security' cognitive-os.yaml",
    "grep -n 'apply-efficiency-profile' scripts/_lib/settings-driver-claude-code.sh",
    "grep -c 'cognitive-os.yaml' docs/00-MOCs/entrypoints/getting-started.md",
    'echo "regenerating .claude/settings.json" && grep -rn TODO scripts/',
    "grep -v 'settings.json' .gitignore",
    "wc -l .claude/settings.json cognitive-os.yaml",
    # A hook NAME, but not over a registration surface: a different question,
    # which grep answers correctly.
    "grep -n 'symlink-mutation-guard' hooks/bash-hot-path-dispatcher.sh",
    "grep -rn 'destructive-rm-blocker' docs/",
    "rg 'release-guard' tests/",
    # A FIXTURE copy of settings.json is test data, not a registration surface:
    # the question being asked there is "what is in my fixture", and grep answers it.
    "grep -n 'symlink-mutation-guard' tests/fixtures/settings.json",
    "grep -c 'destructive-rm-blocker' build/hooks.json",
    # Prose that happens to contain the letters "grep"
    "cat docs/greppable-settings.json.md",
    # The trap command QUOTED, not invoked -- writing it into a report is
    # exactly what documenting this failure looks like.
    'echo "we ran: grep -c \'symlink-mutation-guard\' .claude/settings.json" >> notes.md',
]


@pytest.mark.parametrize("cmd", LEGITIMATE)
def test_no_false_positive(cmd):
    rc, parsed = run_hook(cmd)
    assert rc == 0
    assert parsed is None, f"FALSE POSITIVE on legitimate command: {cmd}"


def test_false_positive_rate_is_zero():
    """Reported as a rate, because that is the number that decides whether an
    operator leaves this hook registered."""
    fired = [c for c in LEGITIMATE if run_hook(c)[1] is not None]
    assert not fired, f"{len(fired)}/{len(LEGITIMATE)} false positives: {fired}"


# --------------------------------------------------------------------------
# Contract edges
# --------------------------------------------------------------------------
def test_non_bash_tool_is_ignored():
    _, parsed = run_hook(
        "grep -c 'symlink-mutation-guard' .claude/settings.json", tool_name="Edit"
    )
    assert parsed is None


def test_killswitch_silences_it():
    _, parsed = run_hook(
        "grep -c 'symlink-mutation-guard' .claude/settings.json",
        DISABLE_HOOK_WRONG_INSTRUMENT_INTERCEPTOR="true",
    )
    assert parsed is None


def test_empty_stdin_is_survivable():
    proc = subprocess.run(
        ["bash", str(HOOK)], input="", capture_output=True, text=True, timeout=30
    )
    assert proc.returncode == 0
    assert proc.stdout.strip() == ""


def test_unknown_hook_name_does_not_fire():
    """A name-shaped token that is not a hook on disk must not produce a verdict.
    Guards against the detector degrading into 'anything hyphenated'."""
    _, parsed = run_hook("grep -c 'no-such-hook-anywhere' .claude/settings.json")
    assert parsed is None


def test_output_is_valid_postoolusehook_json():
    _, parsed = run_hook("grep -c 'symlink-mutation-guard' .claude/settings.json")
    assert parsed["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
    assert isinstance(parsed["hookSpecificOutput"]["additionalContext"], str)


def test_message_carries_no_bare_prose_directive():
    """'Run the gate' is prose again. The injected text must contain a command a
    reader can paste."""
    _, parsed = run_hook("grep -c 'symlink-mutation-guard' .claude/settings.json")
    ctx = context_of(parsed)
    for cmd in (
        ".venv/bin/python3 scripts/audit_hook_registration.py",
        ".venv/bin/python3 scripts/audit_gate_registration.py",
    ):
        assert cmd in ctx
        assert (REPO / cmd.split()[-1]).is_file(), f"{cmd} points at a missing script"


def test_message_does_not_punish_the_reader_with_someone_elses_red():
    """audit_hook_registration.py has exited 1 since 2026-05-31 over an unrelated
    orphan. If the injected text just says "run the gate", the reader collects a red
    that is not theirs and learns to stop running it -- the exact dynamic that let
    the cheap wrong measurement win. So the message must disclose the debt, and must
    do it without inventing a second count of its own."""
    _, parsed = run_hook("grep -c 'symlink-mutation-guard' .claude/settings.json")
    ctx = context_of(parsed)
    assert "scores the WHOLE repo" in ctx
    assert "does not depend on the gate's exit code" in ctx
    # No freshly-invented tally: a number here would need its own command.
    assert not re.search(r"exiting 1 over \d+", ctx)
