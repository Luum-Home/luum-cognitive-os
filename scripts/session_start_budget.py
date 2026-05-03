#!/usr/bin/env python3
# SCOPE: both
"""Report and enforce SessionStart hook budget by adoption profile."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SETTINGS = REPO_ROOT / ".claude" / "settings.json"
MANIFEST = REPO_ROOT / "manifests" / "primitive-lifecycle.yaml"
TIMING = REPO_ROOT / ".cognitive-os" / "metrics" / "hook-timing.jsonl"
DRIVER = REPO_ROOT / "scripts" / "_lib" / "settings-driver-claude-code.sh"
HOOK_RE = re.compile(r"hooks/[A-Za-z0-9_.-]+\.sh")
PROFILE_BUDGETS = {
    "current": {"max_session_start_hooks": 20, "allow_lab": True},
    "core": {"max_session_start_hooks": 5, "allow_lab": False},
    "maintainer": {"max_session_start_hooks": 20, "allow_lab": True},
}


@dataclass(frozen=True)
class HookEntry:
    path: str
    distribution: str
    maturity: str
    lifecycle_state: str
    async_projected: bool
    p50_ms: float | None
    p95_ms: float | None
    samples: int
    candidate_reason: str | None = None


def _extract_hook(command: str) -> str | None:
    match = HOOK_RE.search(command or "")
    return match.group(0) if match else None


def load_settings(path: Path = SETTINGS) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def generated_settings(profile: str, root: Path = REPO_ROOT) -> dict[str, Any]:
    if profile == "current":
        return load_settings(root / ".claude" / "settings.json")
    env = {"PROJECT_DIR": str(root), "PROFILE": profile, "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"}
    proc = subprocess.run(
        ["bash", str(root / "scripts" / "_lib" / "settings-driver-claude-code.sh"), "--emit"],
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=20,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or f"driver failed for profile {profile}")
    return json.loads(proc.stdout)


def session_start_hooks(settings: dict[str, Any]) -> list[tuple[str, bool]]:
    hooks = settings.get("hooks", {}).get("SessionStart", [])
    result: list[tuple[str, bool]] = []
    for group in hooks if isinstance(hooks, list) else []:
        for hook in group.get("hooks", []) if isinstance(group, dict) else []:
            command = hook.get("command", "")
            path = _extract_hook(command)
            if path:
                result.append((path, bool(hook.get("async", False))))
    return result


def load_lifecycle(path: Path = MANIFEST) -> dict[str, dict[str, Any]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    primitives = data.get("primitives", []) if isinstance(data, dict) else []
    return {str(item.get("id")): item for item in primitives if isinstance(item, dict) and item.get("id")}


def load_timing(path: Path = TIMING) -> dict[str, list[float]]:
    timings: dict[str, list[float]] = {}
    if not path.exists():
        return timings
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("event") != "SessionStart":
            continue
        hook = str(row.get("hook") or row.get("hook_path") or "")
        hook_path = _extract_hook(hook) or (hook if hook.startswith("hooks/") else "")
        if not hook_path:
            continue
        duration = row.get("duration_ms")
        try:
            timings.setdefault(hook_path, []).append(float(duration))
        except (TypeError, ValueError):
            continue
    return timings


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 2)
    index = (len(ordered) - 1) * pct
    lo = int(index)
    hi = min(lo + 1, len(ordered) - 1)
    frac = index - lo
    return round(ordered[lo] * (1 - frac) + ordered[hi] * frac, 2)


def candidate_reason(primitive: dict[str, Any], profile: str) -> str | None:
    dist = primitive.get("distribution", "unknown")
    maturity = primitive.get("maturity", "unknown")
    state = primitive.get("lifecycle_state", "unknown")
    if profile == "core" and dist == "lab":
        return "lab primitive must not be in core SessionStart"
    if profile in {"core", "maintainer"} and maturity == "observe":
        return "observe-only startup hook should be lazy, scheduled, or maintainer-only unless boot-critical"
    if state == "sandbox":
        return "sandbox startup hook should not be in a consumer boot path"
    return None


def build_report(profile: str = "current", root: Path = REPO_ROOT) -> dict[str, Any]:
    if profile not in PROFILE_BUDGETS:
        raise ValueError(f"unknown profile {profile!r}")
    settings = generated_settings(profile, root)
    lifecycle = load_lifecycle(root / "manifests" / "primitive-lifecycle.yaml")
    timings = load_timing(root / ".cognitive-os" / "metrics" / "hook-timing.jsonl")
    hooks = session_start_hooks(settings)
    entries: list[HookEntry] = []
    counts_by_tier = {"core": 0, "team": 0, "maintainer": 0, "lab": 0, "unknown": 0}
    findings: list[dict[str, Any]] = []
    for path, async_projected in hooks:
        primitive = lifecycle.get(path, {})
        dist = str(primitive.get("distribution") or "unknown")
        if dist not in counts_by_tier:
            dist = "unknown"
        counts_by_tier[dist] += 1
        samples = timings.get(path, [])
        reason = candidate_reason(primitive, profile)
        entries.append(
            HookEntry(
                path=path,
                distribution=dist,
                maturity=str(primitive.get("maturity") or "unknown"),
                lifecycle_state=str(primitive.get("lifecycle_state") or "unknown"),
                async_projected=async_projected,
                p50_ms=percentile(samples, 0.50),
                p95_ms=percentile(samples, 0.95),
                samples=len(samples),
                candidate_reason=reason,
            )
        )
    budget = PROFILE_BUDGETS[profile]
    if len(hooks) > budget["max_session_start_hooks"]:
        findings.append({
            "id": "session-start-over-budget",
            "severity": "fail" if profile == "core" else "warn",
            "message": "SessionStart hook count exceeds profile budget",
            "count": len(hooks),
            "budget": budget["max_session_start_hooks"],
        })
    if not budget["allow_lab"] and counts_by_tier["lab"]:
        findings.append({
            "id": "core-session-start-lab-hooks",
            "severity": "fail",
            "message": "core SessionStart projection contains lab hooks",
            "count": counts_by_tier["lab"],
            "hooks": [asdict(item) for item in entries if item.distribution == "lab"],
        })
    fail_count = sum(1 for f in findings if f["severity"] == "fail")
    warn_count = sum(1 for f in findings if f["severity"] == "warn")
    return {
        "status": "fail" if fail_count else ("warn" if warn_count else "pass"),
        "profile": profile,
        "session_start_hook_count": len(hooks),
        "counts_by_tier": counts_by_tier,
        "budget": budget,
        "hooks": [asdict(item) for item in entries],
        "candidates_to_move": [asdict(item) for item in entries if item.candidate_reason],
        "findings": findings,
        "fail_count": fail_count,
        "warn_count": warn_count,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=sorted(PROFILE_BUDGETS), default="current")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--fail-on-findings", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = build_report(args.profile)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(
            f"SessionStart budget: {report['status']} profile={report['profile']} "
            f"hooks={report['session_start_hook_count']} tiers={report['counts_by_tier']}"
        )
        for finding in report["findings"]:
            print(f"- {finding['severity'].upper()} {finding['id']}: {finding['message']}")
        if report["candidates_to_move"]:
            print("candidates to move out of SessionStart:")
            for item in report["candidates_to_move"][:20]:
                print(f"- {item['path']} ({item['distribution']}/{item['maturity']}): {item['candidate_reason']}")
    if args.fail_on_findings and report["fail_count"]:
        return 1
    return 0 if report["status"] != "fail" else 1


if __name__ == "__main__":
    raise SystemExit(main())
