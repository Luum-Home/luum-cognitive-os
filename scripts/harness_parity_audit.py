#!/usr/bin/env python3
# SCOPE: both
"""Audit hook projection parity across harness settings drivers.

The goal is not byte-for-byte equality. Claude and Codex expose different hook
surfaces today. This audit answers a sharper question:

- which hooks are projected where the target driver supports the event?
- which gaps are caused by limited or unsupported target capability?
- which hook source still treats one driver file as the implicit source of truth?
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.script_io import read_json as _load_json

try:
    import yaml
except ImportError:  # pragma: no cover - exercised by CLI environments
    yaml = None


HOOK_RE = re.compile(r"([^/\" $]+\.sh)")


@dataclass(frozen=True)
class HookRegistration:
    event: str
    matcher: str
    script: str
    command: str
    async_run: bool


def _load_yaml(path: Path) -> dict[str, Any]:
    if yaml is None:
        raise RuntimeError("PyYAML is required for harness parity audit")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _hook_root(settings: dict[str, Any]) -> dict[str, Any]:
    hooks = settings.get("hooks")
    return hooks if isinstance(hooks, dict) else settings


def extract_registrations(path: Path) -> list[HookRegistration]:
    settings = _load_json(path)
    registrations: list[HookRegistration] = []
    for event, groups in _hook_root(settings).items():
        if not isinstance(groups, list):
            continue
        for group in groups:
            if not isinstance(group, dict):
                continue
            matcher = str(group.get("matcher", ""))
            for hook in group.get("hooks", []):
                if not isinstance(hook, dict):
                    continue
                command = str(hook.get("command", ""))
                matches = HOOK_RE.findall(command)
                # Commands may wrap hooks through scripts/hook-timing-wrapper.sh.
                # The projected hook is the final .sh argument, not the wrapper.
                script = matches[-1] if matches else command
                registrations.append(
                    HookRegistration(
                        event=event,
                        matcher=matcher,
                        script=script,
                        command=command,
                        async_run=bool(hook.get("async")),
                    )
                )
    return registrations


def _driver_capabilities(manifest: dict[str, Any], driver: str) -> dict[str, Any]:
    drivers = manifest.get("drivers", {})
    if driver not in drivers:
        raise ValueError(f"unknown driver in capability manifest: {driver}")
    return drivers[driver]


def _event_status(capabilities: dict[str, Any], event: str) -> str:
    event_cfg = capabilities.get("supported_events", {}).get(event)
    if not isinstance(event_cfg, dict):
        return "unsupported"
    return str(event_cfg.get("status", "unsupported"))


def build_report(root: Path, source: str, target: str) -> dict[str, Any]:
    manifest = _load_yaml(root / "manifests" / "harness-driver-capabilities.yaml")
    source_caps = _driver_capabilities(manifest, source)
    target_caps = _driver_capabilities(manifest, target)
    source_path = root / source_caps["settings_path"]
    target_path = root / target_caps["settings_path"]

    source_regs = extract_registrations(source_path)
    target_regs = extract_registrations(target_path)
    target_keys = {(r.event, r.matcher, r.script) for r in target_regs}
    target_by_event_script = {(r.event, r.script) for r in target_regs}

    projected: list[dict[str, Any]] = []
    missing_supported: list[dict[str, Any]] = []
    missing_limited: list[dict[str, Any]] = []
    unsupported: list[dict[str, Any]] = []

    for reg in source_regs:
        status = _event_status(target_caps, reg.event)
        row = {
            "event": reg.event,
            "matcher": reg.matcher,
            "script": reg.script,
            "target_status": status,
        }
        if (reg.event, reg.matcher, reg.script) in target_keys or (
            reg.event,
            reg.script,
        ) in target_by_event_script:
            projected.append(row)
        elif status == "supported":
            missing_supported.append(row)
        elif status == "limited":
            missing_limited.append(row)
        else:
            unsupported.append(row)

    return {
        "source_driver": source,
        "target_driver": target,
        "source_settings": str(source_path),
        "target_settings": str(target_path),
        "source_hook_count": len(source_regs),
        "target_hook_count": len(target_regs),
        "projected_count": len(projected),
        "missing_supported_count": len(missing_supported),
        "missing_limited_count": len(missing_limited),
        "unsupported_count": len(unsupported),
        "projected": projected,
        "missing_supported": missing_supported,
        "missing_limited": missing_limited,
        "unsupported": unsupported,
    }


def print_text(report: dict[str, Any]) -> None:
    print(f"Harness parity: {report['source_driver']} -> {report['target_driver']}")
    print(f"Source hooks: {report['source_hook_count']}")
    print(f"Target hooks: {report['target_hook_count']}")
    print(f"Projected: {report['projected_count']}")
    print(f"Missing on supported target events: {report['missing_supported_count']}")
    print(f"Missing on limited target events: {report['missing_limited_count']}")
    print(f"Unsupported target event gaps: {report['unsupported_count']}")

    if report["missing_supported"]:
        print("\nFAIL: supported target events missing projections")
        for row in report["missing_supported"]:
            print(f"- {row['event']} {row['matcher']} {row['script']}")
    else:
        print("\nPASS: no missing projections on supported target events")

    if report["missing_limited"]:
        print("\nLIMITED: target driver has partial/evolving support")
        for row in report["missing_limited"]:
            print(f"- {row['event']} {row['matcher']} {row['script']}")

    if report["unsupported"]:
        print("\nUNSUPPORTED: do not copy blindly without a runner/adapter")
        by_event: dict[str, int] = {}
        for row in report["unsupported"]:
            by_event[row["event"]] = by_event.get(row["event"], 0) + 1
        for event, count in sorted(by_event.items()):
            print(f"- {event}: {count} hook(s)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--source", default="claude", help="Reference driver")
    parser.add_argument("--target", default="codex", help="Target driver")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when supported target events are missing projections",
    )
    args = parser.parse_args()

    try:
        report = build_report(Path(args.root).resolve(), args.source, args.target)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_text(report)

    if args.strict and report["missing_supported_count"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
