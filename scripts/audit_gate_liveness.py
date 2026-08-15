#!/usr/bin/env python3
# SCOPE: os-only
"""Classify every WIRED gate into the four liveness quadrants.

Read-only, deterministic. Exit codes: 0 = no theatre, 1 = theatre found, 2 = error.

Two INDEPENDENT questions, never collapsed into one:

  (1) CAN it block?    Static reachability of a blocking exit, read out of the
                       source. A gate whose only `exit 2` sits behind a
                       condition that cannot hold under the current
                       configuration is a FALSE gate no matter how it is wired.
  (2) DID it block?    Telemetry: `exit_code == 2` rows in hook-timing.jsonl.

Crossing them gives four quadrants with genuinely different meanings:

  can + did      -> live        (working as designed)
  can + never    -> untested    (may be fine: nobody did the bad thing yet)
  cannot + never -> THEATRE     (the finding: registered, inert, invisible)
  cannot + did   -> telemetry-lying (static read is wrong, or the row is stale)

Unreachability patterns detected (each one confirmed in this repo):

  jq-polarity     `jq -r '.ok // true'` returns the alternative for BOTH false
                  and null, so it can never yield "false". Killed claim-validator
                  and dispatch-gate. Only the BLOCK-ON-FALSE polarity is broken;
                  `.block // false` read as block-on-true is sound.
  phase-pinned    Guard chain requires phase in (production, maintenance) while
                  cognitive-os.yaml pins phase: reconstruction.
  self-declared   The source itself says it never exits non-zero.
  no-block-path   No blocking exit in the file at all.
  exit-1-not-2    The gate prints a BLOCKED banner and then `exit 1`. Per
                  docs/04-Concepts/architecture/cos-dispatch/README.md ("Exit
                  code 2 = block"), only exit 2 blocks; exit 1 is a
                  non-blocking error. The banner lies and the tool call
                  proceeds. bash-hot-path-dispatcher.sh propagates the child rc
                  verbatim, so routing through it does not repair the code —
                  its own header ("non-zero/2 propagates the first blocking
                  child gate") conflates the two.
  policy-demoted  `cos_governance_policy_allows_block <cat>` currently returns
                  false, demoting the hard block to an advisory.

MEASURABILITY. hook-timing.jsonl is written by the timing wrapper that
scripts/generate-project-settings.sh injects into .claude/settings.json, so it
only ever sees hooks named THERE. A gate reached exclusively through
bash-hot-path-dispatcher.sh is invisible to it: the row is attributed to the
dispatcher. For those gates `ever_blocked == 0` is ABSENCE OF MEASUREMENT, not
evidence of never blocking, and they are reported as `unmeasured` rather than
silently folded into `untested`. Question (1) is unaffected — reachability is
read from source, not from telemetry — so a dispatcher-only gate can still be
classified as theatre on static grounds alone.

Usage:
    .venv/bin/python scripts/audit_gate_liveness.py            # summary table
    .venv/bin/python scripts/audit_gate_liveness.py --json     # full rows
    .venv/bin/python scripts/audit_gate_liveness.py --quadrant theatre
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

TIMING = REPO / ".cognitive-os/metrics/hook-timing.jsonl"
CONFIG = REPO / "cognitive-os.yaml"

# A blocking exit. Mirrors audit_gate_registration.BLOCK_RE so the two scripts
# agree on what "blocking" means, and stays a separate constant so a change
# here is a deliberate change, not an inherited one.
BLOCK_RE = re.compile(
    r"exit\s+2\b"
    r"|\"decision\"\s*:\s*\"block\""
    r"|permissionDecision\"?\s*:?\s*\"?deny"
    r"|'block'",
    re.IGNORECASE)

BLOCK_PHASES = ("production", "maintenance")
PHASE_CMP_RE = re.compile(
    r"(?:phase|PHASE)[^\n]{0,40}?(?:production|maintenance)"
    r"|(?:production|maintenance)[^\n]{0,40}?(?:phase|PHASE)")

# jq default-operator abuse. `a // b` yields b when a is null OR false, so an
# expression defaulting to `true` can never evaluate to "false". It is a bug
# only when a guard then tests that variable FOR "false" — the mirror polarity
# (`// false` tested for "true") is sound and must not be flagged.
JQ_TRUE_DEFAULT_ASSIGN_RE = re.compile(
    r"^\s*(\w+)=.*\bjq\b[^\n]*//\s*true", re.M)

SELF_DECLARED_RE = re.compile(
    r"never\s+exits?\s+non-?zero"
    r"|never\s+blocks?"
    r"|note\s+only",
    re.IGNORECASE)

POLICY_RE = re.compile(r"cos_governance_policy_allows_block\s+(\w[\w-]*)")

OPENERS = ("if ", "if[", "elif ", "while ", "until ", "for ", "case ")


def current_phase() -> str:
    for line in CONFIG.read_text(errors="ignore").splitlines():
        m = re.match(r"\s*phase:\s*([a-z]+)", line)
        if m:
            return m.group(1)
    return "unknown"


def policy_allows_block(category: str) -> bool | None:
    """Ask the live resolver. None when it cannot answer (it then fails closed)."""
    cos = REPO / "scripts/cos"
    if not cos.is_file():
        return None
    try:
        out = subprocess.run(
            [str(cos), "governance", "policy", "--project-dir", str(REPO),
             "--category", category, "--json"],
            capture_output=True, text=True, timeout=30, cwd=REPO).stdout
        data = json.loads(out)
    except Exception:
        return None
    if (data.get("phase") or "unknown") == "unknown":
        return None
    return bool(data.get("allowed_to_block"))


def enclosing_conditions(lines: list[str], idx: int) -> list[str]:
    """Guard chain around lines[idx], by strictly-decreasing indentation.

    Shell has no parser here, and inventing one would trade a readable
    approximation for an unreadable one. Indentation is the actual convention
    every hook in this repo follows, so it is the honest signal: walk backwards
    collecting every block opener that sits at a shallower indent than the site.
    """
    def indent(s: str) -> int:
        return len(s) - len(s.lstrip())

    site_ind = indent(lines[idx])
    chain: list[str] = []
    cur = site_ind
    for j in range(idx - 1, -1, -1):
        ln = lines[j]
        if not ln.strip() or ln.lstrip().startswith("#"):
            continue
        ind = indent(ln)
        if ind >= cur:
            continue
        s = ln.lstrip()
        if s.startswith(OPENERS) or s.endswith(("then", "do")) or re.match(r"^[\w|*\"']+\)\s*$", s):
            chain.append(s)
            cur = ind
        if ind == 0:
            break
    return chain


def analyse(path: Path, phase: str, policy_cache: dict) -> dict:
    src = path.read_text(errors="ignore")
    lines = src.splitlines()

    sites = [i for i, ln in enumerate(lines)
             if BLOCK_RE.search(ln) and not ln.lstrip().startswith("#")]

    if not sites:
        # Distinguish "does nothing" from "means to block and gets the code
        # wrong". Both are inert, but only the second is a one-character fix.
        code = [l for l in lines if not l.lstrip().startswith("#")]
        says_blocked = any(re.search(r"block(ed|ing)?\b", l, re.I) for l in code)
        exits_one = any(re.match(r"\s*exit\s+1\s*$", l) for l in code)
        if says_blocked and exits_one:
            return {"can_block": False, "reason": "exit-1-not-2",
                    "detail": "announces a block then exits 1; only exit 2 "
                              "blocks per the cos-dispatch contract",
                    "block_sites": 0, "reachable_sites": 0}
        return {"can_block": False, "reason": "no-block-path",
                "detail": "no blocking exit anywhere in the file",
                "block_sites": 0, "reachable_sites": 0}

    # Self-declaration wins: if the author wrote that it never exits non-zero,
    # that is stronger evidence than a regex hit on a string literal.
    code_only = "\n".join(l for l in lines if not l.lstrip().startswith("#"))
    doc_only = "\n".join(l for l in lines if l.lstrip().startswith("#"))
    if SELF_DECLARED_RE.search(doc_only) and not BLOCK_RE.search(code_only):
        return {"can_block": False, "reason": "self-declared",
                "detail": "source states it never exits non-zero",
                "block_sites": len(sites), "reachable_sites": 0}

    # Variables whose value comes from a `jq ... // true` expression. Testing
    # one of these for "false" is the dead branch; that link is what makes the
    # finding a bug rather than a coincidence, so it is traced, not guessed.
    poisoned = set(JQ_TRUE_DEFAULT_ASSIGN_RE.findall(src))

    reachable, blockers = [], []
    for i in sites:
        chain = enclosing_conditions(lines, i)
        joined = " ; ".join(chain)
        if phase not in BLOCK_PHASES and PHASE_CMP_RE.search(joined):
            blockers.append(("phase-pinned", f"L{i+1} behind phase in "
                                             f"{BLOCK_PHASES}, phase={phase}"))
            continue
        dead = [v for v in poisoned
                if re.search(rf'\$\{{?{v}\}}?"?\s*(?:=|==)\s*"?false', joined)]
        if dead:
            blockers.append(("jq-polarity",
                             f"L{i+1} guarded by ${dead[0]} = false, but "
                             f"${dead[0]} comes from `jq ... // true` and can "
                             "never be false"))
            continue
        reachable.append(i)

    # Every remaining path may still be demoted by governance policy.
    cats = set(POLICY_RE.findall(src))
    demoted = []
    for c in sorted(cats):
        if c not in policy_cache:
            policy_cache[c] = policy_allows_block(c)
        if policy_cache[c] is False:
            demoted.append(c)

    if reachable and demoted:
        return {"can_block": False, "reason": "policy-demoted",
                "detail": f"governance policy demotes {','.join(demoted)} to advisory",
                "block_sites": len(sites), "reachable_sites": len(reachable)}

    if not reachable:
        reasons = sorted({r for r, _ in blockers})
        return {"can_block": False, "reason": "+".join(reasons) or "unreachable",
                "detail": "; ".join(d for _, d in blockers[:3]),
                "block_sites": len(sites), "reachable_sites": 0}

    return {"can_block": True, "reason": "reachable",
            "detail": f"{len(reachable)}/{len(sites)} blocking exits unguarded "
                      f"by a pinned condition",
            "block_sites": len(sites), "reachable_sites": len(reachable)}


def telemetry() -> tuple[dict[str, int], dict[str, int], int]:
    fired: dict[str, int] = {}
    blocked: dict[str, int] = {}
    rows = 0
    if not TIMING.is_file():
        return fired, blocked, rows
    with TIMING.open(errors="ignore") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            rows += 1
            h = d.get("hook") or ""
            if not h:
                continue
            fired[h] = fired.get(h, 0) + 1
            if str(d.get("exit_code")) == "2":
                blocked[h] = blocked.get(h, 0) + 1
    return fired, blocked, rows


QUADRANT = {
    (True, True): "live",
    (True, False): "untested",
    (False, False): "theatre",
    (False, True): "telemetry-lying",
}

QUADRANTS = ("live", "untested", "unmeasured", "theatre", "telemetry-lying")


def quadrant(can_block: bool, ever_blocked: int, measurable: bool) -> str:
    q = QUADRANT[(can_block, ever_blocked > 0)]
    # Only the "never blocked" half of the table depends on telemetry. When the
    # telemetry cannot see the gate at all, saying "never blocked" would be
    # asserting a fact from a file that structurally cannot contain it.
    if q == "untested" and not measurable:
        return "unmeasured"
    return q


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--quadrant", choices=QUADRANTS)
    args = ap.parse_args()

    try:
        import audit_gate_registration as agr
    except Exception as exc:  # pragma: no cover
        print(f"error: cannot import the census: {exc}", file=sys.stderr)
        return 2

    # Population is defined by the census, not re-derived here, so the two
    # scripts can never disagree about which hooks are gates.
    rows = json.loads(subprocess.run(
        [sys.executable, str(REPO / "scripts/audit_gate_registration.py"), "--json"],
        capture_output=True, text=True, cwd=REPO).stdout)["rows"]
    gates = [r for r in rows if r["class"] == "gate" and r["wiring"]]

    phase = current_phase()
    fired, blocked, trows = telemetry()
    policy_cache: dict[str, bool | None] = {}

    out = []
    for g in gates:
        p = REPO / g["real"]
        a = analyse(p, phase, policy_cache) if p.is_file() else {
            "can_block": False, "reason": "missing", "detail": "file not found",
            "block_sites": 0, "reachable_sites": 0}
        n = g["name"]
        ever = blocked.get(n, 0)
        # The timing wrapper is injected into settings.json entries only, so a
        # gate the telemetry can speak about is one settings.json names.
        measurable = "settings" in g["wiring"] or n in fired
        out.append({
            "name": n, "path": g["real"], "wiring": g["wiring"],
            "via_dispatcher": "dispatcher" in g["wiring"],
            "in_settings": "settings" in g["wiring"],
            "measurable": measurable,
            "can_block": a["can_block"], "reason": a["reason"],
            "detail": a["detail"],
            "block_sites": a["block_sites"], "reachable_sites": a["reachable_sites"],
            "fired": fired.get(n, 0), "ever_blocked": ever,
            "quadrant": quadrant(a["can_block"], ever, measurable),
        })
    out.sort(key=lambda r: (r["quadrant"], r["name"]))

    if args.quadrant:
        out = [r for r in out if r["quadrant"] == args.quadrant]

    if args.json:
        print(json.dumps({"phase": phase, "population": len(gates),
                          "telemetry_rows": trows, "rows": out}, indent=2))
    else:
        counts: dict[str, int] = {}
        for r in out:
            counts[r["quadrant"]] = counts.get(r["quadrant"], 0) + 1
        print(f"phase={phase}  gates(wired)={len(gates)}  "
              f"telemetry_rows={trows}")
        for q in QUADRANTS:
            print(f"  {q:<16} {counts.get(q, 0)}")
        print()
        print(f"{'quadrant':<16} {'gate':<40} {'reason':<16} {'fire':>6} {'blk':>4} disp")
        for r in out:
            print(f"{r['quadrant']:<16} {r['name']:<40} {r['reason']:<16} "
                  f"{r['fired']:>6} {r['ever_blocked']:>4} "
                  f"{'Y' if r['via_dispatcher'] else '-'}")

    return 1 if any(r["quadrant"] == "theatre" for r in out) else 0


if __name__ == "__main__":
    sys.exit(main())
