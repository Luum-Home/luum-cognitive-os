#!/usr/bin/env python3
# SCOPE: os-only
"""Runs-vs-artifacts census for every instrument-class hook.

An instrument exists to PRODUCE something. This script pairs, for each
instrument hook, the number of times it ran against the artifact it claims to
write and whether anything in the repo reads that artifact back.

Read-only and deterministic. Never writes to `.cognitive-os/metrics/`.
Exit codes: 0 = every instrument productive, 1 = unproductive instruments
found, 2 = error.

Three columns decide the verdict:

  runs       rows in hook-timing.jsonl + hook-health.jsonl, INCLUDING the
             gzipped rotations under metrics/.archive/. Counting only the live
             files undercounts by roughly 25% and makes cheap hooks look busier
             than the expensive ones.
  artifact   the metrics/state file the hook's own source writes to, with row
             count and mtime. Resolved by scanning the hook body for paths, not
             by convention.
  consumer   whether any file outside the producing hook itself references that
             artifact path. A JSONL nobody reads is an instrument measuring
             itself.

Verdicts:
  productive     ran, wrote, and something reads the output
  no-consumer    ran and wrote, but nothing reads the artifact
  no-artifact    ran and never produced the file it names
  starved        ran a lot and produced far less than it ran (ratio gate)
  no-producer    consumes/drains an artifact that no hook writes
  idle           never ran in the retained telemetry window

Usage:
    .venv/bin/python scripts/audit_instrument_productivity.py
    .venv/bin/python scripts/audit_instrument_productivity.py --json
    .venv/bin/python scripts/audit_instrument_productivity.py --class gate
"""
from __future__ import annotations

import argparse
import functools
import gzip
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
METRICS = REPO / ".cognitive-os" / "metrics"

# Name tokens are imported, not re-listed. They no longer decide anything; they
# are used only to report how often a filename misdescribes its hook.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from hook_behavior import (  # noqa: E402
    GATE_TOKENS, INSTRUMENT_TOKENS, AMBIGUOUS_TOKENS,
)

# Hooks never write a literal path. They assign it to a shell variable first
# (ACI_FILE="$METRICS_DIR/aci-observations.jsonl") and redirect into the
# variable later. Detecting writes therefore means resolving the assignment.
ASSIGN_RE = re.compile(
    r"^\s*(?:local\s+|export\s+|readonly\s+)?([A-Za-z_][A-Za-z0-9_]*)="
    r"[\"']?([^\"'\s;)]*?([A-Za-z0-9_.-]+\.(?:jsonl|json|log|db)))[\"']?\s*$",
    re.MULTILINE)
LITERAL_RE = re.compile(r"([A-Za-z0-9_.-]+\.(?:jsonl|json|log|db))")
HELPER_INLINE_RE = re.compile(
    r"(?:safe_jsonl_append|jsonl_append|append_jsonl|atomic_write)\s+"
    r"[\"']?[^\"'\s]*?([A-Za-z0-9_.-]+\.(?:jsonl|json|log|db))")
HEREDOC_RE = re.compile(r"<<-?[\"']?(\w+)[\"']?\n(.*?)\n\1", re.DOTALL)
PY_WRITE_RE = re.compile(
    r"(?:open\(\s*[^)]*?[\"']([^\"']+\.(?:jsonl|json|log))[\"']"
    r"|[\"']([A-Za-z0-9_.-]+\.(?:jsonl|json|log))[\"'][^\n]*?"
    r"(?:\"a\"|'a'|append|write_text|dump))")


def _write_re(var: str) -> re.Pattern[str]:
    """Writes include the shared helper, not just redirects.

    Most hooks append through `safe_jsonl_append "$FILE" "$ENTRY"` from
    hooks/_lib/safe-jsonl.sh. Matching only `>>` misses nearly every real
    producer and reports live 8MB artifacts as "never written".
    """
    v = re.escape(var)
    return re.compile(
        rf">>\s*[\"']?\$\{{?{v}\}}?"          # append redirect
        rf"|>\s*[\"']?\$\{{?{v}\}}?"          # truncate redirect
        rf"|tee\s+(?:-a\s+)?[\"']?\$\{{?{v}\}}?"
        rf"|(?:mv|cp)\s+\S+\s+[\"']?\$\{{?{v}\}}?"
        rf"|(?:safe_jsonl_append|jsonl_append|append_jsonl|atomic_write)"
        rf"\s+[\"']?\$\{{?{v}\}}?")


def _read_re(var: str) -> re.Pattern[str]:
    v = re.escape(var)
    return re.compile(
        rf"(?:cat|tail|head|grep|wc|jq|awk|sed|python3?)\b[^\n]*\$\{{?{v}\}}?"
        rf"|<\s*[\"']?\$\{{?{v}\}}?")

STARVED_RATIO = 20.0     # ran >= 20x more often than it produced rows
STARVED_MIN_RUNS = 200   # ...and ran enough for the ratio to mean anything


def sh(cmd: str) -> str:
    return subprocess.run(cmd, shell=True, cwd=REPO, capture_output=True,
                          text=True).stdout


# The class is NOT decided here any more. It used to be a verbatim copy of the
# filename rule in audit_gate_registration.py, kept in sync by hand and wrong in
# both places: 82 of the 119 hooks this script called "instruments" reached that
# class through the final `else` branch, with no instrument token in the name and
# no positive evidence of instrumenting anything.
from hook_behavior import classify as _behaviour_classify  # noqa: E402
from hook_behavior import name_class  # noqa: E402


def classify(name: str, path) -> tuple[str, bool]:
    """(class, can_block) from scripts/hook_behavior.py — one rule, one file."""
    cls, can_block, _n, _scan = _behaviour_classify(name, Path(path))
    return cls, can_block


def census() -> dict[str, dict]:
    """Canonical hook census keyed by realpath: a symlink and its target are ONE."""
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
            name = Path(real).stem
            try:
                body = Path(real).read_text(errors="ignore")
            except OSError:
                body = ""
            row = out.setdefault(real, {
                "name": name, "real": os.path.relpath(real, REPO),
                "aliases": [], "body": body,
            })
            row["aliases"].append(rel)
    for row in out.values():
        row["class"], row["can_block"] = classify(row["name"], REPO / row["real"])
        row["name_class"] = name_class(row["name"])
        row["name_token"] = any(
            t in row["name"].lower()
            for t in GATE_TOKENS + INSTRUMENT_TOKENS + AMBIGUOUS_TOKENS)
    return out


def run_counts() -> dict[str, int]:
    """Rows per hook across live telemetry AND gzipped rotations."""
    counts: dict[str, int] = {}
    files: list[Path] = []
    for base in ("hook-timing.jsonl", "hook-health.jsonl"):
        p = METRICS / base
        if p.is_file():
            files.append(p)
    archive = METRICS / ".archive"
    if archive.is_dir():
        files += sorted(archive.glob("hook-timing-*.jsonl.gz"))
        files += sorted(archive.glob("hook-health-*.jsonl.gz"))
    for f in files:
        opener = gzip.open if f.suffix == ".gz" else open
        try:
            with opener(f, "rt", errors="ignore") as fh:
                for line in fh:
                    line = line.strip()
                    if not line.startswith("{"):
                        continue
                    try:
                        hook = json.loads(line).get("hook")
                    except (ValueError, TypeError):
                        continue
                    if hook:
                        counts[hook] = counts.get(hook, 0) + 1
        except OSError:
            continue
    return counts


def artifacts_for(body: str) -> tuple[list[str], list[str]]:
    """(writes, reads): artifact basenames this hook produces / consumes.

    Resolves the shell-variable indirection: an assignment binds a basename to
    a variable name, then redirects and readers are matched against that
    variable. Literal one-liner redirects are picked up as a fallback.
    """
    writes: list[str] = []
    reads: list[str] = []
    for var, _full, base in ASSIGN_RE.findall(body):
        if _write_re(var).search(body) and base not in writes:
            writes.append(base)
        elif _read_re(var).search(body) and base not in reads:
            reads.append(base)
    # Inline path passed straight to the helper, no variable in between:
    #   safe_jsonl_append "$METRICS_DIR/codebase-itinerary.jsonl" "$LINE"
    for base in HELPER_INLINE_RE.findall(body):
        if base not in writes:
            writes.append(base)
    # Literal redirects.
    for line in body.splitlines():
        if ">>" not in line and "tee " not in line:
            continue
        for base in LITERAL_RE.findall(line):
            if base not in writes:
                writes.append(base)
    # Many hooks do the real write inside an embedded `python3 <<'PY'` heredoc,
    # which the bash-level scan above cannot see at all.
    for _tag, heredoc in HEREDOC_RE.findall(body):
        for m in PY_WRITE_RE.finditer(heredoc):
            base = Path(m.group(1) or m.group(2)).name
            if base not in writes:
                writes.append(base)
    return writes, [r for r in reads if r not in writes]


@functools.lru_cache(maxsize=None)
def _cognitive_os_index() -> dict[str, str]:
    """basename -> first matching path under .cognitive-os, walked ONCE.

    The previous form ran `REPO.glob(".cognitive-os/**/{base}")` per lookup.
    A miss walks the whole tree, and most lookups miss: 68 of 122 in the
    2026-08-18 measurement, over 10,342 files, for 12.0s of the 29.3s run.
    One walk answers every lookup. `sorted` keeps the pick deterministic
    where two directories hold the same basename — `glob` did not.
    """
    index: dict[str, str] = {}
    root = REPO / ".cognitive-os"
    if not root.is_dir():
        return index
    for dirpath, _dirs, files in os.walk(root):
        for fn in files:
            full = os.path.join(dirpath, fn)
            prev = index.get(fn)
            index[fn] = full if prev is None else min(prev, full)
    return index


@functools.lru_cache(maxsize=None)
def artifact_stat(base: str) -> dict:
    p = METRICS / base
    if not p.is_file():
        hit = _cognitive_os_index().get(base)
        if hit:
            p = Path(hit)
    if not p.is_file():
        return {"file": base, "exists": False, "rows": 0, "mtime": None}
    rows = 0
    try:
        with p.open(errors="ignore") as fh:
            for _ in fh:
                rows += 1
    except OSError:
        pass
    import datetime
    return {
        "file": os.path.relpath(p, REPO),
        "exists": True,
        "rows": rows,
        "mtime": datetime.datetime.utcfromtimestamp(
            p.stat().st_mtime).strftime("%Y-%m-%d"),
    }


@functools.lru_cache(maxsize=None)
def _referencing_files(base: str) -> tuple[str, ...]:
    """`git grep` hits for one artifact basename. Depends ONLY on the basename.

    Distinct from `consumers` on purpose: the producer filter is per hook, the
    grep is not. Hooks share artifacts, so the uncached form re-ran identical
    greps — 54 spawns for 38 distinct basenames, at ~0.25s each.
    """
    out = sh(f"git grep -l -F -- {base!r} -- ':!.cognitive-os' | head -40")
    return tuple(h for h in out.splitlines() if h.strip())


def consumers(base: str, producer_real: str) -> list[str]:
    """Files that reference the artifact but are not the producing hook itself."""
    return [h for h in _referencing_files(base) if os.path.relpath(
        os.path.realpath(REPO / h), REPO) != producer_real]


def verdict(runs: int, arts: list[dict], cons: list[str],
            reads: list[dict]) -> str:
    if reads and not arts:
        # Pure consumer: it drains something. Is anyone filling it?
        if all(r["rows"] == 0 for r in reads):
            return "no-producer" if runs else "idle"
        return "productive" if runs else "idle"
    if runs == 0:
        return "idle"
    existing = [a for a in arts if a["exists"] and a["rows"] > 0]
    if not existing:
        return "no-artifact"
    total_rows = sum(a["rows"] for a in existing)
    if not cons:
        return "no-consumer"
    if runs >= STARVED_MIN_RUNS and total_rows * STARVED_RATIO < runs:
        return "starved"
    return "productive"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--class", dest="klass", default="instrument",
                    choices=["instrument", "gate", "inert", "all"])
    args = ap.parse_args()

    try:
        pop = census()
        runs = run_counts()
    except Exception as exc:  # noqa: BLE001 - top-level guard, exit 2 contract
        print(f"error: {exc}", file=sys.stderr)
        return 2

    rows = []
    for real, row in sorted(pop.items(), key=lambda kv: kv[1]["name"]):
        if args.klass != "all" and row["class"] != args.klass:
            continue
        n = runs.get(row["name"], 0)
        w, r = artifacts_for(row["body"])
        arts = [artifact_stat(b) for b in w]
        reads = [artifact_stat(b) for b in r]
        cons: list[str] = []
        for a in arts:
            if a["exists"]:
                cons += consumers(Path(a["file"]).name, row["real"])
        cons = sorted(set(cons))
        rows.append({
            "name": row["name"], "class": row["class"], "runs": n,
            "name_token": row["name_token"],
            "artifacts": arts, "reads": reads, "consumers": cons[:6],
            "consumer_count": len(cons),
            "verdict": verdict(n, arts, cons, reads),
        })

    if args.json:
        print(json.dumps({"rows": rows}, indent=2))
    else:
        print(f"{'hook':<44} {'runs':>7} {'rows':>7}  verdict")
        for r in sorted(rows, key=lambda r: -r["runs"]):
            ar = sum(a["rows"] for a in r["artifacts"] if a["exists"])
            print(f"{r['name']:<44} {r['runs']:>7} {ar:>7}  {r['verdict']}")
        bad = [r for r in rows if r["verdict"] not in ("productive", "idle")]
        wasted = sum(r["runs"] for r in bad)
        print(f"\nclass={args.klass}  total={len(rows)}  unproductive={len(bad)}"
              f"  wasted_invocations={wasted}")

    return 1 if any(r["verdict"] not in ("productive", "idle") for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
