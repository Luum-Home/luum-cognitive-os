"""Pin the hook classifier to BEHAVIOUR and away from the filename.

scripts/hook_behavior.py replaced a name-token rule that three separate censuses
each carried their own copy of. The rule decided that a hook called
`secret-detector` was "ambiguous" (token: detector) while it emitted
`permissionDecision: "block"`, and that 82 hooks with no token at all were
"instruments" by falling through a final `else`.

These tests state the property that must hold: the class follows what the source
DOES, and a filename that suggests otherwise changes nothing except the
`name_class` signal.

Fixtures are synthetic hooks written to tmp_path. No repo hook is read here, so
the tests stay green when the real hooks are legitimately fixed — and they would
have failed against the old classifier, which is the point.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent.parent
SCRIPT = REPO / "scripts" / "hook_behavior.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("hook_behavior", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _classify(mod, tmp_path, filename: str, body: str):
    p = tmp_path / filename
    p.write_text(body)
    cls, can_block, name_cls, scan = mod.classify(Path(filename).stem, p)
    return cls, can_block, name_cls, scan


# --------------------------------------------------------------- the two forms
# of blocking. Claude Code accepts a blocking exit code AND a blocking JSON
# decision on stdout with exit 0. A classifier that knows only the first files
# every hook of the second kind as an instrument.

def test_exit_2_is_a_gate(mod, tmp_path):
    cls, can_block, _, _ = _classify(
        mod, tmp_path, "some-instrument.sh",
        '#!/usr/bin/env bash\nif [ "$X" = bad ]; then\n  exit 2\nfi\n')
    assert (cls, can_block) == ("gate", True)


def test_permission_decision_block_with_exit_0_is_a_gate(mod, tmp_path):
    """The secret-detector shape: blocks via JSON, exits 0, named `-detector`."""
    cls, can_block, name_cls, _ = _classify(
        mod, tmp_path, "credential-detector.sh",
        '#!/usr/bin/env bash\n'
        'jq -n \'{hookSpecificOutput:{permissionDecision:"block",\n'
        '  permissionDecisionReason:"secret"}}\'\n'
        'exit 0\n')
    assert (cls, can_block) == ("gate", True)
    assert name_cls == "ambiguo", "the filename is what used to hide this hook"


def test_decision_block_json_is_a_gate(mod, tmp_path):
    cls, _, _, _ = _classify(
        mod, tmp_path, "quiet-thing.sh",
        '#!/usr/bin/env bash\necho \'{"decision": "block"}\'\nexit 0\n')
    assert cls == "gate"


# ------------------------------------------------- the filename cannot promote

def test_gate_in_the_name_does_not_make_a_gate(mod, tmp_path):
    """The decision-depth-gate / dod-gate shape: gate name, never blocks.

    The old rule classified these as gates, and the liveness audit then reported
    them as `theatre`. They are honest instruments.
    """
    cls, can_block, name_cls, _ = _classify(
        mod, tmp_path, "decision-depth-gate.sh",
        '#!/usr/bin/env bash\n'
        '# Advisory only: this hook never exits non-zero.\n'
        'echo "depth looks shallow" >> "$X/.cognitive-os/metrics/depth.jsonl"\n'
        'exit 0\n')
    assert (cls, can_block) == ("instrument", False)
    assert name_cls == "gate"


def test_block_word_in_a_comment_is_not_a_block(mod, tmp_path):
    """Whole-line comments are stripped before the scan; prose is not evidence."""
    cls, _, _, _ = _classify(
        mod, tmp_path, "policy-guard.sh",
        '#!/usr/bin/env bash\n'
        '# This guard would exit 2 to block, but that path was removed.\n'
        '# "decision": "block"\n'
        'exit 0\n')
    assert cls == "inert"


# ---------------------------------------------------- instrument vs inert vs else

def test_no_token_in_name_is_not_silently_an_instrument(mod, tmp_path):
    """The 82-hook bug: no token in the name used to mean `instrument` by default.

    Here the hook persists nothing, so it is `inert`, and the name signal is
    reported as `unnamed` instead of vanishing into an `else`.
    """
    cls, _, name_cls, _ = _classify(
        mod, tmp_path, "session-init.sh",
        '#!/usr/bin/env bash\necho "hello"\nexit 0\n')
    assert cls == "inert"
    assert name_cls == "unnamed"


def test_jsonl_write_makes_an_instrument(mod, tmp_path):
    cls, can_block, _, scan = _classify(
        mod, tmp_path, "whatever.sh",
        '#!/usr/bin/env bash\n'
        'echo "{}" >> "$D/.cognitive-os/metrics/thing.jsonl"\nexit 0\n')
    assert (cls, can_block) == ("instrument", False)
    assert "jsonl" in scan["artifact_signals"]


def test_additional_context_makes_an_instrument(mod, tmp_path):
    cls, _, _, _ = _classify(
        mod, tmp_path, "ctx.sh",
        '#!/usr/bin/env bash\n'
        'jq -n \'{hookSpecificOutput:{additionalContext:"note"}}\'\nexit 0\n')
    assert cls == "instrument"


# ------------------------------------------------------- argparse is not policy

def test_argparse_exit_2_is_not_a_policy_block(mod, tmp_path):
    """`exit 2` on a bad flag is argument validation, not enforcement."""
    cls, can_block, _, scan = _classify(
        mod, tmp_path, "tool-gate.sh",
        '#!/usr/bin/env bash\n'
        'case "$1" in\n'
        '  *) echo "usage: tool-gate.sh <path>" >&2; exit 2 ;;\n'
        'esac\n')
    assert (cls, can_block) == ("inert", False)
    assert scan["block_sites"], "the site is still recorded, just not as policy"
    assert not scan["block_sites_policy"]


# -------------------------------------------------------- one-hop delegation

def test_a_wrapper_inherits_its_delegate_block(mod, tmp_path, monkeypatch):
    """`completeness-check.sh` shape: a thin wrapper that execs a real gate."""
    monkeypatch.setattr(mod, "REPO", tmp_path)
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "real_gate.sh").write_text(
        '#!/usr/bin/env bash\nif [ -n "$BAD" ]; then\n  exit 2\nfi\n')
    cls, can_block, _, scan = _classify(
        mod, tmp_path, "thin-wrapper.sh",
        '#!/usr/bin/env bash\nexec bash "scripts/real_gate.sh" "$@"\n')
    assert (cls, can_block) == ("gate", True)
    assert any("real_gate.sh" in d for d in scan["delegates_to"])


def test_a_swallowed_delegate_does_not_make_a_gate(mod, tmp_path, monkeypatch):
    """`|| true` discards the child's exit code, so no block can propagate."""
    monkeypatch.setattr(mod, "REPO", tmp_path)
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "real_gate.sh").write_text(
        '#!/usr/bin/env bash\nexit 2\n')
    cls, can_block, _, _ = _classify(
        mod, tmp_path, "lenient-guard.sh",
        '#!/usr/bin/env bash\nbash "scripts/real_gate.sh" || true\n')
    assert (cls, can_block) == ("inert", False)


# ----------------------------------------------------- the name is only a signal

@pytest.mark.parametrize("filename,expected", [
    ("destructive-rm-blocker.sh", "gate"),
    ("tool-sequence-capture.sh", "instrument"),
    ("secret-detector.sh", "ambiguo"),
    ("session-init.sh", "unnamed"),
])
def test_name_class_is_reported_but_never_decides(mod, filename, expected):
    assert mod.name_class(Path(filename).stem) == expected


def test_behaviour_class_ignores_the_name_entirely(mod, tmp_path):
    """Same body, four names: one class."""
    body = '#!/usr/bin/env bash\nif [ "$X" = bad ]; then\n  exit 2\nfi\n'
    seen = {_classify(mod, tmp_path, n, body)[0] for n in
            ("a-gate.sh", "b-monitor.sh", "c-detector.sh", "d.sh")}
    assert seen == {"gate"}
