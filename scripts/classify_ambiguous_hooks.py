#!/usr/bin/env python3
# SCOPE: os-only
"""Classify ambiguous hooks by BEHAVIOUR, not by name.

A hook called `-check` / `-detector` / `-validator` does not say whether it
BLOCKS (gate) or only OBSERVES (instrument). This script answers two separate
questions per hook, with evidence:

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

Wiring is read from four surfaces (delegated to audit_gate_registration.py):
`.claude/settings.json`, dispatcher fan-out, DEFAULT_HOOKS projected into every
consumer install, and packages/*/cos-package.yaml.

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

BLOCK_PATTERNS = [
    ("exit2", re.compile(r"(?:^|[;&|]|\bthen\b|\belse\b|\bdo\b|\{)\s*exit\s+2\b")),
]

# These are emitted as JSON, frequently by a multi-line `jq -n` program, so a
# per-line scan misses them. `secret-detector` blocks exactly this way and a
# line-by-line grep reported it as a pure instrument.
BLOCK_MULTILINE = [
    ("decision-block", re.compile(r'"decision"\s*:\s*\\?"\s*block', re.S)),
    ("deny", re.compile(r'permissionDecision\\?"?\s*:\s*\\?"\s*(?:deny|block)', re.S)),
    ("sys-exit2", re.compile(r"sys\.exit\(\s*2\s*\)")),
]

# An `exit 2` that only fires on a malformed CLI invocation is not a policy
# block; it is argument validation. Flag those so a human can audit the call.
ARGPARSE_RE = re.compile(
    r"unknown option|usage:|requires value|--help|invalid argument|missing arg",
    re.IGNORECASE)

ARTIFACT_PATTERNS = [
    ("jsonl", re.compile(r"\.jsonl\b")),
    ("cos-state", re.compile(r"\.cognitive-os/")),
    ("append-redirect", re.compile(r">>\s*[\"'$]?\S*(?:\.cognitive-os|metrics|log)")),
    ("safe-jsonl-lib", re.compile(r"safe_jsonl_append|jsonl_append|cos_append")),
    ("additional-context", re.compile(r"additionalContext|hookSpecificOutput")),
    ("report-file", re.compile(r"docs/06-Daily/reports|/reports/")),
]

# A hook is often a thin wrapper. Follow ONE hop into what it executes, or the
# scan describes the wrapper instead of the behaviour. `completeness-check.sh`
# is 16 lines that `exec` a real gate; scanning only the wrapper called it inert.
#
# Matching the *invocation* was too brittle: hooks routinely stash the target
# in a variable first (`SCRIPT="$PROJECT_DIR/scripts/state_retention_audit.py"`
# then `python3 "$SCRIPT"`), which no call-site regex resolves. So instead we
# take any reference to an EXISTING repo file and treat it as a delegate.
# Over-inclusive by design: a hook that merely names a file it never runs gets
# its callee's signals folded in, so `delegates_to` is printed for audit.
DELEGATE_RE = re.compile(
    r"(?:hooks|scripts|lib|cos_lib|packages)/[A-Za-z0-9_./-]+\.(?:sh|py)")

# Bare sibling reference: `exec "$HOOK_DIR/predev-completeness-check.sh"`.
DELEGATE_BARE_RE = re.compile(r"[A-Za-z0-9_.-]+\.(?:sh|py)")

# Python-module handoff: `from cos_lib.skill_drift_detector import main`.
# skill-drift-detector.sh is 50 lines of guards around exactly this line, and a
# path-only scan concluded it writes nothing while it fills skill-drift.jsonl.
DELEGATE_MODULE_RE = re.compile(
    r"(?:from|import)\s+((?:cos_lib|lib|scripts)(?:\.[A-Za-z0-9_]+)+)")

# `cmd || true` (or `|| exit 0`) swallows the delegate's exit code: even if the
# delegate can exit 2, the wrapper cannot propagate a block.
SWALLOW_RE = re.compile(r"\|\|\s*(?:true|exit\s+0|:)\s*$")

# stdout on an advisory event still reaches the model as context; count only
# deliberate structured emission, not incidental echoes to the user's terminal.
CONTEXT_RE = re.compile(r"additionalContext|hookSpecificOutput|systemMessage")


def strip_comments(src: str) -> list[tuple[int, str]]:
    """(1-based lineno, code) with whole-line comments and shebang removed.

    Inline `# ...` is NOT stripped (a `#` inside a quoted string is common in
    these hooks and naive stripping produced false negatives on jq programs).
    Whole-line comments are the ones that caused false POSITIVES in the earlier
    name-based audit, and those are removed exactly.
    """
    out = []
    for i, line in enumerate(src.splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        out.append((i, line))
    return out


def _delegates(code: list[tuple[int, str]], self_name: str) -> list[tuple[str, bool]]:
    """[(repo-relative path, every-reference-swallowed)] this hook hands off to."""
    seen: dict[str, list[bool]] = {}
    for _, line in code:
        if "_lib/" in line:
            continue  # helper sourcing; not a behaviour delegate
        refs = [m.group(0) for m in DELEGATE_RE.finditer(line)]
        refs += [m.group(0) for m in DELEGATE_BARE_RE.finditer(line)]
        refs += [m.group(1).replace(".", "/") + ".py"
                 for m in DELEGATE_MODULE_RE.finditer(line)]
        for ref in refs:
            cand = next((c for c in (REPO / ref, REPO / "hooks" / ref,
                                     REPO / "scripts" / ref) if c.is_file()), None)
            if cand is None:
                continue
            rel = cand.resolve().relative_to(REPO).as_posix()
            if Path(rel).stem == self_name:
                continue
            seen.setdefault(rel, []).append(bool(SWALLOW_RE.search(line.strip())))
    return [(rel, all(sw)) for rel, sw in seen.items()]


def scan_source(path: Path, _depth: int = 0) -> dict:
    src = path.read_text(errors="ignore") if path.is_file() else ""
    code = strip_comments(src)
    joined = "\n".join(l for _, l in code)

    blocks = []
    for lineno, line in code:
        for kind, rx in BLOCK_PATTERNS:
            if rx.search(line):
                blocks.append({"line": lineno, "kind": kind, "where": path.name,
                               "code": line.strip()[:160],
                               "argparse": bool(ARGPARSE_RE.search(line))})
    for kind, rx in BLOCK_MULTILINE:
        m = rx.search(joined)
        if m:
            blocks.append({"line": joined[:m.start()].count("\n") + 1,
                           "kind": kind, "where": path.name,
                           "code": m.group(0).replace("\n", " ")[:160],
                           "argparse": False})

    artifacts = {kind for kind, rx in ARTIFACT_PATTERNS if rx.search(joined)}
    ctx = bool(CONTEXT_RE.search(joined))
    warns = bool(re.search(r"(?:echo|printf)\s+[^\n]*>&2", joined))
    speaks = bool(re.search(r"^\s*(?:echo|printf|cat)\s+(?![^\n]*>&2)", joined, re.M))
    delegated: list[str] = []

    if _depth == 0:  # follow exactly one hop
        for ref, swallowed in _delegates(code, path.stem):
            sub = scan_source(REPO / ref, _depth + 1)
            artifacts |= set(sub["artifact_signals"])
            ctx = ctx or sub["emits_context"]
            warns = warns or sub["warns_stderr"]
            speaks = speaks or sub["writes_stdout"]
            tag = f"{ref}{' (exit swallowed)' if swallowed else ''}"
            delegated.append(tag)
            if not swallowed:
                for b in sub["block_sites"]:
                    blocks.append({**b, "where": f"via {ref}"})

    return {
        "block_sites": blocks,
        "block_sites_policy": [b for b in blocks if not b["argparse"]],
        "artifact_signals": sorted(artifacts),
        "emits_context": ctx,
        "delegates_to": delegated,
        "warns_stderr": warns,
        "writes_stdout": speaks,
        "loc": len(code),
    }


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
        src = _audit.read(p)
        cls, _ = _audit.classify(e["name"], src)
        if cls != "ambiguo" and not want_all:
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
        ev: set[str] = set()
        for n in names:
            ev |= direct_ev.get(n, set()) | disp_ev.get(n, set())
        scan = scan_source(p)
        row = {"name": e["name"], "real": e["real"], "name_class": cls,
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
          f"{' (all classes)' if want_all else ' (name-ambiguous only)'}")
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
