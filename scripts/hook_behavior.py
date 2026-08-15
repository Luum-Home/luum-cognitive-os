#!/usr/bin/env python3
# SCOPE: os-only
"""Single source of truth for what a hook IS, derived from what it DOES.

Before this module, four scripts each decided independently whether a hook was a
gate, and three of them decided it from the FILENAME:

    scripts/audit_gate_registration.py       name tokens  -> gate/ambiguo/instrument
    scripts/audit_instrument_productivity.py a verbatim copy of the same tokens
    scripts/classify_ambiguous_hooks.py      behaviour (correct, but downstream)
    scripts/audit_gate_liveness.py           asked the census for its population

Measured consequences of the name-token rule on 2026-08-15 (commands in the
docstrings of the callers):

  * `hooks/secret-detector.sh` emits `permissionDecision: "block"` and exits 0.
    It blocks. The token "detector" put it in `ambiguo`, so it was NOT among the
    66 gates the liveness audit examined: a real blocker invisible to the audit
    of blockers.
  * 82 of the 119 hooks called "instrument" carried no instrument token at all.
    They landed there through the final `else` branch. "119 instruments" was the
    remainder of a subtraction.
  * `decision-depth-gate` and `dod-gate` say in their own source that they never
    exit non-zero. The token "gate" made them gates, and the liveness audit then
    reported them as theatre. They are honest instruments with a gate's name.

The rule here is the opposite: the class comes from the source, and the name is
kept only as a SIGNAL so the disagreement between the two stays measurable.

Three classes, and no "ambiguous" — behaviour never shrugs:

    gate        a policy block emitter is present (see BLOCK_* below)
    instrument  no block emitter, but it persists an artifact or feeds context
    inert       no block emitter and nothing persisted

Whether a gate can actually PREVENT anything depends on the harness event it is
registered on; that is a separate question and it lives in the callers
(classify_ambiguous_hooks.py) — it is not folded into the class.

Read-only. Importable; not a CLI.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# --------------------------------------------------------------- name signals
# Retained ONLY to measure how often the name lies. Never used to decide a class.
GATE_TOKENS = ["guard", "gate", "enforcer", "blocker", "interceptor", "limiter",
               "firewall", "lock", "freeze"]
INSTRUMENT_TOKENS = ["capture", "heartbeat", "emit", "metric", "watchdog",
                     "tracker", "sync", "snapshot", "monitor", "logger",
                     "recorder", "reporter", "collector", "notifier",
                     "aggregator", "meter"]
AMBIGUOUS_TOKENS = ["check", "validator", "detector", "scan", "advisor",
                    "reminder", "audit", "review", "verify", "classifier"]


def name_class(name: str) -> str:
    """What the FILENAME suggests. A signal to be checked, not a verdict."""
    low = name.lower()
    gate_n = any(t in low for t in GATE_TOKENS)
    instr_n = any(t in low for t in INSTRUMENT_TOKENS)
    amb_n = any(t in low for t in AMBIGUOUS_TOKENS)
    if gate_n and not instr_n:
        return "gate"
    if instr_n and not gate_n:
        return "instrument"
    if amb_n:
        return "ambiguo"
    return "unnamed"  # the old code's silent `else` branch, now visible


# ------------------------------------------------------------ block detection
# Line-scoped: an `exit 2` must be a statement, not a substring of prose.
BLOCK_PATTERNS = [
    ("exit2", re.compile(r"(?:^|[;&|]|\bthen\b|\belse\b|\bdo\b|\{)\s*exit\s+2\b")),
]

# Emitted as JSON, frequently by a multi-line `jq -n` program, so a per-line
# scan misses them. `secret-detector` blocks exactly this way (and exits 0),
# which is why an exit-code-only criterion filed it as an instrument.
BLOCK_MULTILINE = [
    ("decision-block", re.compile(r'"decision"\s*:\s*\\?"\s*block', re.S)),
    ("deny", re.compile(r'permissionDecision\\?"?\s*:\s*\\?"\s*(?:deny|block)', re.S)),
    ("sys-exit2", re.compile(r"sys\.exit\(\s*2\s*\)")),
]

# An `exit 2` that only fires on a malformed CLI invocation is argument
# validation, not policy. Those sites are recorded separately, never as a block.
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
# Matching the *invocation* was too brittle: hooks routinely stash the target in
# a variable first, which no call-site regex resolves. So any reference to an
# EXISTING repo file counts as a delegate. Over-inclusive by design, and
# `delegates_to` is reported so the over-inclusion stays auditable.
DELEGATE_RE = re.compile(
    r"(?:hooks|scripts|lib|cos_lib|packages)/[A-Za-z0-9_./-]+\.(?:sh|py)")
DELEGATE_BARE_RE = re.compile(r"[A-Za-z0-9_.-]+\.(?:sh|py)")
DELEGATE_MODULE_RE = re.compile(
    r"(?:from|import)\s+((?:cos_lib|lib|scripts)(?:\.[A-Za-z0-9_]+)+)")

# `cmd || true` (or `|| exit 0`) swallows the delegate's exit code: even if the
# delegate can exit 2, the wrapper cannot propagate a block.
SWALLOW_RE = re.compile(r"\|\|\s*(?:true|exit\s+0|:)\s*$")

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
            try:
                rel = cand.resolve().relative_to(REPO).as_posix()
            except ValueError:
                continue
            if Path(rel).stem == self_name:
                continue
            seen.setdefault(rel, []).append(bool(SWALLOW_RE.search(line.strip())))
    return [(rel, all(sw)) for rel, sw in seen.items()]


def scan_source(path: Path, _depth: int = 0) -> dict:
    """Everything the class decision needs, read out of the source."""
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


def behaviour_class(scan: dict) -> str:
    """gate | instrument | inert — from the scan, never from the name."""
    if scan["block_sites_policy"]:
        return "gate"
    if scan["artifact_signals"] or scan["emits_context"]:
        return "instrument"
    return "inert"


def classify(name: str, path: Path) -> tuple[str, bool, str, dict]:
    """(class, can_block, name_class, scan) for one hook.

    `can_block` stays a source-level fact: a policy block emitter exists. It says
    nothing about whether the harness event lets that block prevent anything.
    """
    scan = scan_source(Path(path))
    cls = behaviour_class(scan)
    return cls, bool(scan["block_sites_policy"]), name_class(name), scan
