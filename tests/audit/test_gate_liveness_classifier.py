"""Pin the gate-liveness classifier to the false-gate patterns it must catch.

scripts/audit_gate_liveness.py answers two questions that must never collapse
into one: can a wired gate block (static reachability), and did it ever block
(telemetry). This test guards the static half against regression, because that
is the half that produces the finding — a gate reported as blocking while its
only blocking exit is unreachable.

Fixtures are synthetic hooks written to tmp_path. No repo hook is read here, so
the test stays green when the real hooks are legitimately fixed.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent.parent
SCRIPT = REPO / "scripts" / "audit_gate_liveness.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("audit_gate_liveness", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _analyse(mod, tmp_path, body: str, phase: str = "reconstruction"):
    p = tmp_path / "fixture-gate.sh"
    p.write_text(body)
    # Empty policy cache: no fixture calls the governance resolver.
    return mod.analyse(p, phase, {})


def test_plain_exit_2_is_reachable(mod, tmp_path):
    r = _analyse(mod, tmp_path, '#!/usr/bin/env bash\nif [ "$X" = "bad" ]; then\n  exit 2\nfi\nexit 0\n')
    assert r["can_block"] is True
    assert r["reason"] == "reachable"


def test_phase_pinned_exit_2_is_unreachable(mod, tmp_path):
    body = (
        '#!/usr/bin/env bash\n'
        'PHASE=$(get_phase)\n'
        'if [ "$PHASE" = "production" ] || [ "$PHASE" = "maintenance" ]; then\n'
        '  exit 2\n'
        'fi\n'
        'exit 0\n'
    )
    r = _analyse(mod, tmp_path, body, phase="reconstruction")
    assert r["can_block"] is False
    assert r["reason"] == "phase-pinned"
    # Same source, production phase: the very same exit becomes reachable.
    assert _analyse(mod, tmp_path, body, phase="production")["can_block"] is True


def test_jq_default_true_can_never_be_false(mod, tmp_path):
    """`jq '.ok // true'` yields the alternative for false AND null.

    This is the bug that killed claim-validator and dispatch-gate: the block
    branch tests for "false", which the expression cannot produce.
    """
    body = (
        '#!/usr/bin/env bash\n'
        'OK=$(printf "%s" "$R" | jq -r \'.ok // true\')\n'
        'if [ "$OK" = "false" ]; then\n'
        '  exit 2\n'
        'fi\n'
        'exit 0\n'
    )
    r = _analyse(mod, tmp_path, body)
    assert r["can_block"] is False
    assert r["reason"] == "jq-polarity"


def test_jq_default_false_block_on_true_is_sound(mod, tmp_path):
    """The mirror polarity is NOT a bug and must not be flagged.

    `.block // false` still yields true when block is genuinely true, so a
    gate reading it as block-on-true is reachable. Flagging it would be a false
    positive that trains readers to ignore the real one.
    """
    body = (
        '#!/usr/bin/env bash\n'
        'BLOCK=$(printf "%s" "$R" | jq -r \'.block // false\')\n'
        'if [ "$BLOCK" = "true" ]; then\n'
        '  exit 2\n'
        'fi\n'
        'exit 0\n'
    )
    assert _analyse(mod, tmp_path, body)["can_block"] is True


def test_exit_1_after_a_block_banner_does_not_block(mod, tmp_path):
    """Only exit 2 blocks; exit 1 is a non-blocking error the agent walks past.

    See docs/04-Concepts/architecture/cos-dispatch/README.md ("Exit code 2 =
    block"). A gate that announces BLOCKED and exits 1 is inert, and routing it
    through bash-hot-path-dispatcher.sh does not repair it: the dispatcher
    propagates the child return code verbatim.
    """
    body = (
        '#!/usr/bin/env bash\n'
        '[ -z "$BAD" ] && exit 0\n'
        'echo "=== COMMIT BLOCKED ===" >&2\n'
        'exit 1\n'
    )
    r = _analyse(mod, tmp_path, body)
    assert r["can_block"] is False
    assert r["reason"] == "exit-1-not-2"


def test_no_blocking_exit_at_all(mod, tmp_path):
    r = _analyse(mod, tmp_path, '#!/usr/bin/env bash\necho warn >&2\nexit 0\n')
    assert r["can_block"] is False
    assert r["reason"] == "no-block-path"


def test_quadrants_separate_unmeasured_from_untested(mod):
    """A gate the telemetry cannot see must not be reported as "never blocked".

    hook-timing.jsonl only records hooks named in .claude/settings.json, so for
    a dispatcher-only gate a zero count is absence of measurement.
    """
    assert mod.quadrant(True, 1, True) == "live"
    assert mod.quadrant(True, 0, True) == "untested"
    assert mod.quadrant(True, 0, False) == "unmeasured"
    assert mod.quadrant(False, 0, True) == "theatre"
    assert mod.quadrant(False, 0, False) == "theatre"
    assert mod.quadrant(False, 3, True) == "telemetry-lying"


def test_script_is_read_only(mod):
    """The classifier must never mutate the repo it audits."""
    src = SCRIPT.read_text()
    for forbidden in ("write_text(", "open(.*'w'", "unlink(", "mkdir("):
        assert forbidden not in src, f"classifier must stay read-only: {forbidden}"
