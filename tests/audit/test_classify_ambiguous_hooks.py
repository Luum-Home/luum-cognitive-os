"""Pin the event-semantics rule in ``scripts/classify_ambiguous_hooks.py``.

The classifier exists because a source grep alone gets this wrong: Claude Code
gives exit code 2 a different meaning per harness event. The same ``exit 2``
blocks a tool call on PreToolUse and merely prints to stderr on PostToolUse,
where the tool has already run. So "contains a block emitter" and "can block"
are different claims, and collapsing them is the specific defect this script
was written to detect.

This test executes the classifier over the real hook set and asserts that
separation still holds. It is the contract, not the counts: a hook whose only
wiring is a non-blocking event must never be reported as an effective gate,
because that is the report an operator would act on.

Note on the exit code: this script exits 1 by design while any hook classifies
as ``neither`` (wired but neither blocking nor recording). That population is a
standing operator finding, not a gate at zero, and it is deliberately NOT
ratcheted here -- no baseline was ever measured for it, and inventing one in
this test would be authoring a cushion rather than recording a decision.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "classify_ambiguous_hooks.py"

# Mirrors BLOCKING_EVENTS in the script under test. Duplicated intentionally:
# if the script's own set is edited, this test must disagree and fail rather
# than silently adopt the new definition.
BLOCKING_EVENTS = {"PreToolUse", "UserPromptSubmit", "Stop", "SubagentStop"}


@pytest.fixture(scope="module")
def rows() -> list[dict]:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--json"],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    # Exit 1 means "neither"-class hooks exist, which is a finding, not an error.
    assert proc.returncode in (0, 1), f"classifier errored (exit {proc.returncode}):\n{proc.stderr}"
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:  # pragma: no cover - diagnostic path
        pytest.fail(f"classifier emitted non-JSON: {exc}\nstderr:\n{proc.stderr}")
    assert payload["total"] > 0, "classifier walked zero hooks"
    assert len(payload["rows"]) == payload["total"]
    return payload["rows"]


def test_script_matches_the_blocking_event_set_under_test() -> None:
    """The classifier's own event set must match what this test asserts against."""
    source = SCRIPT.read_text(encoding="utf-8")
    for event in BLOCKING_EVENTS:
        assert f'"{event}"' in source, f"{event} no longer named in the classifier"


def test_effective_gates_are_wired_on_a_blocking_event(rows) -> None:
    """gate-effective must require a harness event where exit 2 actually blocks."""
    offenders = [
        (r["name"], r["events"])
        for r in rows
        if r["verdict"] == "gate-effective" and not (set(r["events"]) & BLOCKING_EVENTS)
    ]
    assert offenders == [], (
        f"hooks reported as effective gates with no blocking event: {offenders}. "
        f"On PostToolUse/SessionStart/PreCompact, exit 2 informs but prevents nothing."
    )
    assert any(r["verdict"] == "gate-effective" for r in rows), (
        "no hook classified gate-effective at all -- the classifier stopped discriminating"
    )


def test_advisory_gates_are_exactly_the_misplaced_block_emitters(rows) -> None:
    """gate-advisory means: it has a block emitter, wired where it cannot block."""
    advisory = [r for r in rows if r["verdict"] == "gate-advisory"]
    assert advisory, "no gate-advisory hooks -- the class collapsed"
    for r in advisory:
        assert r["block_sites"], (
            f"{r['name']} classified gate-advisory without any block emitter"
        )
        assert not (set(r["events"]) & BLOCKING_EVENTS), (
            f"{r['name']} is advisory yet wired on a blocking event {r['events']} -- "
            f"it should be gate-effective"
        )


def test_every_declared_gate_class_carries_its_evidence(rows) -> None:
    """No hook may be called any kind of gate without a located block emitter."""
    gate_classes = {"gate-effective", "gate-advisory", "gate-unreachable"}
    missing = [
        r["name"]
        for r in rows
        if r["verdict"] in gate_classes and not r["block_sites"]
    ]
    assert missing == [], f"gate-classified hooks with no block site evidence: {missing}"
