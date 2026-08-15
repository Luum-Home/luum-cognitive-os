#!/usr/bin/env python3
# SCOPE: os-only
"""Recount unregistered gates: canonical census x class x executor surface x git history.

Read-only. Exit codes: 0 = no unwired gates, 1 = unwired gates found, 2 = error.

Why this exists (and what it corrects in the 2026-08-15 architecture audit):

  * "Registered" was measured only against `.claude/settings.json`. That file is
    GENERATED. A gate can be wired through (a) a projected dispatcher that fans
    out to it, (b) a security profile applied by set-security-profile.sh, or
    (c) the cognitive-os.yaml harness registry that feeds the projector.
    `destructive-rm-blocker` is wired through (a) and was reported as dead.

  * Symlinks were counted as distinct hooks. A symlink and its target are ONE
    hook; this census keys on os.path.realpath.

  * The repo already ships `scripts/check_hook_registration.py`, which exits 0
    because 185 hooks sit in a grandfathered allowlist. This script deliberately
    does NOT honour that allowlist for counting: it reports the raw wiring truth
    and separately reports whether a written decision covers each gate.

Usage:
    .venv/bin/python scripts/audit_gate_registration.py          # summary
    .venv/bin/python scripts/audit_gate_registration.py --json   # full rows
    .venv/bin/python scripts/audit_gate_registration.py --history  # + git archaeology
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

GATE_TOKENS = ["guard", "gate", "enforcer", "blocker", "interceptor", "limiter",
               "firewall", "lock", "freeze"]
INSTRUMENT_TOKENS = ["capture", "heartbeat", "emit", "metric", "watchdog",
                     "tracker", "sync", "snapshot", "monitor", "logger",
                     "recorder", "reporter", "collector", "notifier",
                     "aggregator", "meter"]
AMBIGUOUS_TOKENS = ["check", "validator", "detector", "scan", "advisor",
                    "reminder", "audit", "review", "verify", "classifier"]

BLOCK_RE = re.compile(
    r"exit\s+2\b"
    r"|\"decision\"\s*:\s*\"block\""
    r"|permissionDecision\"?\s*:?\s*\"?deny"
    r"|'block'",
    re.IGNORECASE)

HOOK_REF = re.compile(r"([A-Za-z0-9_.-]+)\.sh\b")


def sh(cmd: str) -> str:
    return subprocess.run(cmd, shell=True, cwd=REPO, capture_output=True,
                          text=True).stdout


def read(p: Path) -> str:
    try:
        return p.read_text(errors="ignore") if p.is_file() else ""
    except OSError:
        return ""


def census() -> dict[str, dict]:
    """Canonical hook census keyed by realpath. A symlink and its target are ONE."""
    out: dict[str, dict] = {}
    roots = [REPO / "hooks"] + sorted(REPO.glob("packages/*/hooks"))
    for root in roots:
        if not root.is_dir():
            continue
        for p in sorted(root.rglob("*.sh")):
            rel = p.relative_to(REPO).as_posix()
            if "/_lib/" in rel or "/_archived/" in rel or rel.endswith(".disabled"):
                continue
            real = os.path.realpath(p)
            e = out.setdefault(real, {"aliases": [], "name": Path(real).stem,
                                      "real": rel})
            e["aliases"].append(rel)
            # prefer the top-level hooks/ path as the canonical display path
            if rel.startswith("hooks/"):
                e["real"] = rel
    return out


def classify(name: str, src: str) -> tuple[str, bool]:
    low = name.lower()
    can_block = bool(BLOCK_RE.search(src))
    gate_n = any(t in low for t in GATE_TOKENS)
    instr_n = any(t in low for t in INSTRUMENT_TOKENS)
    amb_n = any(t in low for t in AMBIGUOUS_TOKENS)
    if gate_n and not instr_n:
        return "gate", can_block
    if instr_n and not gate_n:
        return ("ambiguo" if can_block else "instrument"), can_block
    if amb_n:
        return "ambiguo", can_block
    return ("gate" if can_block else "instrument"), can_block


def direct_registrations() -> set[str]:
    """Hook basenames named by a concrete settings artifact the harness reads."""
    txt = "\n".join(read(REPO / p) for p in (
        ".claude/settings.json", ".claude/settings.local.json",
        ".codex/hooks.json"))
    return {m.group(1) for m in HOOK_REF.finditer(txt)}


# An invocation is either a call to one of the dispatcher's _run* helpers
# (_run_gate / _run_many / _run_hook ...) or a shell exec of a quoted hook path.
EXEC_LINE = re.compile(r"_run[a-z_]*\s|\bbash\b|\bexec\b|\bsource\b|\B\.\s+\"|\"hooks/")


def dispatcher_fanout() -> dict[str, set[str]]:
    """dispatcher-basename -> set of hook basenames it actually EXECUTES.

    Only counts lines that invoke (bash/exec/source/_run_gate) and ignores
    hooks/_lib/ helper sourcing, which every hook does and which registers
    nothing.
    """
    out: dict[str, set[str]] = {}
    for p in sorted(REPO.glob("hooks/*.sh")) + sorted(REPO.glob("packages/*/hooks/*.sh")):
        txt = read(p)
        if not txt:
            continue
        named = set()
        # Join backslash line-continuations first: dispatchers list their
        # fan-out targets as continuation lines under a single _run_gate call,
        # so a per-line scan misses every target but the first.
        joined: list[str] = []
        buf = ""
        for line in txt.splitlines():
            buf += line.rstrip()
            if buf.endswith("\\"):
                buf = buf[:-1] + " "
                continue
            joined.append(buf)
            buf = ""
        if buf:
            joined.append(buf)
        for s in joined:
            s = s.strip()
            if s.startswith("#") or not EXEC_LINE.search(s):
                continue
            if "_lib/" in s:
                continue
            for m in HOOK_REF.finditer(s):
                if m.group(1) != p.stem:
                    named.add(m.group(1))
        if named:
            out[p.stem] = named
    return out


def profile_registrations() -> set[str]:
    txt = "\n".join(read(p) for p in
                    sorted(REPO.glob("templates/security-profiles/*.json")))
    return {m.group(1) for m in HOOK_REF.finditer(txt)}


def consumer_projection() -> set[str]:
    """Hooks projected into CONSUMER installs.

    This is the surface every prior count missed. `scripts/cos_init.py`
    DEFAULT_HOOKS and `scripts/generate-project-settings.sh` DEFAULT_HOOKS are
    the ADR-093 default tier: hooks copied and registered in every external
    project. A hook can be absent from this repo's own .claude/settings.json
    and still ship enabled to every consumer.
    """
    names: set[str] = set()
    py = read(REPO / "scripts/cos_init.py")
    m = re.search(r"DEFAULT_HOOKS\s*=\s*\((.*?)\)\.split\(\)", py, re.S)
    if m:
        names |= set(re.findall(r"[A-Za-z0-9_-]+", m.group(1).replace('"', " ")))
    sh_txt = read(REPO / "scripts/generate-project-settings.sh")
    m = re.search(r'DEFAULT_HOOKS="(.*?)"', sh_txt, re.S)
    if m:
        names |= {x.removesuffix(".sh") for x in re.findall(r"[A-Za-z0-9_-]+\.sh", m.group(1))}
    # package manifests declare hooks shipped + registered with a package
    for p in sorted(REPO.glob("packages/*/cos-package.yaml")):
        txt = read(p)
        for mm in re.finditer(r"(?:source|script):\s*\"?[^\"\n]*?([A-Za-z0-9_-]+)\.sh", txt):
            names.add(mm.group(1))
    return names


def yaml_registry() -> set[str]:
    """Hooks declared in the cognitive-os.yaml harness registry (projector input)."""
    txt = read(REPO / "cognitive-os.yaml")
    return {m.group(1) for m in re.finditer(r"script:\s*\S*?([A-Za-z0-9_.-]+)\.sh", txt)}


def classification_manifest() -> dict[str, dict]:
    raw = read(REPO / "manifests/hook-registration-classification.yaml")
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return {Path(e["path"]).name.removesuffix(".sh"): e
            for e in data.get("entries", [])}


def allowlist() -> set[str]:
    out = set()
    for line in read(REPO / "hooks/_lib/registration-allowlist.txt").splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            out.add(s.removesuffix(".sh"))
    return out


def history(names: list[str]) -> dict[str, list[str]]:
    """Commits where .claude/settings.json added (+) or removed (-) each hook."""
    log = sh("git log --follow --format='@@@%H|%ad|%s' --date=short "
             "-p -- .claude/settings.json")
    res: dict[str, list[str]] = {n: [] for n in names}
    pats = {n: re.compile(re.escape(n) + r"\.sh\b") for n in names}
    commit = ""
    for line in log.splitlines():
        if line.startswith("@@@"):
            commit = line[3:]
            continue
        if not line or line[0] not in "+-" or line[:3] in ("+++", "---"):
            continue
        sign = line[0]
        for n, rx in pats.items():
            if rx.search(line):
                tag = f"{sign}|{commit}"
                if tag not in res[n]:
                    res[n].append(tag)
    return res


def main() -> int:
    hooks = census()
    direct = direct_registrations()
    fan = dispatcher_fanout()
    prof = profile_registrations()
    yreg = yaml_registry()
    consumer = consumer_projection()
    manifest = classification_manifest()
    allow = allowlist()

    # transitive: a dispatcher that is itself directly registered
    live_dispatchers = {d for d in fan if d in direct}
    transitive: set[str] = set()
    for d in live_dispatchers:
        transitive |= fan[d]

    rows = []
    for real, e in hooks.items():
        src = read(Path(real))
        cls, can_block = classify(e["name"], src)
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
        entry = manifest.get(e["name"])
        rows.append({
            "name": e["name"], "real": e["real"], "aliases": e["aliases"],
            "class": cls, "can_block": can_block, "wiring": wiring,
            "manifest_status": entry["status"] if entry else None,
            "manifest_rationale": (entry or {}).get("rationale"),
            "allowlisted": e["name"] in allow,
        })

    gates = [r for r in rows if r["class"] == "gate"]
    unwired = [r for r in gates if not r["wiring"]]
    not_in_settings = [r for r in gates if "settings" not in r["wiring"]]

    if "--json" in sys.argv or "--history" in sys.argv:
        hist = history([r["name"] for r in not_in_settings])
        for r in rows:
            r["settings_history"] = hist.get(r["name"], [])
        if "--json" in sys.argv:
            print(json.dumps({"total": len(rows), "rows": rows}, indent=2))
            return 1 if unwired else 0
        print("=== gates absent from current .claude/settings.json ===")
        for r in sorted(not_in_settings, key=lambda x: x["name"]):
            h = r["settings_history"]
            ever = "EVER-IN-SETTINGS" if any(t.startswith("+") for t in h) else "never"
            print(f"{r['name']:<44} wiring={','.join(r['wiring']) or 'NONE':<28} "
                  f"{ever:<17} manifest={r['manifest_status']}")
            for t in h:
                print(f"      {t}")
        return 1 if unwired else 0

    counts: dict[str, int] = {}
    for r in rows:
        counts[r["class"]] = counts.get(r["class"], 0) + 1
    print(f"canonical hooks (symlink-resolved): {len(rows)}   "
          f"(aliases collapsed: {sum(len(r['aliases']) for r in rows) - len(rows)})")
    for k in sorted(counts):
        sub = [r for r in rows if r["class"] == k]
        w = sum(1 for r in sub if r["wiring"])
        print(f"  {k:<11} {len(sub):>4}   wired {w:>4}   unwired {len(sub)-w:>4}")
    print(f"\nlive dispatchers (registered + fanning out): "
          f"{sorted(live_dispatchers)}")
    print(f"gates absent from .claude/settings.json : {len(not_in_settings)}")
    print(f"gates with NO executor at all          : {len(unwired)}")
    print(f"\nallowlist entries                      : {len(allow)}")
    stale = sorted(n for n in allow
                   if any(r["name"] == n and r["wiring"] for r in rows))
    print(f"allowlist entries that ARE wired (cushion): {len(stale)}")
    if unwired:
        print("\nunwired gates:")
        for r in sorted(unwired, key=lambda x: x["name"]):
            print(f"  {r['name']:<44} block={str(r['can_block']):<5} "
                  f"manifest={r['manifest_status']} allow={r['allowlisted']}")
    return 1 if unwired else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)
