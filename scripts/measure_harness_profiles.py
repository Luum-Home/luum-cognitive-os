#!/usr/bin/env python3
# SCOPE: os-only
"""Measure Cognitive OS minimal vs full harness surfaces.

This is a static, no-mutation measurement: it compares the committed minimal
profile contract in manifests/harness-profiles.yaml with the active projected
hook surfaces in .claude/settings.json and .codex/hooks.json.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _load_minimal_profile(root: Path) -> dict[str, Any]:
    path = root / "manifests" / "harness-profiles.yaml"
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore
        data = yaml.safe_load(text) or {}
        minimal = (data.get("profiles") or {}).get("minimal") or {}
        return {
            "required_hooks": list(minimal.get("required_hooks") or []),
            "required_files": list(minimal.get("required_files") or []),
            "context_budget_tokens": minimal.get("context_budget_tokens"),
            "startup_budget_ms": minimal.get("startup_budget_ms"),
        }
    except Exception:
        in_minimal = False
        current_key = None
        out: dict[str, Any] = {"required_hooks": [], "required_files": [], "context_budget_tokens": None, "startup_budget_ms": None}
        for raw in text.splitlines():
            if raw.startswith("  minimal:"):
                in_minimal = True
                continue
            if in_minimal and raw.startswith("  full:"):
                break
            if not in_minimal:
                continue
            stripped = raw.strip()
            if stripped.startswith("context_budget_tokens:"):
                out["context_budget_tokens"] = int(stripped.split(":", 1)[1].strip())
            elif stripped.startswith("startup_budget_ms:"):
                out["startup_budget_ms"] = int(stripped.split(":", 1)[1].strip())
            elif stripped.startswith("required_hooks:"):
                current_key = "required_hooks"
            elif stripped.startswith("required_files:"):
                current_key = "required_files"
            elif stripped and not stripped.startswith("-") and stripped.endswith(":"):
                current_key = None
            elif current_key and stripped.startswith("- "):
                out[current_key].append(stripped[2:].strip().strip("\"'"))
        return out


def _count_claude_hooks(root: Path) -> dict[str, Any]:
    path = root / ".claude" / "settings.json"
    if not path.exists():
        return {"available": False, "hook_commands": 0, "events": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    hooks = data.get("hooks", {})
    events: dict[str, int] = {}
    total = 0
    for event, entries in hooks.items():
        count = 0
        for entry in entries:
            count += len(entry.get("hooks", [])) if isinstance(entry, dict) else 1
        events[event] = count
        total += count
    return {"available": True, "hook_commands": total, "events": events}


def _count_codex_hooks(root: Path) -> dict[str, Any]:
    path = root / ".codex" / "hooks.json"
    if not path.exists():
        return {"available": False, "hook_commands": 0, "events": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    events: dict[str, int] = {}
    total = 0
    for event, entries in data.items():
        count = 0
        for entry in entries:
            count += len(entry.get("hooks", [])) if isinstance(entry, dict) else 1
        events[event] = count
        total += count
    return {"available": True, "hook_commands": total, "events": events}


def measure(root: Path) -> dict[str, Any]:
    minimal = _load_minimal_profile(root)
    full = {"claude_code": _count_claude_hooks(root), "codex": _count_codex_hooks(root)}
    minimal_hook_count = len(minimal["required_hooks"])
    full_counts = [v["hook_commands"] for v in full.values() if v.get("available")]
    max_full = max(full_counts) if full_counts else 0
    ratio = round(max_full / minimal_hook_count, 2) if minimal_hook_count else None
    return {
        "minimal": {**minimal, "hook_count": minimal_hook_count},
        "full": full,
        "comparison": {
            "max_full_hook_count": max_full,
            "minimal_to_full_hook_ratio": ratio,
            "interpretation": "Higher ratios mean the full projection is much larger than the minimal harness contract; use only when optional governance value justifies the surface.",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure minimal vs full Cognitive OS harness profiles")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    parser.add_argument("--root", default=str(ROOT), help="Project root")
    args = parser.parse_args()
    payload = measure(Path(args.root).resolve())
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print("=== Harness Profile Measurement ===")
        print(f"minimal hooks: {payload['minimal']['hook_count']}")
        print(f"minimal context budget: {payload['minimal']['context_budget_tokens']} tokens")
        for name, data in payload["full"].items():
            if data["available"]:
                print(f"{name} full hooks: {data['hook_commands']} ({', '.join(f'{k}={v}' for k,v in sorted(data['events'].items()))})")
            else:
                print(f"{name} full hooks: unavailable")
        print(f"max full/minimal hook ratio: {payload['comparison']['minimal_to_full_hook_ratio']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
