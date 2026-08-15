#!/usr/bin/env python3
"""Audit the INVERSE direction of ADR coverage.

Every other ADR audit in this repo asks "does this ADR describe something
real?".  This one asks the opposite, and nothing else does:

    Does every implemented decision have a WRITTEN decision behind it?

A decision without an ADR is a decision nobody can review, revert, or
understand: the code says *what*, and nobody is left who knows *why*.

--------------------------------------------------------------------------
THE CRITERION (written before it was applied; applicable by someone else)
--------------------------------------------------------------------------
Not every file needs an ADR.  Demanding one per script produces hundreds of
findings and zero action.  A file is a DECISION SURFACE -- i.e. it needs a
written decision behind it -- when someone could plausibly want to revert or
challenge it.  Concretely, exactly one of:

  D1  BLOCKING GATE     a hook that can deny an operator action.
                        Source of truth: scripts/audit_gate_registration.py
                        (`can_block: true`).  It changes what the operator is
                        allowed to do, which is the definition of a decision.

  D2  CODIFIED POLICY   a manifest under manifests/ whose content encodes a
                        policy rather than an inventory -- freeze, allowlist,
                        denylist, scope, budget, quota, ratchet, baseline,
                        threshold, required/forbidden.  Detected by top-level
                        key names, not by filename.

  D3  PACKAGE BOUNDARY  packages/*/cos-package.yaml -- a package is a claim
                        about what ships together and what a consumer gets.

Explicitly NOT decision surfaces (and therefore not audited here): read-only
evidence scripts, tests, reports, internal helpers, docs, and inventories
with no policy verbs.  If you widen the population, widen it here, in code,
with a reason -- not in prose.

--------------------------------------------------------------------------
WHAT COUNTS AS BACKING (checked in BOTH directions -- this matters)
--------------------------------------------------------------------------
  self_cited   the surface's own body cites ADR-NNN and that ADR file exists.
  adr_cites    some ADR file names the surface (hook name / manifest / pkg).
  dangling     the surface cites ADR-NNN and NO such ADR file exists.  This
               is worse than no citation: it reads as backed and is not.

BACKED   = self_cited or adr_cites.
UNBACKED = neither.  This is the census of the hole.

Deliberately NOT done here: writing retroactive ADRs to close the gap.  An
ADR written afterwards, by someone who did not make the decision, inventing
the *why*, looks like a record and is fiction.  The correct output for an
unbacked surface whose motive cannot be reconstructed from git history is
"implemented without a written decision, motive lost" -- not a new ADR.

--------------------------------------------------------------------------
Read-only.  Deterministic.  Exit 0 = within ratchet, 1 = regression, 2 = error.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ADR_DIR = REPO / "docs" / "02-Decisions" / "adrs"
RATCHET = REPO / "manifests" / "decision-backing-ratchet.yaml"

ADR_RE = re.compile(r"ADR-(\d{1,4})")

# D2: top-level manifest keys that mean "this encodes a policy", not "this
# lists things".  Substring match against top-level YAML keys.
POLICY_KEY_MARKERS = (
    "freeze",
    "frozen",
    "allowlist",
    "allowed",
    "denylist",
    "blocked",
    "forbidden",
    "budget",
    "quota",
    "limit",
    "max_",
    "min_",
    "threshold",
    "ratchet",
    "baseline",
    "required",
    "scope",
    "policy",
    "enforce",
)


def die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(2)


def existing_adr_numbers() -> set[int]:
    if not ADR_DIR.is_dir():
        die(f"ADR directory not found: {ADR_DIR.relative_to(REPO)}")
    nums = set()
    for p in ADR_DIR.glob("ADR-*.md"):
        m = re.match(r"ADR-(\d+)", p.name)
        if m:
            nums.add(int(m.group(1)))
    if not nums:
        die("no ADR files found")
    return nums


def adr_corpus() -> str:
    """One blob of every ADR body, lowercased, for backward-reference lookup."""
    parts = []
    for p in sorted(ADR_DIR.glob("ADR-*.md")):
        try:
            parts.append(p.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
    return "\n".join(parts).lower()


def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def blocking_gates() -> list[dict]:
    """D1 population, from the repo's own gate census (no second opinion)."""
    script = REPO / "scripts" / "audit_gate_registration.py"
    if not script.is_file():
        die("scripts/audit_gate_registration.py not found (D1 census source)")
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "--json"],
            capture_output=True,
            text=True,
            cwd=str(REPO),
            timeout=300,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        die(f"gate census failed: {exc}")
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        die("gate census did not emit JSON")
    return [r for r in data.get("rows", []) if r.get("can_block")]


def top_level_yaml_keys(text: str) -> list[str]:
    """Cheap top-level key scan.  Avoids a yaml dependency and is enough to
    tell a policy manifest from an inventory."""
    keys = []
    for line in text.splitlines():
        if not line or line[0] in " \t#-":
            continue
        if ":" in line:
            keys.append(line.split(":", 1)[0].strip().lower())
    return keys


def policy_manifests() -> list[Path]:
    """D2 population."""
    out = []
    mdir = REPO / "manifests"
    if not mdir.is_dir():
        return out
    for p in sorted(mdir.glob("*.yaml")) + sorted(mdir.glob("*.yml")):
        keys = top_level_yaml_keys(read(p))
        if any(marker in k for k in keys for marker in POLICY_KEY_MARKERS):
            out.append(p)
    return out


def package_manifests() -> list[Path]:
    """D3 population."""
    return sorted((REPO / "packages").glob("*/cos-package.yaml"))


def identifiers_for(kind: str, name: str, path: str) -> list[str]:
    """Strings an ADR would plausibly use to name this surface."""
    ids = {name.lower()}
    base = os.path.basename(path)
    ids.add(base.lower())
    ids.add(base.rsplit(".", 1)[0].lower())
    if kind == "package":
        # packages/foo/cos-package.yaml -> "foo"
        parts = path.split("/")
        if len(parts) >= 2:
            ids.add(parts[-2].lower())
        ids.discard("cos-package")
        ids.discard("cos-package.yaml")
    return sorted(i for i in ids if len(i) >= 6)


def classify(kind: str, name: str, rel: str, adr_nums: set[int], corpus: str) -> dict:
    body = read(REPO / rel)
    cited = sorted({int(n) for n in ADR_RE.findall(body)})
    resolved = [n for n in cited if n in adr_nums]
    dangling = [n for n in cited if n not in adr_nums]

    ids = identifiers_for(kind, name, rel)
    back = sorted(i for i in ids if i in corpus)

    if resolved:
        verdict = "backed:self-cited"
    elif back:
        verdict = "backed:adr-names-it"
    else:
        verdict = "UNBACKED"

    return {
        "kind": kind,
        "name": name,
        "path": rel,
        "cites_adr": [f"ADR-{n:03d}" for n in resolved],
        "dangling_adr": [f"ADR-{n:03d}" for n in dangling],
        "named_by_adr_via": back,
        "verdict": verdict,
    }


def collect(adr_nums: set[int], corpus: str) -> list[dict]:
    rows = []
    for g in blocking_gates():
        rows.append(
            classify("blocking-gate", g["name"], g["real"], adr_nums, corpus)
        )
    for p in policy_manifests():
        rel = str(p.relative_to(REPO))
        rows.append(classify("policy-manifest", p.stem, rel, adr_nums, corpus))
    for p in package_manifests():
        rel = str(p.relative_to(REPO))
        rows.append(classify("package", p.parent.name, rel, adr_nums, corpus))
    rows.sort(key=lambda r: (r["kind"], r["name"]))
    return rows


def load_ratchet() -> dict:
    """Minimal flat-int parser -- no yaml dependency, and the file is flat by
    design so a reader can see the numbers without a parser."""
    limits = {"blocking-gate": 0, "policy-manifest": 0, "package": 0, "dangling": 0}
    if not RATCHET.is_file():
        return limits
    section = None
    for line in read(RATCHET).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not line[0].isspace() and stripped.endswith(":"):
            section = stripped[:-1]
            continue
        if section == "max_unbacked" and ":" in stripped:
            k, v = stripped.split(":", 1)
            try:
                limits[k.strip()] = int(v.split("#")[0].strip())
            except ValueError:
                pass
    return limits


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument(
        "--kind",
        choices=["blocking-gate", "policy-manifest", "package"],
        help="restrict to one decision-surface class",
    )
    ap.add_argument(
        "--unbacked-only", action="store_true", help="print only the hole"
    )
    args = ap.parse_args()

    adr_nums = existing_adr_numbers()
    rows = collect(adr_nums, adr_corpus())
    if args.kind:
        rows = [r for r in rows if r["kind"] == args.kind]

    unbacked = [r for r in rows if r["verdict"] == "UNBACKED"]
    dangling = [r for r in rows if r["dangling_adr"]]
    limits = load_ratchet()

    counts = {}
    for kind in sorted({r["kind"] for r in rows}):
        pop = [r for r in rows if r["kind"] == kind]
        ub = [r for r in pop if r["verdict"] == "UNBACKED"]
        counts[kind] = {
            "population": len(pop),
            "unbacked": len(ub),
            "limit": limits.get(kind),
        }

    regressions = [
        f"{k}: {v['unbacked']} unbacked > ratchet {v['limit']}"
        for k, v in counts.items()
        if v["limit"] is not None and v["unbacked"] > v["limit"]
    ]
    if limits.get("dangling") is not None and len(dangling) > limits["dangling"]:
        regressions.append(
            f"dangling: {len(dangling)} > ratchet {limits['dangling']}"
        )

    if args.json:
        print(
            json.dumps(
                {
                    "adr_files": len(list(ADR_DIR.glob("ADR-*.md"))),
                    "adr_numbers": len(adr_nums),
                    "counts": counts,
                    "dangling_total": len(dangling),
                    "regressions": regressions,
                    "rows": unbacked if args.unbacked_only else rows,
                },
                indent=2,
            )
        )
    else:
        print(f"ADR corpus: {len(list(ADR_DIR.glob('ADR-*.md')))} files, "
              f"{len(adr_nums)} distinct numbers")
        for kind, v in counts.items():
            lim = "n/a" if v["limit"] is None else v["limit"]
            print(f"  {kind:16s} population={v['population']:3d} "
                  f"unbacked={v['unbacked']:3d} ratchet={lim}")
        if dangling:
            print(f"\nDANGLING ADR CITATIONS ({len(dangling)}) "
                  f"-- reads as backed, is not:")
            for r in dangling:
                print(f"  {r['name']}: cites {', '.join(r['dangling_adr'])} "
                      f"(no such ADR file)")
        show = unbacked if not args.unbacked_only else unbacked
        if show:
            print(f"\nUNBACKED ({len(show)}) -- implemented, no written decision:")
            for r in show:
                print(f"  [{r['kind']}] {r['name']}  ({r['path']})")
        for msg in regressions:
            print(f"RATCHET REGRESSION: {msg}", file=sys.stderr)

    return 1 if regressions else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
