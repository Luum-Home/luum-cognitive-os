#!/usr/bin/env python3
# SCOPE: os-only
"""Select proof-drill and smoke opt-in commands from the governed registry."""
from __future__ import annotations
import os as _cos_os
import sys as _cos_sys
_cos_sys.path.insert(0, _cos_os.path.dirname(_cos_os.path.dirname(__file__)))
from lib.script_helpers import read_yaml_required as load_registry

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY = REPO_ROOT / "manifests" / "proof-drill-registry.yaml"
OPT_IN_CLASSES = {"smoke-opt-in", "proof-drill", "manual-proof"}


def _contains(entry: dict[str, Any], token: str) -> bool:
    token = token.lower()
    haystack = " ".join(
        str(part)
        for part in [
            entry.get("id", ""),
            entry.get("class", ""),
            entry.get("scope", ""),
            entry.get("selector", ""),
            entry.get("command", ""),
            entry.get("cost_class", ""),
            entry.get("when_to_run", ""),
            " ".join(entry.get("selectors", []) or []),
        ]
    ).lower()
    return token in haystack


def select_entries(
    registry: dict[str, Any],
    *,
    entry_id: str | None = None,
    scope: str | None = None,
    drill_class: str | None = None,
    profile: str | None = None,
    tokens: list[str] | None = None,
) -> list[dict[str, Any]]:
    entries = list(registry.get("entries", []))
    if entry_id:
        entries = [entry for entry in entries if entry.get("id") == entry_id]
    if scope:
        entries = [entry for entry in entries if entry.get("scope") in {scope, "both"}]
    if drill_class:
        entries = [entry for entry in entries if entry.get("class") == drill_class]
    if profile:
        profiles = registry.get("projection_profiles", {})
        if profile not in profiles:
            raise ValueError(f"unknown projection profile: {profile}")
        allowed = set(profiles[profile].get("allows", []))
        entries = [entry for entry in entries if entry.get("consumer_projection") in allowed]
    for token in tokens or []:
        entries = [entry for entry in entries if _contains(entry, token)]
    return sorted(entries, key=lambda entry: (entry.get("class") in OPT_IN_CLASSES, entry.get("id", "")))


def command_row(entry: dict[str, Any]) -> dict[str, Any]:
    opt_in = entry.get("class") in OPT_IN_CLASSES or entry.get("default_lane") is False
    return {
        "id": entry.get("id"),
        "class": entry.get("class"),
        "scope": entry.get("scope"),
        "consumer_projection": entry.get("consumer_projection"),
        "selector": entry.get("selector"),
        "command": entry.get("command"),
        "default_lane": entry.get("default_lane"),
        "opt_in_required": bool(opt_in),
        "cost_class": entry.get("cost_class"),
        "requires_credentials": entry.get("requires_credentials", []),
        "proves": entry.get("proves"),
        "does_not_prove": entry.get("does_not_prove"),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", default=str(REGISTRY), help="Proof drill registry path")
    parser.add_argument("--id", dest="entry_id", help="Exact proof drill id")
    parser.add_argument("--scope", choices=("os-self", "consumer-project", "both"))
    parser.add_argument("--class", dest="drill_class", choices=("standard-test-lane", "smoke-opt-in", "proof-drill", "manual-proof"))
    parser.add_argument("--profile", help="Projection profile from registry, e.g. consumer-default")
    parser.add_argument("--contains", action="append", default=[], help="Filter by text token such as provider, docker, headless, codex")
    parser.add_argument("--commands", action="store_true", help="Print shell commands only")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when no entries match")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    registry = load_registry(Path(args.registry))
    try:
        entries = select_entries(
            registry,
            entry_id=args.entry_id,
            scope=args.scope,
            drill_class=args.drill_class,
            profile=args.profile,
            tokens=args.contains,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    rows = [command_row(entry) for entry in entries]
    payload = {
        "schema_version": "proof-drill-selection.v1",
        "count": len(rows),
        "filters": {
            "id": args.entry_id,
            "scope": args.scope,
            "class": args.drill_class,
            "profile": args.profile,
            "contains": args.contains,
        },
        "entries": rows,
    }
    if args.commands:
        for row in rows:
            print(row["command"])
    elif args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for row in rows:
            marker = "OPT-IN" if row["opt_in_required"] else "default"
            print(f"{row['id']} [{row['class']}/{row['scope']}/{marker}] {row['command']}")
    if args.strict and not rows:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
