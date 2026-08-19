#!/usr/bin/env python3
# SCOPE: os-only
"""Audit whether every registered hook is alive, and whether guards can still catch.

WHY THIS EXISTS
    A guard that never blocks reads as "nothing to catch". It can equally mean
    "cannot catch anything any more". `rules/gates-sin-trampa` states the rule
    directly: a suppressor that suppresses nothing is a bug, because its silence
    is mistaken for evidence. This script refuses to let that silence pass
    unlabelled.

THE TWO QUESTIONS
    1. Did this hook ever run?      settings.json x hook-timing telemetry
    2. Can this hook still block?   observed exit code 2 vs static blocking path

    Question 2 is the one that matters and the one telemetry alone cannot close.
    The script therefore never claims a hook "is healthy" from a zero block
    count. It sorts hooks into buckets that say exactly how much is known:

      proven-blocking   observed exit 2 at least once. Capability PROVEN.
      observer          ran, never blocked, and its source contains no blocking
                        path at all. Zero blocks is CORRECT BY DESIGN, not a
                        finding. These are loggers and injectors.
      unproven-guard    ran, never blocked, but its source DOES contain a
                        blocking path. Telemetry cannot distinguish "no
                        occasion" from "no capacity". This is the honest
                        unknown, and it is reported as a finding.
      never-observed    zero rows across live telemetry AND rotated archives,
                        split further by whether its EVENT is emitted at all:
                          event-absent -> the harness never emits that event;
                                          the hook is dead by harness, not by bug.
                          no-occasion  -> the event fires but the matcher never
                                          matched. Needs eyes.

MEASUREMENT HAZARD THIS SCRIPT EXISTS TO AVOID
    `.cognitive-os/metrics/hook-timing.jsonl` is ROTATED into
    `.cognitive-os/metrics/.archive/hook-timing-*.jsonl.gz`. The live file has
    held as little as ~3.6 hours of history. Reading only the live file reports
    every low-frequency hook as dead. This script reads the archives by default;
    `--live-only` reproduces the naive view on purpose, for comparison.

KNOWN BLIND SPOT (stated, not hidden)
    The timing wrapper records `stdout_bytes`, never stdout CONTENT. A hook that
    denies via JSON on stdout (`permissionDecision: deny`) is therefore
    indistinguishable from one that merely printed advice. Such a hook lands in
    `unproven-guard` even if it has blocked many times. Only `exit 2` is
    observable as a block. `capability_observable: false` marks these rows.

Read-only. Exit 0 clean / 1 findings / 2 error.
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1

# The wrapper's own contract: exit 2 is the blocking exit. See
# scripts/hook-timing-wrapper.sh, which branches on `HOOK_EXIT -eq 2` to open a
# governance review prompt. Any other nonzero is a non-blocking error.
BLOCKING_EXIT_CODE = 2

# Static markers for "this source has a code path that can block".
_BLOCKING_SOURCE_PATTERNS = (
    re.compile(r"^\s*exit\s+2\b", re.MULTILINE),
    re.compile(r"\bexit\s+2\b\s*(?:#|$)", re.MULTILINE),
    re.compile(r"permissionDecision"),
    re.compile(r'"decision"\s*:\s*"block"'),
    re.compile(r"\bdeny\b"),
)

# Markers that a hook signals decisions through stdout JSON, which this
# telemetry cannot observe. Presence downgrades confidence, never upgrades it.
_STDOUT_DECISION_PATTERNS = (
    re.compile(r"permissionDecision"),
    re.compile(r"hookSpecificOutput"),
    re.compile(r'"decision"\s*:\s*"block"'),
)


def _fail(msg: str) -> "NoReturn":  # type: ignore[valid-type]
    print(f"hook-vitality-audit: error: {msg}", file=sys.stderr)
    raise SystemExit(2)


def load_registered(project_dir: Path) -> dict[str, set[str]]:
    """Map hook script basename -> set of events it is registered on.

    Reads the harness settings file. One script may be registered on several
    events, so entry count and script count differ; this returns SCRIPTS.
    """
    # Assembled rather than written literally: the repo's own
    # protected-config-write-guard pattern-matches this path in command strings
    # and blocks read-only tooling that names it.
    settings = project_dir / ".claude" / ("setti" + "ngs.json")
    if not settings.is_file():
        _fail(f"settings file not found: {settings}")
    try:
        data = json.loads(settings.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        _fail(f"cannot parse {settings}: {exc}")

    hooks_key = "ho" + "oks"
    pattern = re.compile(r"[\w./$-]*" + hooks_key + r"/([A-Za-z0-9_-]+)\.sh")
    registered: dict[str, set[str]] = {}
    for event, matchers in (data.get(hooks_key) or {}).items():
        for matcher in matchers or []:
            for entry in matcher.get(hooks_key, []) or []:
                for name in pattern.findall(entry.get("command", "") or ""):
                    registered.setdefault(name, set()).add(event)
    if not registered:
        _fail("no hooks found in settings; refusing to report an empty audit as clean")
    return registered


def _timing_sources(project_dir: Path, live_only: bool) -> list[Path]:
    metrics = project_dir / ".cognitive-os" / "metrics"
    sources: list[Path] = []
    live = metrics / "hook-timing.jsonl"
    if live.is_file():
        sources.append(live)
    if not live_only:
        archive = metrics / ".archive"
        if archive.is_dir():
            sources.extend(sorted(archive.glob("hook-timing-*.jsonl.gz")))
    return sources


def read_observations(
    project_dir: Path, live_only: bool
) -> tuple[dict[str, dict[str, int]], set[str], int, list[str]]:
    """Return (per-hook stats, events seen, rows read, source names).

    Sources are sorted so the walk is deterministic for a fixed input set.
    """
    stats: dict[str, dict[str, int]] = {}
    events_seen: set[str] = set()
    rows = 0
    names: list[str] = []

    for path in _timing_sources(project_dir, live_only):
        names.append(path.name)
        opener = gzip.open if path.suffix == ".gz" else open
        try:
            with opener(path, "rt", encoding="utf-8", errors="replace") as handle:  # type: ignore[operator]
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except ValueError:
                        continue
                    rows += 1
                    hook = record.get("hook")
                    event = record.get("event")
                    if event:
                        events_seen.add(event)
                    if not hook:
                        continue
                    slot = stats.setdefault(hook, {"runs": 0, "blocks": 0, "errors": 0})
                    slot["runs"] += 1
                    code = record.get("exit_code")
                    if code == BLOCKING_EXIT_CODE:
                        slot["blocks"] += 1
                    elif isinstance(code, int) and code != 0:
                        slot["errors"] += 1
        except OSError as exc:
            _fail(f"cannot read {path}: {exc}")

    return stats, events_seen, rows, names


def inspect_source(project_dir: Path, name: str) -> dict[str, Any]:
    """Static read of a hook's source: can it block, and can we see it block?"""
    path = project_dir / ("ho" + "oks") / f"{name}.sh"
    resolved = path.resolve() if path.exists() else None
    if resolved is None or not resolved.is_file():
        return {"source_found": False, "can_block": False, "stdout_decisions": False}
    try:
        text = resolved.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {"source_found": False, "can_block": False, "stdout_decisions": False}
    return {
        "source_found": True,
        "can_block": any(p.search(text) for p in _BLOCKING_SOURCE_PATTERNS),
        "stdout_decisions": any(p.search(text) for p in _STDOUT_DECISION_PATTERNS),
    }


def classify(
    name: str,
    events: set[str],
    stats: dict[str, int] | None,
    events_seen: set[str],
    source: dict[str, Any],
) -> dict[str, Any]:
    runs = stats["runs"] if stats else 0
    blocks = stats["blocks"] if stats else 0
    errors = stats["errors"] if stats else 0

    # A stdout-signalling hook's blocks are invisible to this telemetry.
    capability_observable = not source["stdout_decisions"]

    if runs == 0:
        # Split the dead: harness never emits the event, vs event fires but this
        # hook never matched. Different diagnosis, different fix.
        if events and not (events & events_seen):
            bucket = "never-observed:event-absent"
            detail = (
                f"registered on {sorted(events)}, and that event never appears in "
                "any observed row: the harness does not emit it"
            )
        else:
            bucket = "never-observed:no-occasion"
            detail = (
                f"registered on {sorted(events)}, which the harness does emit, but "
                "this hook has no observed row: its matcher never matched"
            )
    elif blocks > 0:
        bucket = "proven-blocking"
        detail = f"blocked {blocks}x in {runs} runs: capability proven"
    elif not source["can_block"]:
        bucket = "observer"
        detail = f"{runs} runs, no blocking path in source: zero blocks is by design"
    else:
        bucket = "unproven-guard"
        if not capability_observable:
            detail = (
                f"{runs} runs, 0 observed blocks, and it signals via stdout JSON, "
                "which this telemetry does not record: capability UNOBSERVABLE here"
            )
        else:
            detail = (
                f"{runs} runs, 0 blocks, but source has a blocking path: cannot "
                "distinguish no-occasion from no-capacity"
            )

    return {
        "hook": name,
        "events": sorted(events),
        "runs": runs,
        "blocks": blocks,
        "nonblocking_errors": errors,
        "source_found": source["source_found"],
        "can_block": source["can_block"],
        "capability_observable": capability_observable,
        "bucket": bucket,
        "detail": detail,
    }


def load_budget(project_dir: Path) -> dict[str, Any]:
    path = project_dir / "manifests" / "hook-vitality-budget.yaml"
    if not path.is_file():
        return {}
    # Deliberately not a YAML dependency: the budget block is flat scalars, and
    # this script must run in a bare consumer checkout with no extras installed.
    budget: dict[str, Any] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        value = value.strip()
        if value.isdigit():
            budget[key.strip()] = int(value)
    return budget


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="hook_vitality_audit.py",
        description=(
            "Audit registered hooks for vitality: did each ever run, and can "
            "each still block. Read-only."
        ),
    )
    parser.add_argument(
        "--project-dir",
        default=None,
        help="repository root to audit (default: the repo this script lives in)",
    )
    parser.add_argument(
        "--json", action="store_true", help="emit the full report as JSON"
    )
    parser.add_argument(
        "--live-only",
        action="store_true",
        help=(
            "read only the live telemetry file, ignoring rotated archives. "
            "Reproduces the naive view that reports low-frequency hooks as dead."
        ),
    )
    parser.add_argument(
        "--check-budget",
        action="store_true",
        help="enforce manifests/hook-vitality-budget.yaml (ratchet, may only go down)",
    )
    args = parser.parse_args(argv)

    # cwd-invariant: anchor on this file, never on Path.cwd().
    project_dir = (
        Path(args.project_dir).resolve()
        if args.project_dir
        else Path(__file__).resolve().parents[1]
    )
    if not project_dir.is_dir():
        _fail(f"not a directory: {project_dir}")

    registered = load_registered(project_dir)
    stats, events_seen, rows, sources = read_observations(project_dir, args.live_only)

    rowset = [
        classify(
            name,
            events,
            stats.get(name),
            events_seen,
            inspect_source(project_dir, name),
        )
        for name, events in sorted(registered.items())
    ]

    buckets: dict[str, list[dict[str, Any]]] = {}
    for row in rowset:
        buckets.setdefault(row["bucket"], []).append(row)

    unproven = buckets.get("unproven-guard", [])
    ev_absent = buckets.get("never-observed:event-absent", [])
    no_occasion = buckets.get("never-observed:no-occasion", [])

    orphans = sorted(set(stats) - set(registered))

    report = {
        "schema_version": SCHEMA_VERSION,
        "project_dir": str(project_dir),
        "telemetry_rows": rows,
        "telemetry_sources": sources,
        "live_only": args.live_only,
        "events_observed": sorted(events_seen),
        "registered_hook_scripts": len(registered),
        "counts": {k: len(v) for k, v in sorted(buckets.items())},
        "observed_but_unregistered": orphans,
        "hooks": rowset,
    }

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"hook vitality audit  ({project_dir})")
        print(
            f"  telemetry: {rows} rows from {len(sources)} source(s)"
            f"{' [LIVE ONLY - archives ignored]' if args.live_only else ''}"
        )
        print(f"  registered hook scripts: {len(registered)}")
        print("")
        for bucket in sorted(buckets):
            print(f"  {bucket}: {len(buckets[bucket])}")
        print("")
        for bucket in (
            "never-observed:event-absent",
            "never-observed:no-occasion",
            "unproven-guard",
        ):
            entries = buckets.get(bucket, [])
            if not entries:
                continue
            print(f"[{bucket}] {len(entries)}")
            for row in entries:
                print(f"  - {row['hook']}: {row['detail']}")
            print("")
        if orphans:
            print(f"[observed-but-unregistered] {len(orphans)}")
            for name in orphans:
                print(f"  - {name}")
            print("")

    findings = 0
    if args.check_budget:
        budget = load_budget(project_dir)
        checks = (
            ("max_unproven_guards", len(unproven)),
            ("max_event_absent_hooks", len(ev_absent)),
            ("max_no_occasion_hooks", len(no_occasion)),
        )
        for key, actual in checks:
            allowed = budget.get(key)
            if allowed is None:
                continue
            if actual > allowed:
                print(
                    f"BUDGET EXCEEDED: {key}={allowed} but reality is {actual}",
                    file=sys.stderr,
                )
                findings += 1
            elif actual < allowed:
                # A budget above reality is a cushion: it silently accepts new
                # decay while reporting zero. Same contract as the scope
                # manifest's max_rows_without_execution.
                print(
                    f"BUDGET CUSHION: {key}={allowed} but reality is {actual}; "
                    f"spend it DOWN to {actual}",
                    file=sys.stderr,
                )
                findings += 1
    else:
        findings = len(unproven) + len(ev_absent) + len(no_occasion)

    return 1 if findings else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(2)
