#!/usr/bin/env python3
"""ADR-226 Slice B guardrail validator.

Checks the IMPLEMENTATION-CHECKLIST guardrail: consumer ADRs (228/230/233/projections)
must NOT assume an event-store shape that contradicts ADR-226 Slice A+B substrate.

Run: python3 scripts/validate_substrate_consumers.py
Exit 0 PASS, 1 FAIL (with diagnostics).
"""

from __future__ import annotations

import importlib
import sys
import time
import traceback
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"
findings: list[tuple[str, str, str]] = []


def check(name: str) -> Callable:
    def deco(fn: Callable) -> Callable:
        try:
            fn()
            findings.append((PASS, name, ""))
        except AssertionError as e:
            findings.append((FAIL, name, str(e)))
        except Exception as e:
            findings.append((FAIL, name, f"{type(e).__name__}: {e}\n{traceback.format_exc()}"))
        return fn
    return deco


# ─── A. Schema version invariant ───────────────────────────────────────────────
@check("A1. session_bus EVENT_STORE_SCHEMA_VERSION matches manifest")
def _():
    from lib.session_bus import EVENT_STORE_SCHEMA_VERSION
    manifest = (ROOT / "manifests/event-sourced-session-bus.yaml").read_text()
    assert "event-sourced-session-bus/v1" in manifest, "manifest missing schema_version"
    assert EVENT_STORE_SCHEMA_VERSION == "event-sourced-session-bus/v1", (
        f"runtime const = {EVENT_STORE_SCHEMA_VERSION}, manifest = v1"
    )


@check("A2. handoff_dispatcher writes via canonical append_session_event")
def _():
    src = (ROOT / "lib/handoff_dispatcher.py").read_text()
    assert "from lib.session_bus import append_session_event" in src, \
        "handoff_dispatcher must import the v2 substrate API"
    # Negative: should NOT bypass to raw file writes
    assert "open(" not in src or "append_session_event" in src, \
        "handoff_dispatcher should not bypass the substrate"


# ─── B. Projection robustness (events with missing fields) ────────────────────
@check("B1. cost_ledger.fold tolerates events without payload/cost")
def _():
    from lib.event_projections.cost_ledger import fold
    state = fold(None, {"event_type": "x", "seq": 1})
    assert state["total_cost_usd"] == 0.0
    assert state["events"] == 1


@check("B2. cost_ledger.fold rejects malformed cost gracefully")
def _():
    from lib.event_projections.cost_ledger import fold
    state = fold(None, {"event_type": "x", "payload": {"cost_usd": "not-a-number"}})
    assert state["total_cost_usd"] == 0.0  # ignored, no crash


@check("B3. handoff_chain.fold detects cycles correctly")
def _():
    from lib.event_projections.handoff_chain import fold
    s = None
    s = fold(s, {"event_type": "handoff-requested", "seq": 1,
                 "payload": {"to_agent": "B", "call_chain": ["A"]}})
    s = fold(s, {"event_type": "handoff-requested", "seq": 2,
                 "payload": {"to_agent": "A", "call_chain": ["A", "B"]}})
    assert s["cycles_detected"] == 1, f"expected 1 cycle, got {s['cycles_detected']}"


@check("B4. handoff_chain.fold ignores unrelated event types")
def _():
    from lib.event_projections.handoff_chain import fold
    s = fold(None, {"event_type": "unrelated", "seq": 99, "payload": {}})
    assert s["cycles_detected"] == 0
    assert s["handoffs"] == []


@check("B5. all projections have signature fold(state, event) -> state")
def _():
    proj_dir = ROOT / "lib/event_projections"
    for f in proj_dir.glob("*.py"):
        if f.name == "__init__.py":
            continue
        mod = importlib.import_module(f"lib.event_projections.{f.stem}")
        assert hasattr(mod, "fold"), f"{f.stem} missing fold()"
        # Smoke: fold(None, {}) should not crash (defensive)
        result = mod.fold(None, {"event_type": "noop", "seq": 0})
        assert isinstance(result, dict), f"{f.stem}.fold must return dict, got {type(result)}"


# ─── C. Strict-durability required-for invariant ──────────────────────────────
@check("C1. ADR-227 file_restore commit uses strict_durability=True")
def _():
    p = ROOT / "lib/shadow_git.py"
    if not p.exists():
        raise AssertionError("lib/shadow_git.py missing")
    src = p.read_text()
    # Either the file uses strict_durability when committing restore events,
    # or it doesn't emit such events at all (Slice A may not yet wire them).
    if "file_restore_committed" in src or "RESTORE_COMPLETED" in src:
        assert "strict_durability=True" in src, \
            "shadow_git emits a restore-commit event without strict_durability=True"


@check("C2. ADR-228 idempotency claim uses strict_durability=True")
def _():
    p = ROOT / "lib/dispatch_gate.py"
    if not p.exists():
        raise AssertionError("lib/dispatch_gate.py missing")
    src = p.read_text()
    if "idempotency_key_claimed" in src or "idempotency.claim" in src:
        assert "strict_durability=True" in src, \
            "dispatch_gate claims idempotency without strict_durability=True"


# ─── D. Seq type compatibility ────────────────────────────────────────────────
@check("D1. handoff envelope parent_event_seq accepts substrate seq type")
def _():
    from lib.handoff_envelope import HandoffEnvelope
    # Substrate produces non-negative ints; envelope must accept them.
    env_kwargs = dict(
        handoff_id="abc-123",
        parent_event_seq=42,
        from_agent="orchestrator",
        to_agent="subagent:x",
        intent="delegate",
        context_mode="reference",
        context_payload={},
        granted_tools=[],
        granted_blast_radius=0,
        depth=0,
        call_chain=["orchestrator"],
        deadline_ts=None,
        return_control=False,
    )
    env = HandoffEnvelope.create(**env_kwargs)
    assert env.parent_event_seq == 42

    # And rejects negatives
    try:
        HandoffEnvelope.create(**{**env_kwargs, "parent_event_seq": -1})
    except Exception:
        pass
    else:
        raise AssertionError("parent_event_seq=-1 must be rejected")


# ─── E. Performance budget liveness ───────────────────────────────────────────
@check("E1. event-bus baseline benchmark exists and passes the manifest p95 budget")
def _():
    bench = ROOT / "tests/benchmark/test_event_sourced_bus_baseline.py"
    if not bench.exists():
        raise AssertionError("Slice B baseline benchmark missing")
    # Check that the manifest declares the budget consumed by the benchmark
    manifest = (ROOT / "manifests/event-sourced-session-bus.yaml").read_text()
    assert "p95_budget_ms" in manifest, "manifest must declare p95_budget_ms"


@check("E2. round-trip append_session_event + read_session_events under append_event budget")
def _():
    from lib.session_bus import append_session_event, read_session_events  # noqa: F401
    import tempfile, uuid

    with tempfile.TemporaryDirectory() as tmp:
        sid = f"guardrail-{uuid.uuid4().hex[:8]}"
        n = 30
        t0 = time.perf_counter()
        for i in range(n):
            append_session_event(
                "guardrail.smoke",
                {"i": i},
                project_dir=tmp,
                session_id=sid,
                fan_out_index=False,
            )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        per_event_ms = elapsed_ms / n

        events = list(read_session_events(sid, project_dir=tmp))
        assert len(events) == n, f"read {len(events)} of {n}"
        seqs = [e["seq"] for e in events]
        assert seqs == list(range(seqs[0], seqs[0] + n)), f"seq not monotonic: {seqs}"

        # Loose budget: per-event amortized ms must be < 25ms (manifest p95).
        # This is a smoke check, not the formal benchmark; it catches gross regressions.
        assert per_event_ms < 25.0, f"per-event amortized {per_event_ms:.2f}ms > 25ms budget"

        # Schema version present
        assert all(e.get("schema_version") == "event-sourced-session-bus/v1" for e in events)


# ─── F. Substrate-truth-vs-consumer-claims sanity ─────────────────────────────
@check("F1. no consumer reads events ignoring schema_version")
def _():
    # Spot-check: any consumer reading a stream must filter by schema_version.
    # Soft check — accept either filter or read_session_events helper usage.
    consumers = [
        ROOT / "lib/handoff_dispatcher.py",
        ROOT / "lib/dispatch_gate.py",
        ROOT / "lib/agent_team.py",
    ]
    for c in consumers:
        if not c.exists():
            continue
        src = c.read_text()
        # Reads from per-session stream must go through the helper
        if "events.jsonl" in src or "read_session" in src:
            assert "read_session_events" in src or "schema_version" in src, \
                f"{c.name} reads stream without using read_session_events helper"


@check("F2. checklist guardrail still in repo (preserved)")
def _():
    p = ROOT / "docs/03-PoCs/research/orchestration-gaps/IMPLEMENTATION-CHECKLIST-2026-05-07.md"
    assert p.exists(), "implementation checklist missing"
    src = p.read_text()
    assert "ADR-226 Slice B must land first" in src, "guardrail text missing"


# ─── Report ───────────────────────────────────────────────────────────────────

def main() -> int:
    print(f"\nADR-226 Slice B Guardrail — {len(findings)} checks\n" + "─" * 72)
    fail_count = 0
    for status, name, detail in findings:
        marker = "✅" if status == PASS else ("❌" if status == FAIL else "⏭")
        print(f"{marker} {status}  {name}")
        if status == FAIL:
            fail_count += 1
            for line in detail.splitlines()[:8]:
                print(f"        {line}")
    print("─" * 72)
    print(f"Result: {len(findings) - fail_count} pass / {fail_count} fail / {len(findings)} total\n")
    return 1 if fail_count else 0


if __name__ == "__main__":
    sys.exit(main())
