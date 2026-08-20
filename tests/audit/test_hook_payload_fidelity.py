"""The gate: a hook test may not invent the payload it feeds the hook.

Three things are proven here, and the third is what keeps the gate honest.

1. A test that fabricates a payload dict is caught, and the baseline is compared
   with **exact equality** — a file that stops fabricating must leave the list in
   the same commit, so the baseline cannot be used as a cushion.
2. The faithful builder produces what the harness sends, and refuses fields the
   harness does not send.
3. A test that *legitimately* needs a synthetic payload — malformed stdin, a
   dropped field — stays green without touching it. A gate that forbids testing
   the error path is a worse gate than none.

Evidence:
    scripts/audit_hook_payload_fidelity.py --census --live
    scripts/audit_hook_payload_fidelity.py --gate
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from tests.utils.harness_payload import (  # noqa: E402
    UnknownPayloadField,
    fields_sent,
    live_payloads,
    malformed,
    payload,
    raw,
    without,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
AUDIT = REPO_ROOT / "scripts" / "audit_hook_payload_fidelity.py"
BASELINE = REPO_ROOT / "manifests" / "hook-payload-fabrication-baseline.txt"
ENVELOPE = REPO_ROOT / "tests" / "fixtures" / "hook-payload-envelope" / "envelope.json"


def _audit(*args: str) -> dict:
    r = subprocess.run(
        [sys.executable, str(AUDIT), *args, "--json"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert r.stdout.strip(), f"audit produced nothing: {r.stderr[-800:]}"
    return json.loads(r.stdout)


# ── 1. the gate itself ───────────────────────────────────────────────────────
def test_no_new_test_fabricates_a_hook_payload():
    """Exact equality against the baseline: no new offender, no stale entry."""
    res = _audit("--gate")
    assert not res["new"], (
        "these tests build a hook payload by hand instead of calling "
        "tests.utils.harness_payload.payload(): " + ", ".join(res["new"])
    )
    assert not res["stale"], (
        "these files no longer fabricate a payload but are still listed in "
        f"{BASELINE.name} — drop them from the baseline in the same commit: "
        + ", ".join(res["stale"])
    )


def test_baseline_lists_only_files_that_exist_and_still_fabricate():
    """Anti-cushion: a baseline entry that names nothing real is a free slot."""
    listed = {
        ln.strip() for ln in BASELINE.read_text().splitlines()
        if ln.strip() and not ln.lstrip().startswith("#")
    }
    missing = sorted(p for p in listed if not (REPO_ROOT / p).exists())
    assert not missing, f"baseline names files that do not exist: {missing}"
    offenders = set(_audit("--gate")["offenders"])
    assert listed == offenders, (
        "baseline and reality disagree; regenerate with "
        "scripts/audit_hook_payload_fidelity.py --write-baseline"
    )


def test_gate_catches_a_fabricated_payload_and_clears_a_faithful_one(tmp_path):
    """The gate's own three runs, as a test rather than as a claim.

    Run A: a test file with a hand-built payload dict  -> flagged.
    Run B: the same test using the faithful builder     -> not flagged.
    Run C: a genuinely synthetic payload, marked        -> not flagged.
    """
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import importlib.util

    spec = importlib.util.spec_from_file_location("_fidelity", AUDIT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    probe_dir = REPO_ROOT / "tests" / "fixtures" / "hook-payload-envelope" / "_gate_probe"
    probe_dir.mkdir(exist_ok=True)
    a = probe_dir / "test_probe_fabricated.py"
    b = probe_dir / "test_probe_faithful.py"
    c = probe_dir / "test_probe_synthetic_marked.py"
    try:
        a.write_text(
            "import json\n"
            "def test_x():\n"
            "    p = {'tool_name': 'Bash', 'tool_input': {'command': 'ls'}}\n"
            "    assert json.dumps(p)\n"
        )
        b.write_text(
            "from tests.utils.harness_payload import raw\n"
            "def test_x():\n"
            "    assert raw('PreToolUse', tool_name='Bash',\n"
            "               tool_input={'command': 'ls'})\n"
        )
        c.write_text(
            "import json\n"
            "def test_hook_survives_a_payload_missing_tool_input():\n"
            "    # payload-synthetic: the harness always sends tool_input; this\n"
            "    # test exists to prove the hook does not crash when it is gone.\n"
            "    p = {'tool_name': 'Bash', 'hook_event_name': 'PreToolUse'}\n"
            "    assert json.dumps(p)\n"
        )
        offenders, detail = mod.gate_scan()
        rel_a = str(a.relative_to(REPO_ROOT))
        rel_b = str(b.relative_to(REPO_ROOT))
        rel_c = str(c.relative_to(REPO_ROOT))
        assert rel_a in offenders, "run A: fabricated payload was NOT caught"
        assert rel_b not in offenders, "run B: faithful builder was wrongly flagged"
        assert rel_c not in offenders, (
            "run C: a marked synthetic payload was flagged — the gate would "
            "forbid testing the malformed-payload path"
        )
    finally:
        for f in (a, b, c):
            f.unlink(missing_ok=True)
        probe_dir.rmdir()


# ── 2. the faithful builder ──────────────────────────────────────────────────
def test_builder_emits_exactly_the_fields_the_harness_sends():
    p = payload("PreToolUse", tool_name="Bash", tool_input={"command": "ls"})
    assert set(p) == fields_sent("PreToolUse")
    assert set(p) >= {"session_id", "cwd", "transcript_path", "hook_event_name"}
    assert p["hook_event_name"] == "PreToolUse"
    # raw() is what a hook actually receives on stdin: JSON, same key set.
    assert set(json.loads(raw("PreToolUse", tool_name="Bash", tool_input={}))) == set(p)
    # session_id is the field the ablation showed flipping a real verdict, so it
    # must be a fresh, non-empty id on every build — an empty one pools every
    # test into the operator's live session bucket.
    first = payload("PreToolUse", tool_name="Bash", tool_input={})["session_id"]
    second = payload("PreToolUse", tool_name="Bash", tool_input={})["session_id"]
    assert first and second and first != second


def test_builder_refuses_a_field_the_harness_does_not_send():
    """The three fields real tests in this repo invented: skill_name,
    tool_count, main_worktree. None is ever sent."""
    for invented in ("skill_name", "tool_count", "main_worktree"):
        with pytest.raises(UnknownPayloadField):
            payload("PreToolUse", tool_name="Bash", tool_input={}, **{invented: "x"})


def test_envelope_carries_no_operator_data():
    """The privacy invariant, checked here and not only at capture time."""
    blob = ENVELOPE.read_text()
    assert str(Path.home()) not in blob
    assert str(REPO_ROOT) not in blob
    assert "/Users/" not in blob and "/home/" not in blob


# ── 3. the escape hatch still works ──────────────────────────────────────────
def test_synthetic_payloads_are_still_constructible():
    assert malformed("not-json") == "this is not json at all"
    assert malformed("truncated").startswith("{")
    degraded = without("PreToolUse", "session_id", tool_name="Bash", tool_input={})
    assert "session_id" not in degraded
    assert "tool_name" in degraded


# ── 4. real content, when this machine has any ───────────────────────────────
def test_live_payloads_match_the_envelope_field_set():
    live = live_payloads("PreToolUse", limit=10)
    if not live:
        pytest.skip("no harness transcript on this machine; envelope-only run")
    sent = fields_sent("PreToolUse")
    for p in live:
        extra = set(p) - sent
        assert not extra, (
            f"the harness sent a field the envelope has never seen: {extra}. "
            "Re-capture: scripts/audit_hook_payload_fidelity.py --capture"
        )
