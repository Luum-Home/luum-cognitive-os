#!/usr/bin/env python3
# SCOPE: os-only
"""Gate: no hook may be declared in cognitive-os.yaml and silently never run.

Read-only. Deterministic. Exit 0 = no orphans, 1 = orphans, 2 = error.

    .venv/bin/python scripts/audit_hook_registration.py
    .venv/bin/python scripts/audit_hook_registration.py --json

An ORPHAN is a hook declared in `cognitive-os.yaml > harness.hooks` that is
absent from EVERY Claude Code reachability surface, has NO declared reason for
that absence, and shows NO firing evidence in hook-timing (live file plus its
rotated archives -- the live file holds hours, not history).

CONTRADICTED OMISSIONS are reported on every run but do not set the exit code:
a hook whose yaml entry says "not projected to Claude" while a Claude surface
wires it anyway is two declarations disagreeing, not a hook nobody registered.
Folding it into the same exit code would mean fixing an orphan could not turn
the gate green, and a gate that cannot go green gets switched off.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cos_lib.hook_registration_audit import (  # noqa: E402
    CLAUDE_REACHABILITY_SURFACES,
    HookRegistrationAudit,
)


def _serialize(verdict) -> dict:
    return {
        "name": verdict.name,
        "script": verdict.script,
        "entries": verdict.entries,
        "surfaces_present": sorted(k for k, v in verdict.surfaces.items() if v),
        "omissions": verdict.omissions,
        "firings": verdict.firings,
        "inherited_from": verdict.inherited_from,
        "status": verdict.status,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    # El default es EL REPO DE ESTE ARCHIVO, no el cwd. Un auditor anclado en
    # cwd no falla: audita el arbol equivocado y sale verde por vacio, que es la
    # peor forma de pasar — parece que no hay problemas. Lo cazo el proof
    # pareado (tests/red_team/portability/test_audit_hook_registration.py) en su
    # primera corrida, comparando el veredicto desde el repo contra el mismo
    # desde un directorio ajeno.
    parser.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parent.parent),
        help="project root (default: the repo this script lives in, not the cwd)",
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()

    try:
        report = HookRegistrationAudit(args.root).audit()
    except Exception as exc:  # noqa: BLE001 - exit 2 is the error contract
        print(f"audit_hook_registration: ERROR: {exc}", file=sys.stderr)
        return 2

    orphans = report["orphans"]
    contradicted = report["contradicted_omission"]

    if args.json:
        print(
            json.dumps(
                {
                    "declared_scripts": report["declared_scripts"],
                    "declared_entries": report["declared_entries"],
                    "surface_totals": report["surface_totals"],
                    "harness_coverage": report["harness_coverage"],
                    "counts": {
                        "registered": len(report["registered"]),
                        "omission_declared": len(report["omission_declared"]),
                        "contradicted_omission": len(contradicted),
                        "unreachable_but_observed": len(report["unreachable_but_observed"]),
                        "orphans": len(orphans),
                    },
                    "orphans": [_serialize(v) for v in orphans],
                    "contradicted_omission": [_serialize(v) for v in contradicted],
                    "unreachable_but_observed": [
                        _serialize(v) for v in report["unreachable_but_observed"]
                    ],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1 if orphans else 0

    print("=== HOOK REGISTRATION AUDIT (Claude Code lane) ===")
    print(
        f"declared: {report['declared_scripts']} scripts "
        f"in {report['declared_entries']} yaml entries"
    )
    print("Claude reachability surfaces: " + ", ".join(CLAUDE_REACHABILITY_SURFACES))
    for label, total in sorted(report["surface_totals"].items()):
        print(f"  {label:22} {total:4} hook names")
    print("other-harness coverage (informational, never gates):")
    for label, covered in sorted(report["harness_coverage"].items()):
        print(f"  {label:22} {covered:4}/{report['declared_scripts']}")
    print(
        f"registered={len(report['registered'])} "
        f"omission-declared={len(report['omission_declared'])} "
        f"contradicted={len(contradicted)} "
        f"observed-only={len(report['unreachable_but_observed'])} "
        f"ORPHANS={len(orphans)}"
    )

    if contradicted:
        print("\nWARN - yaml declares a Claude opt-out, a Claude surface wires it anyway:")
        for verdict in contradicted:
            wired = [s for s in CLAUDE_REACHABILITY_SURFACES if verdict.surfaces.get(s)]
            print(f"  ! {verdict.script}")
            print(f"      opt-out: {'; '.join(verdict.omissions)}")
            print(f"      wired on: {', '.join(wired)}")

    if report["unreachable_but_observed"]:
        print("\nNOTE - no reachability surface found, but telemetry shows runs:")
        for verdict in report["unreachable_but_observed"]:
            print(f"  ? {verdict.script} ({verdict.firings} rows)")

    if not orphans:
        print("\nOK: no declared hook is silently unregistered.")
        return 0

    print("\nFAIL - declared, unreachable, undeclared absence, never observed:")
    for verdict in orphans:
        print(f"  X {verdict.script}  (yaml entries: {', '.join(verdict.entries)})")
        print(f"      absent from: {', '.join(CLAUDE_REACHABILITY_SURFACES)}")
        print(f"      firings in hook-timing (live + rotated): {verdict.firings}")
        print(
            "      fix: add it to scripts/_lib/settings-driver-claude-code.sh "
            "and re-run scripts/apply-efficiency-profile.sh, OR declare the "
            "omission (default_projection/claude_projection in cognitive-os.yaml, "
            "or tests/contracts/EXCLUDED_HOOKS.txt with a reason)."
        )
    return 1


if __name__ == "__main__":
    sys.exit(main())
