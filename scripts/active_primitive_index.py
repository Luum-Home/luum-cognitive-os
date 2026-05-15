#!/usr/bin/env python3
# SCOPE: os-only
"""Build the active agentic primitive index from the lifecycle manifest."""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "manifests" / "primitive-lifecycle.yaml"
TIERS = ("core", "team", "maintainer", "lab")
INACTIVE_STATES = {"candidate", "demoted", "archived", "deleted"}
ACTIVE_SURFACE_TIERS = {"core", "team", "maintainer"}
DEFAULT_VISIBLE_TIERS = {"core", "team"}
VISIBLE_WARN_THRESHOLD = 12
VISIBLE_FAIL_THRESHOLD = 25
ACTIVE_WARN_THRESHOLD = 25
# Existing maintainer runtime projection is above the original aspirational fail
# threshold; keep it visible as a warning and reserve failure for large regressions.
ACTIVE_FAIL_THRESHOLD = 96
RUNTIME_COVERAGE_WARN_RATIO = 0.95
HOOK_PATH_RE = re.compile(r"hooks/[A-Za-z0-9_.-]+\.sh")


@dataclass(frozen=True)
class PrimitiveEntry:
    id: str
    kind: str
    tier: str
    lifecycle_state: str
    maturity: str
    governance_class: str
    risk_class: str
    owner_adr: str
    active: bool
    default_visible: bool
    projection_targets: list[str]
    evidence_commands: list[str]
    runtime_projection: bool


class ActivePrimitiveIndexError(ValueError):
    """Raised when the active primitive index cannot be built."""


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle)
    except FileNotFoundError as exc:
        raise ActivePrimitiveIndexError(f"missing primitive lifecycle manifest: {path}") from exc
    except OSError as exc:
        raise ActivePrimitiveIndexError(f"cannot read primitive lifecycle manifest: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ActivePrimitiveIndexError(f"invalid primitive lifecycle manifest YAML: {exc}") from exc
    if not isinstance(loaded, dict):
        raise ActivePrimitiveIndexError("primitive lifecycle manifest root must be a mapping")
    return loaded


def primitive_to_entry(primitive: dict[str, Any]) -> PrimitiveEntry:
    primitive_id = primitive.get("id")
    tier = primitive.get("distribution")
    lifecycle_state = primitive.get("lifecycle_state")
    if tier not in TIERS:
        raise ActivePrimitiveIndexError(f"primitive {primitive_id!r} has unknown adoption tier {tier!r}")
    if not isinstance(primitive_id, str) or not primitive_id.strip():
        raise ActivePrimitiveIndexError("primitive id must be a non-empty string")
    state = lifecycle_state if isinstance(lifecycle_state, str) else "unknown"
    active = tier in ACTIVE_SURFACE_TIERS and state not in INACTIVE_STATES
    default_visible = tier in DEFAULT_VISIBLE_TIERS and active
    return PrimitiveEntry(
        id=primitive_id,
        kind=str(primitive.get("kind") or "unknown"),
        tier=str(tier),
        lifecycle_state=state,
        maturity=str(primitive.get("maturity") or "unknown"),
        governance_class=str(primitive.get("governance_class") or "unknown"),
        risk_class=str(primitive.get("risk_class") or "unknown"),
        owner_adr=str(primitive.get("owner_adr") or "unknown"),
        active=active,
        default_visible=default_visible,
        projection_targets=_string_list(primitive.get("projection_targets")),
        evidence_commands=_string_list(primitive.get("evidence_commands")),
        runtime_projection=bool(primitive.get("runtime_projection", False)),
    )


def build_entries(manifest: dict[str, Any]) -> list[PrimitiveEntry]:
    primitives = manifest.get("primitives")
    if not isinstance(primitives, list):
        raise ActivePrimitiveIndexError("primitive lifecycle manifest must contain a primitives list")
    entries: list[PrimitiveEntry] = []
    for primitive in primitives:
        if not isinstance(primitive, dict):
            raise ActivePrimitiveIndexError("each primitive lifecycle manifest entry must be a mapping")
        entries.append(primitive_to_entry(primitive))
    return entries


def _hook_path_from_primitive(entry: PrimitiveEntry) -> str | None:
    candidates = [entry.id, *entry.projection_targets, *entry.evidence_commands]
    for candidate in candidates:
        match = HOOK_PATH_RE.search(candidate)
        if match:
            return match.group(0)
        if candidate.startswith("hooks/") and not candidate.endswith(".sh"):
            return f"{candidate}.sh"
    return None


def _extract_hook_paths_from_command(command: str) -> list[str]:
    return HOOK_PATH_RE.findall(command or "")


def _load_claude_projected_hooks(root: Path) -> tuple[list[str], str]:
    settings_path = root / ".claude" / "settings.json"
    if not settings_path.exists():
        return [], "missing"
    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [], "invalid"
    hooks_by_event = data.get("hooks", {})
    if not isinstance(hooks_by_event, dict):
        return [], "invalid"
    projected: list[str] = []
    for matchers in hooks_by_event.values():
        if not isinstance(matchers, list):
            continue
        for matcher in matchers:
            if not isinstance(matcher, dict):
                continue
            hook_defs = matcher.get("hooks", [])
            if not isinstance(hook_defs, list):
                continue
            for hook_def in hook_defs:
                if not isinstance(hook_def, dict):
                    continue
                command = hook_def.get("command", "")
                if isinstance(command, str):
                    projected.extend(_extract_hook_paths_from_command(command))
    return projected, "ok"


def runtime_coverage(entries: list[PrimitiveEntry], root: Path) -> dict[str, Any]:
    projected_entries, source_status = _load_claude_projected_hooks(root)
    projected_unique = sorted(set(projected_entries))
    lifecycle_hooks = sorted(
        {hook for entry in entries if (hook := _hook_path_from_primitive(entry))}
    )
    lifecycle_hook_set = set(lifecycle_hooks)
    covered = sorted(path for path in projected_unique if path in lifecycle_hook_set)
    missing = sorted(path for path in projected_unique if path not in lifecycle_hook_set)
    projected_count = len(projected_unique)
    coverage_ratio = (len(covered) / projected_count) if projected_count else 1.0
    findings: list[dict[str, Any]] = []
    if source_status == "invalid":
        findings.append(
            {
                "id": "runtime-projection-unreadable",
                "severity": "fail",
                "message": "Claude settings projection exists but could not be parsed",
                "source": ".claude/settings.json",
            }
        )
    elif projected_count and coverage_ratio < RUNTIME_COVERAGE_WARN_RATIO:
        findings.append(
            {
                "id": "lifecycle-runtime-coverage-gap",
                "severity": "fail",
                "message": "projected runtime hooks are not covered by lifecycle metadata",
                "covered_unique_hooks": len(covered),
                "projected_unique_hooks": projected_count,
                "coverage_ratio": round(coverage_ratio, 4),
                "threshold": RUNTIME_COVERAGE_WARN_RATIO,
            }
        )
    return {
        "source": ".claude/settings.json",
        "source_status": source_status,
        "projected_hook_entries": len(projected_entries),
        "projected_unique_hooks": projected_count,
        "lifecycle_hook_count": len(lifecycle_hooks),
        "covered_unique_hooks": len(covered),
        "missing_unique_hooks": len(missing),
        "coverage_ratio": round(coverage_ratio, 4),
        "covered_hooks": covered,
        "missing_hooks": missing[:50],
        "missing_hooks_truncated": max(0, len(missing) - 50),
        "findings": findings,
        "status": "fail" if any(finding["severity"] == "fail" for finding in findings) else "pass",
    }


def summarize(entries: list[PrimitiveEntry], root: Path = REPO_ROOT) -> dict[str, Any]:
    counts_by_tier = {tier: 0 for tier in TIERS}
    active_counts_by_tier = {tier: 0 for tier in TIERS}
    default_visible_counts_by_tier = {tier: 0 for tier in TIERS}
    for entry in entries:
        counts_by_tier[entry.tier] += 1
        if entry.active:
            active_counts_by_tier[entry.tier] += 1
        if entry.default_visible:
            default_visible_counts_by_tier[entry.tier] += 1

    active_surface_count = sum(active_counts_by_tier[tier] for tier in ACTIVE_SURFACE_TIERS)
    runtime_active_surface_count = sum(
        1 for entry in entries
        if entry.active and entry.tier in ACTIVE_SURFACE_TIERS and entry.runtime_projection
    )
    default_visible_count = sum(default_visible_counts_by_tier[tier] for tier in DEFAULT_VISIBLE_TIERS)
    lab_active_count = active_counts_by_tier["lab"]
    coverage = runtime_coverage(entries, root)

    findings: list[dict[str, Any]] = []
    if default_visible_count > VISIBLE_FAIL_THRESHOLD:
        findings.append(
            {
                "id": "default-visible-surface-too-large",
                "severity": "fail",
                "message": "default-visible active primitive surface exceeds DX fail threshold",
                "count": default_visible_count,
                "threshold": VISIBLE_FAIL_THRESHOLD,
            }
        )
    elif default_visible_count > VISIBLE_WARN_THRESHOLD:
        findings.append(
            {
                "id": "default-visible-surface-near-limit",
                "severity": "warn",
                "message": "default-visible active primitive surface exceeds DX warning threshold",
                "count": default_visible_count,
                "threshold": VISIBLE_WARN_THRESHOLD,
            }
        )

    if runtime_active_surface_count > ACTIVE_FAIL_THRESHOLD:
        findings.append(
            {
                "id": "runtime-active-surface-too-large",
                "severity": "fail",
                "message": "core/team/maintainer runtime-projected active primitive surface exceeds DX fail threshold",
                "count": runtime_active_surface_count,
                "threshold": ACTIVE_FAIL_THRESHOLD,
            }
        )
    elif runtime_active_surface_count > ACTIVE_WARN_THRESHOLD:
        findings.append(
            {
                "id": "runtime-active-surface-near-limit",
                "severity": "warn",
                "message": "core/team/maintainer runtime-projected active primitive surface exceeds DX warning threshold",
                "count": runtime_active_surface_count,
                "threshold": ACTIVE_WARN_THRESHOLD,
            }
        )

    if lab_active_count:
        findings.append(
            {
                "id": "lab-primitives-marked-active",
                "severity": "fail",
                "message": "lab primitives must not count as active/default adoption surface",
                "count": lab_active_count,
                "threshold": 0,
            }
        )

    findings.extend(coverage["findings"])
    fail_count = sum(1 for finding in findings if finding["severity"] == "fail")
    warn_count = sum(1 for finding in findings if finding["severity"] == "warn")
    return {
        "counts_by_tier": counts_by_tier,
        "active_counts_by_tier": active_counts_by_tier,
        "default_visible_counts_by_tier": default_visible_counts_by_tier,
        "active_surface_count": active_surface_count,
        "runtime_active_surface_count": runtime_active_surface_count,
        "default_visible_count": default_visible_count,
        "runtime_coverage": coverage,
        "thresholds": {
            "default_visible_warn": VISIBLE_WARN_THRESHOLD,
            "default_visible_fail": VISIBLE_FAIL_THRESHOLD,
            "active_surface_warn": ACTIVE_WARN_THRESHOLD,
            "active_surface_fail": ACTIVE_FAIL_THRESHOLD,
            "runtime_coverage_warn_ratio": RUNTIME_COVERAGE_WARN_RATIO,
        },
        "findings": findings,
        "warn_count": warn_count,
        "fail_count": fail_count,
        "status": "fail" if fail_count else ("warn" if warn_count else "pass"),
    }


def build_index(
    manifest_path: Path = DEFAULT_MANIFEST,
    tier: str | None = None,
    project_root: Path | None = None,
) -> dict[str, Any]:
    if tier is not None and tier not in TIERS:
        raise ActivePrimitiveIndexError(f"unknown adoption tier {tier!r}; expected one of {', '.join(TIERS)}")
    manifest = load_manifest(manifest_path)
    all_entries = build_entries(manifest)
    filtered = [entry for entry in all_entries if tier is None or entry.tier == tier]
    root = project_root or manifest_path.resolve().parents[1]
    summary = summarize(all_entries, root)
    return {
        "manifest": str(manifest_path),
        "schema_version": manifest.get("schema_version"),
        "source_of_truth": "manifests/primitive-lifecycle.yaml",
        "tier_filter": tier,
        "tiers": list(TIERS),
        "summary": summary,
        "primitives": [asdict(entry) for entry in filtered],
    }


def print_human(index: dict[str, Any]) -> None:
    summary = index["summary"]
    coverage = summary["runtime_coverage"]
    print("Active agentic primitive index")
    print(f"source: {index['source_of_truth']}")
    print(f"status: {summary['status']} active_surface={summary['active_surface_count']} runtime_active={summary['runtime_active_surface_count']} default_visible={summary['default_visible_count']} runtime_coverage={coverage['coverage_ratio']}")
    print("counts by tier:")
    for tier in TIERS:
        total = summary["counts_by_tier"][tier]
        active = summary["active_counts_by_tier"][tier]
        visible = summary["default_visible_counts_by_tier"][tier]
        print(f"- {tier}: total={total} active={active} default_visible={visible}")
    print("runtime coverage:")
    print(
        f"- projected_hook_entries={coverage['projected_hook_entries']} "
        f"projected_unique_hooks={coverage['projected_unique_hooks']} "
        f"lifecycle_hook_count={coverage['lifecycle_hook_count']} "
        f"covered_unique_hooks={coverage['covered_unique_hooks']} "
        f"missing_unique_hooks={coverage['missing_unique_hooks']}"
    )
    if summary["findings"]:
        print("findings:")
        for finding in summary["findings"]:
            print(f"- {finding['severity'].upper()} {finding['id']}: {finding['message']} ({finding['count']}>{finding['threshold']})")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--project-dir", type=Path, default=None, help="project root containing runtime projection files")
    parser.add_argument("--tier", choices=TIERS, help="filter primitives by adoption tier")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON; this is the default")
    parser.add_argument("--human", action="store_true", help="emit a compact human summary")
    args = parser.parse_args(argv)
    try:
        index = build_index(args.manifest, args.tier, args.project_dir)
    except ActivePrimitiveIndexError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.human:
        print_human(index)
    else:
        print(json.dumps(index, indent=2, sort_keys=True))
    return 0 if index["summary"]["status"] != "fail" else 1


if __name__ == "__main__":
    raise SystemExit(main())
