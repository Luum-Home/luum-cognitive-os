#!/usr/bin/env python3
# SCOPE: os-only
"""Refine, per harness event, the behavioural class the census already derived.

A hook called `-check` / `-detector` / `-validator` does not say whether it
BLOCKS (gate) or only OBSERVES (instrument). Neither does a hook called `-gate`:
`decision-depth-gate` and `dod-gate` state in their own source that they never
exit non-zero. As of 2026-08-15 the census (audit_gate_registration.py) no
longer classifies by name either — both scripts read scripts/hook_behavior.py,
so they cannot disagree about what a gate is. What is left for THIS script is
the question the census deliberately does not answer: given the harness event a
hook is registered on, does its block emitter actually prevent anything?

The default population is therefore no longer "hooks with an ambiguous token in
the name". It is the set whose FILENAME disagrees with its behaviour — the
disagreement itself, which is the thing worth reading. `--all` covers all 256.

This script answers two separate questions per hook, with evidence:

  1. CAN it block?      -> comment-stripped source scan for a block emitter,
                           crossed with the harness event it is registered on.
  2. DID it ever block? -> `.cognitive-os/metrics/hook-timing.jsonl` (+ rotated
                           `.archive/*.gz`) and `hook-health.jsonl`.

Why the event matters (this is the part a source grep alone gets wrong).
Claude Code gives exit code 2 a DIFFERENT meaning per event:

    PreToolUse        exit 2 -> tool call is blocked            (blocking)
    UserPromptSubmit  exit 2 -> prompt is erased, not processed (blocking)
    Stop/SubagentStop exit 2 -> termination is blocked          (blocking)
    PostToolUse       exit 2 -> stderr shown to the model, the tool ALREADY ran
    SessionStart      exit 2 -> advisory only
    PreCompact        exit 2 -> advisory only

So a hook that contains `exit 2` and is registered only on PostToolUse cannot
block anything: it is a declared gate wired onto a non-blocking surface.

Classification produced:

    gate-effective    block emitter + reachable on a blocking event
    gate-advisory     block emitter, but wired on a non-blocking event: it can
                      tell the model off after the fact, never prevent the act
    gate-unreachable  block emitter with no harness event at all
    instrument        no block emitter, writes an artifact (JSONL/report/context)
    neither           no block emitter, nothing persisted, output reaches nobody

Wiring is read from FIVE surfaces (delegated to audit_gate_registration.py):
`.claude/settings.json`, dispatcher fan-out, DEFAULT_HOOKS projected into every
consumer install, packages/*/cos-package.yaml, and — added 2026-08-15 — the
hook configs of OTHER harnesses (.cursor/hooks.json, .devin/hooks.json,
.kiro/hooks/*.kiro.hook, .codex/hooks.json), which execute repo hooks by path
and which every previous census missed.

Read-only. Exit codes: 0 = no `neither`, 1 = at least one `neither`, 2 = error.

Usage:
    .venv/bin/python scripts/classify_ambiguous_hooks.py            # table
    .venv/bin/python scripts/classify_ambiguous_hooks.py --json     # rows
    .venv/bin/python scripts/classify_ambiguous_hooks.py --all      # all 256

"""
from __future__ import annotations

import gzip
import importlib.util
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

# ---------------------------------------------------------------- reuse audit
_spec = importlib.util.spec_from_file_location(
    "audit_gate_registration", REPO / "scripts" / "audit_gate_registration.py")
_audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_audit)  # type: ignore[union-attr]

# ------------------------------------------------------------------ semantics
# Events on which a non-zero-2 exit actually stops something happening.
BLOCKING_EVENTS = {"PreToolUse", "UserPromptSubmit", "Stop", "SubagentStop"}
ADVISORY_EVENTS = {"PostToolUse", "SessionStart", "SessionEnd", "PreCompact",
                   "Notification", "SubagentStart", "TeammateIdle",
                   "TaskCreated", "TaskCompleted"}

# Block detection, artifact detection, delegate-following and the class rule all
# live in scripts/hook_behavior.py now. They used to live HERE, correct, while
# the census that feeds this script decided the same question from the filename.
# One rule, one file: that is the whole point of the unification.
from hook_behavior import (  # noqa: E402
    behaviour_class, scan_source, name_class,
)


def settings_events() -> dict[str, set[str]]:
    """hook basename -> set of harness events it is registered on.

    Reads only cfg['hooks'][EVENT][*]['hooks'][*]['command'] — a hook merely
    MENTIONED elsewhere in the file is not registered. (Verified 2026-08-15:
    text-level mentions and real registrations both come to 155, so the
    parent audit's text grep is not currently inflating anything. The strict
    parse is kept so it stays true if a commented-out block is ever added.)
    """
    ev: dict[str, set[str]] = defaultdict(set)
    for settings in (".claude/settings.json", ".claude/settings.local.json"):
        p = REPO / settings
        if not p.is_file():
            continue
        try:
            cfg = json.loads(p.read_text())
        except json.JSONDecodeError:
            continue
        for event, groups in (cfg.get("hooks") or {}).items():
            for group in groups or []:
                for entry in (group or {}).get("hooks", []) or []:
                    for m in re.finditer(r"([A-Za-z0-9_.-]+)\.sh",
                                         entry.get("command", "")):
                        ev[m.group(1)].add(event)
    return ev


def dispatcher_events(direct_ev: dict[str, set[str]]) -> dict[str, set[str]]:
    """A fanned-out hook inherits the event(s) of its live dispatcher."""
    fan = _audit.dispatcher_fanout()
    out: dict[str, set[str]] = defaultdict(set)
    for disp, targets in fan.items():
        if disp not in direct_ev:
            continue
        for t in targets:
            out[t] |= direct_ev[disp]
    return out


def telemetry() -> dict[str, dict]:
    """hook -> {runs, exits{code:n}, first, last} across live + rotated files."""
    out: dict[str, dict] = {}
    files: list[Path] = []
    md = REPO / ".cognitive-os" / "metrics"
    for name in ("hook-timing.jsonl", "hook-health.jsonl"):
        if (md / name).is_file():
            files.append(md / name)
    files += sorted((md / ".archive").glob("hook-timing-*.jsonl*"))
    files += sorted((md / ".archive").glob("hook-health-*.jsonl*"))
    for f in files:
        opener = gzip.open if f.suffix == ".gz" else open
        try:
            with opener(f, "rt", errors="ignore") as fh:  # type: ignore[operator]
                for line in fh:
                    try:
                        d = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    h = d.get("hook")
                    if not h:
                        continue
                    e = out.setdefault(h, {"runs": 0, "exits": {},
                                           "first": None, "last": None})
                    e["runs"] += 1
                    code = str(d.get("exit_code"))
                    e["exits"][code] = e["exits"].get(code, 0) + 1
                    ts = d.get("timestamp")
                    if ts:
                        e["first"] = ts if not e["first"] else min(e["first"], ts)
                        e["last"] = ts if not e["last"] else max(e["last"], ts)
        except OSError:
            continue
    return out


def classify_row(row: dict, ev: set[str], scan: dict) -> tuple[str, str]:
    policy_blocks = scan["block_sites_policy"]
    wired = bool(row["wiring"])
    blocking_ev = ev & BLOCKING_EVENTS
    writes = bool(scan["artifact_signals"]) or scan["emits_context"]

    if policy_blocks:
        if blocking_ev:
            return "gate-effective", f"blocks on {','.join(sorted(blocking_ev))}"
        if not wired:
            return "gate-unreachable", "block emitter, no executor on any surface"
        if ev:
            # It can still tell the model off AFTER the fact; it cannot prevent.
            return "gate-advisory", ("block emitter on non-blocking event(s) "
                                     f"{','.join(sorted(ev))}: informs, never prevents")
        return "gate-unreachable", ("block emitter, wired only via "
                                    f"{','.join(row['wiring'])} — no harness event "
                                    "in this repo's settings")
    if writes:
        return "instrument", ",".join(scan["artifact_signals"]) or "context-only"
    # Nothing persisted. Distinguish "shouts into the void" from "does nothing".
    # Claude Code only folds a hook's stdout into the model's context on
    # SessionStart / UserPromptSubmit; elsewhere an exit-0 hook's output is
    # transcript-only, and stderr on exit 0 reaches nobody.
    if scan["writes_stdout"] and (ev & {"SessionStart", "UserPromptSubmit"}):
        return "instrument", "stdout folded into context (no persisted artifact)"
    if scan["warns_stderr"] or scan["writes_stdout"]:
        return "neither", ("prints a warning that neither blocks nor persists"
                           f"{' (unwired)' if not wired else ''}")
    return "neither", "no block emitter, no artifact write, no output"


def main() -> int:
    want_all = "--all" in sys.argv
    hooks = _audit.census()
    direct = _audit.direct_registrations()
    fan = _audit.dispatcher_fanout()
    prof = _audit.profile_registrations()
    yreg = _audit.yaml_registry()
    consumer = _audit.consumer_projection()
    harness_native = _audit.harness_native_registrations()

    live = {d for d in fan if d in direct}
    transitive: set[str] = set()
    for d in live:
        transitive |= fan[d]

    direct_ev = settings_events()
    disp_ev = dispatcher_events(direct_ev)
    tele = telemetry()

    rows = []
    for real, e in hooks.items():
        p = Path(real)
        cls, _ = _audit.classify(e["name"], p)
        n_cls = name_class(e["name"])
        # The population used to be "hooks with an ambiguous TOKEN in the name",
        # which is exactly the criterion this whole change exists to retire.
        # Now it is the set the filename gets WRONG — the disagreement itself.
        if not want_all and n_cls == cls:
            continue
        names = {e["name"]} | {Path(a).stem for a in e["aliases"]}
        wiring = []
        if names & direct:
            wiring.append("settings")
        if names & transitive:
            wiring.append("dispatcher")
        if names & prof:
            wiring.append("profile")
        if names & yreg:
            wiring.append("cognitive-os.yaml")
        if names & consumer:
            wiring.append("consumer-install")
        if names & harness_native:
            wiring.append("harness-native")
        ev: set[str] = set()
        for n in names:
            ev |= direct_ev.get(n, set()) | disp_ev.get(n, set())
        scan = scan_source(p)
        row = {"name": e["name"], "real": e["real"],
               "behaviour_class": cls, "name_class": n_cls,
               "wiring": wiring, "events": sorted(ev)}
        verdict, why = classify_row(row, ev, scan)
        t = tele.get(e["name"], {})
        row.update({
            "verdict": verdict,
            "delegates_to": scan["delegates_to"],
            "why": why,
            "block_sites": scan["block_sites_policy"],
            "block_sites_argparse_only": [b for b in scan["block_sites"]
                                          if b["argparse"]],
            "artifact_signals": scan["artifact_signals"],
            "emits_context": scan["emits_context"],
            "warns_stderr": scan["warns_stderr"],
            "writes_stdout": scan["writes_stdout"],
            "telemetry_runs": t.get("runs", 0),
            "telemetry_exits": t.get("exits", {}),
            "ever_blocked": t.get("exits", {}).get("2", 0) > 0,
            "telemetry_window": [t.get("first"), t.get("last")],
        })
        rows.append(row)

    rows.sort(key=lambda r: (r["verdict"], r["name"]))
    neither = [r for r in rows if r["verdict"] == "neither"]

    if "--json" in sys.argv:
        print(json.dumps({"total": len(rows), "rows": rows}, indent=2))
        return 1 if neither else 0

    counts: dict[str, int] = defaultdict(int)
    for r in rows:
        counts[r["verdict"]] += 1
    print(f"hooks classified: {len(rows)}"
          f"{' (all hooks)' if want_all else ' (filename disagrees with behaviour)'}")
    for k in ("gate-effective", "gate-advisory", "gate-unreachable",
              "instrument", "neither"):
        print(f"  {k:<16} {counts.get(k, 0):>4}")
    obs = sum(1 for r in rows if r["telemetry_runs"])
    blocked = sum(1 for r in rows if r["ever_blocked"])
    print(f"\ntelemetry: {obs}/{len(rows)} observed running, "
          f"{blocked} observed exiting 2")
    print(f"{'hook':<42} {'verdict':<15} {'runs':>6} {'blocked':>7}  events / why")
    for r in rows:
        print(f"{r['name']:<42} {r['verdict']:<15} {r['telemetry_runs']:>6} "
              f"{'YES' if r['ever_blocked'] else '-':>7}  "
              f"{','.join(r['events']) or '(no event)'} | {r['why']}")
    return 1 if neither else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)
