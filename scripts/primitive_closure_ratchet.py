#!/usr/bin/env python3
# SCOPE: both
"""ADR-311 primitive closure ratchet.

Checks that high-risk governance primitives have a closed loop:
projection, runtime proof test, and language-routing debt ratchet. It is
intentionally small and deterministic so it can run in local quick lanes.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml


VALID_HARNESS_REQUIREMENT_STATUSES = {
    "required",
    "capability_gap",
    "adapter_gap",
    "structural_advisory",
    "command_surface",
    "roadmap",
}

RUNTIME_PROJECTION_PATHS = {
    "claude": ".claude/settings.json",
    "codex": ".codex/hooks.json",
}


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    message: str
    path: str = ""


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text()) or {}
    return data if isinstance(data, dict) else {}


def count_medium_plus_language_findings(report: Path) -> int:
    if not report.exists():
        return 0
    count = 0
    for line in report.read_text(encoding="utf-8", errors="replace").splitlines():
        if re.match(r"^\|\s*(high|medium)\s*\|", line):
            count += 1
    return count


def text_contains(path: Path, needle: str) -> bool:
    if not path.exists():
        return False
    return needle in path.read_text(encoding="utf-8", errors="replace")


def projection_closes_hook(root: Path, projection: Path, hook: str) -> bool:
    """Return true when a hook is directly projected or routed by dispatcher.

    Default interactive profiles intentionally project a small Bash dispatcher
    instead of the exhaustive PreToolUse:Bash mesh. For closure purposes, that
    is still a real runtime route only when both conditions hold:

    1. the harness projection contains the dispatcher, and
    2. the dispatcher source names the required hook.
    """

    if text_contains(projection, hook):
        return True
    dispatcher = "hooks/bash-hot-path-dispatcher.sh"
    return text_contains(projection, dispatcher) and text_contains(root / dispatcher, hook)


def implemented_harness_ids(root: Path) -> set[str]:
    projection_manifest = load_manifest(root / "manifests" / "harness-projection.yaml")
    harnesses = projection_manifest.get("harnesses") or []
    ids: set[str] = set()
    for harness in harnesses:
        if isinstance(harness, dict) and harness.get("status") == "implemented" and harness.get("id"):
            ids.add(str(harness["id"]))
    return ids


def expanded_harness_requirements(item: dict[str, Any]) -> dict[str, dict[str, Any]]:
    requirements = item.get("harness_requirements")
    if not isinstance(requirements, dict):
        return {}
    expanded: dict[str, dict[str, Any]] = {}
    for key, raw in requirements.items():
        if not isinstance(raw, dict):
            expanded[str(key)] = {"status": str(raw)}
            continue
        targets = raw.get("applies_to") or [key]
        if isinstance(targets, str):
            targets = [targets]
        for target in targets:
            expanded[str(target)] = raw
    return expanded


def check_harness_requirement_contract(root: Path, item: dict[str, Any], primitive: str) -> list[Finding]:
    findings: list[Finding] = []
    requirements = item.get("harness_requirements")
    if not isinstance(requirements, dict) or not requirements:
        findings.append(
            Finding(
                "legacy_claude_codex_only_projection_contract",
                "block",
                f"{primitive} must declare harness_requirements; claude_required/codex_required booleans are no longer sufficient",
                "manifests/primitive-closure-ratchet.yaml",
            )
        )
        return findings

    for key, raw in requirements.items():
        if not isinstance(raw, dict):
            findings.append(Finding("invalid_harness_requirement", "block", f"{primitive} harness requirement {key} must be a mapping", "manifests/primitive-closure-ratchet.yaml"))
            continue
        status = str(raw.get("status") or "")
        if status not in VALID_HARNESS_REQUIREMENT_STATUSES:
            findings.append(Finding("invalid_harness_requirement_status", "block", f"{primitive} harness requirement {key} has unsupported status {status!r}", "manifests/primitive-closure-ratchet.yaml"))
        if status != "required" and not str(raw.get("reason") or "").strip():
            findings.append(Finding("missing_harness_gap_reason", "block", f"{primitive} harness requirement {key} must explain non-required status {status!r}", "manifests/primitive-closure-ratchet.yaml"))

    implemented = implemented_harness_ids(root)
    if implemented:
        covered = set(expanded_harness_requirements(item))
        missing = sorted(implemented - covered)
        if missing:
            findings.append(
                Finding(
                    "missing_harness_projection_requirement",
                    "block",
                    f"{primitive} does not classify implemented harnesses: {', '.join(missing)}",
                    "manifests/primitive-closure-ratchet.yaml",
                )
            )
    return findings


def check_language_ratchet(root: Path, manifest: dict[str, Any]) -> list[Finding]:
    cfg = manifest.get("language_dependence") or {}
    report = root / str(cfg.get("report") or ".cognitive-os/reports/language-dependence-audit.md")
    max_allowed = int(cfg.get("max_medium_plus_findings") or 0)
    current = count_medium_plus_language_findings(report)
    if current > max_allowed:
        try:
            display_path = str(report.relative_to(root))
        except ValueError:
            display_path = str(report)
        return [Finding("language_medium_plus_regression", "block", f"language audit medium+ findings increased: {current} > baseline {max_allowed}", display_path)]
    return []


def check_runtime_proofs(root: Path, manifest: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    for item in manifest.get("required_runtime_proofs") or []:
        hook = root / str(item.get("hook") or "")
        test = root / str(item.get("test") or "")
        primitive = str(item.get("primitive") or hook.name)
        if not hook.exists():
            findings.append(Finding("missing_runtime_hook", "block", f"{primitive} hook is missing", str(hook.relative_to(root))))
        if not test.exists():
            findings.append(Finding("missing_runtime_proof", "block", f"{primitive} runtime proof test is missing", str(test.relative_to(root))))
    return findings


def check_hook_projections(root: Path, manifest: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    config = root / "cognitive-os.yaml"
    for item in manifest.get("critical_hook_projections") or []:
        hook = str(item.get("hook") or "")
        primitive = str(item.get("primitive") or hook)
        if not text_contains(config, hook):
            findings.append(Finding("missing_canonical_projection", "block", f"{primitive} missing from cognitive-os.yaml", "cognitive-os.yaml"))

        findings.extend(check_harness_requirement_contract(root, item, primitive))
        for harness_id, requirement in expanded_harness_requirements(item).items():
            if requirement.get("status") != "required":
                continue
            projection_path = RUNTIME_PROJECTION_PATHS.get(harness_id)
            if projection_path is None:
                findings.append(
                    Finding(
                        "uncheckable_required_harness_projection",
                        "block",
                        f"{primitive} marks {harness_id} required but the ratchet has no runtime projection checker for that harness",
                        "manifests/primitive-closure-ratchet.yaml",
                    )
                )
                continue
            if not projection_closes_hook(root, root / projection_path, hook):
                findings.append(Finding(f"missing_{harness_id}_projection", "block", f"{primitive} missing from {projection_path}", projection_path))
    return findings


def git_dirty_authority(root: Path, patterns: list[str]) -> list[str]:
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain=v1"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
    except Exception:
        return []
    dirty: list[str] = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if any(fnmatch.fnmatch(path, pat) for pat in patterns):
            dirty.append(path)
    return sorted(set(dirty))


def check_authority_dirty(root: Path, manifest: dict[str, Any]) -> list[Finding]:
    patterns = [str(p) for p in (manifest.get("authority_paths") or [])]
    dirty = git_dirty_authority(root, patterns)
    if not dirty:
        return []
    return [Finding("dirty_authority_paths", "warn", "authority files are modified; do not claim governance closure without committing or explicitly declaring WIP", ",".join(dirty))]


def run(root: Path, manifest_path: Path, check_dirty: bool = False) -> list[Finding]:
    manifest = load_manifest(manifest_path)
    findings: list[Finding] = []
    findings.extend(check_language_ratchet(root, manifest))
    findings.extend(check_runtime_proofs(root, manifest))
    findings.extend(check_hook_projections(root, manifest))
    if check_dirty:
        findings.extend(check_authority_dirty(root, manifest))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check ADR-311 primitive closure ratchets")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--manifest", type=Path, default=Path("manifests/primitive-closure-ratchet.yaml"))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--check-dirty", action="store_true", help="Warn if authority files are modified")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    manifest = args.manifest if args.manifest.is_absolute() else root / args.manifest
    findings = run(root, manifest, check_dirty=args.check_dirty)
    blocking = [f for f in findings if f.severity == "block"]
    if args.json:
        print(json.dumps({"valid": not blocking, "findings": [asdict(f) for f in findings]}, indent=2, sort_keys=True))
    else:
        if not findings:
            print("primitive-closure-ratchet: OK")
        for finding in findings:
            print(f"{finding.severity.upper()} {finding.code}: {finding.message} {finding.path}".rstrip())
    return 2 if blocking else 0


if __name__ == "__main__":
    raise SystemExit(main())
