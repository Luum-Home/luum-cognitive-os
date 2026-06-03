#!/usr/bin/env python3
# SCOPE: os-only
"""Gate derived Cognitive OS artifacts before commit or merge.

The gate keeps the canonical hook registry in cognitive-os.yaml synchronized
with generated artifacts and harness projections. It is intentionally fast and
structural: no pytest is launched from this script.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.script_io import read_json as normalized_json_file

import yaml

ROOT = Path(__file__).resolve().parents[1]
DERIVED_BY_CONFIG = {
    "cognitive-os.yaml": [
        "manifests/hook-quality.yaml",
        ".claude/settings.json",
        ".codex/hooks.json",
        "opencode.json",
        ".opencode/cos-hooks.json",
    ],
    "scripts/_lib/settings-driver-claude-code.sh": [".claude/settings.json"],
    "scripts/_lib/settings-driver-codex.sh": [".codex/hooks.json"],
    "scripts/_lib/settings-driver-opencode.sh": ["opencode.json", ".opencode/cos-hooks.json"],
    "scripts/hook_quality_audit.py": ["manifests/hook-quality.yaml"],
}


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False, timeout=30)


def changed_staged() -> set[str]:
    proc = run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"])
    if proc.returncode != 0:
        return set()
    return {line.strip() for line in proc.stdout.splitlines() if line.strip()}


def fail(message: str, failures: list[str]) -> None:
    failures.append(message)


def check_hook_quality(failures: list[str]) -> None:
    proc = run([sys.executable, "scripts/hook_quality_audit.py", "--check"])
    if proc.returncode != 0:
        fail((proc.stderr + proc.stdout).strip(), failures)


def check_driver(driver: str, target: str, failures: list[str]) -> None:
    proc = run(["bash", f"scripts/_lib/{driver}", "--check"])
    if proc.returncode != 0:
        fail((proc.stderr + proc.stdout).strip(), failures)


def _registrations_from_json(path: Path) -> list[tuple[str, str, str]]:
    import re

    settings = normalized_json_file(path)
    root = settings.get("hooks") if isinstance(settings.get("hooks"), dict) else settings
    regs: list[tuple[str, str, str]] = []
    for event, groups in root.items():
        if not isinstance(groups, list):
            continue
        for group in groups:
            matcher = str(group.get("matcher", "")) if isinstance(group, dict) else ""
            for hook in group.get("hooks", []) if isinstance(group, dict) else []:
                cmd = str(hook.get("command", ""))
                matches = re.findall(r"([^/\" $]+\.sh)", cmd)
                if matches:
                    regs.append((str(event), matcher, matches[-1]))
    return regs


def check_claude_registry_parity(failures: list[str]) -> None:
    cfg = yaml.safe_load((ROOT / "cognitive-os.yaml").read_text(encoding="utf-8")) or {}
    hooks = (cfg.get("harness") or {}).get("hooks") or {}
    lifecycle = yaml.safe_load((ROOT / "manifests" / "primitive-lifecycle.yaml").read_text(encoding="utf-8")) or {}
    inactive_scripts = {
        Path(str(item.get("id"))).name
        for item in lifecycle.get("primitives", [])
        if isinstance(item, dict) and item.get("lifecycle_state") in {"demoted", "archived", "deleted"}
    }
    expected = set()
    for entry in hooks.values():
        if isinstance(entry, dict) and entry.get("event") and entry.get("script"):
            script_name = Path(str(entry["script"])).name
            if script_name in inactive_scripts:
                continue
            if entry.get("default_projection") is False or entry.get("claude_projection") is False:
                continue
            expected.add((str(entry["event"]), str(entry.get("matcher") or ""), Path(str(entry["script"])).name))
    actual = set(_registrations_from_json(ROOT / ".claude" / "settings.json"))
    missing_set = expected - actual

    # ADR-311/interactive maintainer profile: the default Claude Bash hot path
    # can be represented by a tiered dispatcher instead of projecting every
    # command-scoped Bash gate synchronously. The settings driver check above is
    # the byte-for-byte authority for the active profile; this parity check must
    # not re-expand the dispatcher back into the exhaustive full profile.
    if ("PreToolUse", "Bash", "bash-hot-path-dispatcher.sh") in actual:
        missing_set = {item for item in missing_set if item[0:2] != ("PreToolUse", "Bash")}

    missing = sorted(missing_set)
    extra = sorted(actual - expected)
    if missing or extra:
        details = []
        if missing:
            details.append("missing from .claude/settings.json: " + ", ".join(f"{e}:{m}:{s}" for e, m, s in missing[:20]))
        if extra:
            details.append("extra in .claude/settings.json: " + ", ".join(f"{e}:{m}:{s}" for e, m, s in extra[:20]))
        fail("Claude projection differs from cognitive-os.yaml registry; run settings driver and sync registry. " + " | ".join(details), failures)


def check_codex_supported_parity(failures: list[str]) -> None:
    proc = run([sys.executable, "scripts/harness_parity_audit.py", "--source", "claude", "--target", "codex", "--strict", "--json"])
    if proc.returncode != 0:
        fail((proc.stderr + proc.stdout).strip(), failures)


def check_staged_closure(failures: list[str]) -> None:
    staged = changed_staged()
    required: set[str] = set()
    for source, derived in DERIVED_BY_CONFIG.items():
        if source in staged:
            required.update(derived)
    missing = sorted(path for path in required if path not in staged)
    if missing:
        fail(
            "Derived-artifact closure failed for staged canonical changes. "
            "Stage regenerated artifacts too: " + ", ".join(missing),
            failures,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staged", action="store_true", help="also require staged source changes to include derived artifacts")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    failures: list[str] = []
    if args.staged:
        check_staged_closure(failures)
    check_hook_quality(failures)
    check_driver("settings-driver-claude-code.sh", ".claude/settings.json", failures)
    check_driver("settings-driver-codex.sh", ".codex/hooks.json", failures)
    check_driver("settings-driver-opencode.sh", "opencode.json", failures)
    check_claude_registry_parity(failures)
    check_codex_supported_parity(failures)
    report = {"status": "PASS" if not failures else "FAIL", "failures": failures}
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif failures:
        print("derived-artifact-gate: FAIL", file=sys.stderr)
        for item in failures:
            print(f"- {item}", file=sys.stderr)
    else:
        print("derived-artifact-gate: OK")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
