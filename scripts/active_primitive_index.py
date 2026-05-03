#!/usr/bin/env python3
# SCOPE: both
"""Build the active agentic primitive index from the lifecycle manifest."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "manifests" / "primitive-lifecycle.yaml"
TIERS = ("core", "team", "maintainer", "lab")
INACTIVE_STATES = {"demoted", "archived", "deleted"}
ACTIVE_SURFACE_TIERS = {"core", "team", "maintainer"}
DEFAULT_VISIBLE_TIERS = {"core", "team"}
VISIBLE_WARN_THRESHOLD = 12
VISIBLE_FAIL_THRESHOLD = 25
ACTIVE_WARN_THRESHOLD = 24
ACTIVE_FAIL_THRESHOLD = 48


@dataclass(frozen=True)
class PrimitiveEntry:
    id: str
    kind: str
    tier: str
    lifecycle_state: str
    governance_class: str
    risk_class: str
    owner_adr: str
    active: bool
    default_visible: bool
    projection_targets: list[str]
    evidence_commands: list[str]


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
        governance_class=str(primitive.get("governance_class") or "unknown"),
        risk_class=str(primitive.get("risk_class") or "unknown"),
        owner_adr=str(primitive.get("owner_adr") or "unknown"),
        active=active,
        default_visible=default_visible,
        projection_targets=_string_list(primitive.get("projection_targets")),
        evidence_commands=_string_list(primitive.get("evidence_commands")),
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


def summarize(entries: list[PrimitiveEntry]) -> dict[str, Any]:
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
    default_visible_count = sum(default_visible_counts_by_tier[tier] for tier in DEFAULT_VISIBLE_TIERS)
    lab_active_count = active_counts_by_tier["lab"]

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

    if active_surface_count > ACTIVE_FAIL_THRESHOLD:
        findings.append(
            {
                "id": "active-surface-too-large",
                "severity": "fail",
                "message": "core/team/maintainer active primitive surface exceeds DX fail threshold",
                "count": active_surface_count,
                "threshold": ACTIVE_FAIL_THRESHOLD,
            }
        )
    elif active_surface_count > ACTIVE_WARN_THRESHOLD:
        findings.append(
            {
                "id": "active-surface-near-limit",
                "severity": "warn",
                "message": "core/team/maintainer active primitive surface exceeds DX warning threshold",
                "count": active_surface_count,
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

    fail_count = sum(1 for finding in findings if finding["severity"] == "fail")
    warn_count = sum(1 for finding in findings if finding["severity"] == "warn")
    return {
        "counts_by_tier": counts_by_tier,
        "active_counts_by_tier": active_counts_by_tier,
        "default_visible_counts_by_tier": default_visible_counts_by_tier,
        "active_surface_count": active_surface_count,
        "default_visible_count": default_visible_count,
        "thresholds": {
            "default_visible_warn": VISIBLE_WARN_THRESHOLD,
            "default_visible_fail": VISIBLE_FAIL_THRESHOLD,
            "active_surface_warn": ACTIVE_WARN_THRESHOLD,
            "active_surface_fail": ACTIVE_FAIL_THRESHOLD,
        },
        "findings": findings,
        "warn_count": warn_count,
        "fail_count": fail_count,
        "status": "fail" if fail_count else ("warn" if warn_count else "pass"),
    }


def build_index(manifest_path: Path = DEFAULT_MANIFEST, tier: str | None = None) -> dict[str, Any]:
    if tier is not None and tier not in TIERS:
        raise ActivePrimitiveIndexError(f"unknown adoption tier {tier!r}; expected one of {', '.join(TIERS)}")
    manifest = load_manifest(manifest_path)
    all_entries = build_entries(manifest)
    filtered = [entry for entry in all_entries if tier is None or entry.tier == tier]
    summary = summarize(all_entries)
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
    print("Active agentic primitive index")
    print(f"source: {index['source_of_truth']}")
    print(f"status: {summary['status']} active_surface={summary['active_surface_count']} default_visible={summary['default_visible_count']}")
    print("counts by tier:")
    for tier in TIERS:
        total = summary["counts_by_tier"][tier]
        active = summary["active_counts_by_tier"][tier]
        visible = summary["default_visible_counts_by_tier"][tier]
        print(f"- {tier}: total={total} active={active} default_visible={visible}")
    if summary["findings"]:
        print("findings:")
        for finding in summary["findings"]:
            print(f"- {finding['severity'].upper()} {finding['id']}: {finding['message']} ({finding['count']}>{finding['threshold']})")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--tier", choices=TIERS, help="filter primitives by adoption tier")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON; this is the default")
    parser.add_argument("--human", action="store_true", help="emit a compact human summary")
    args = parser.parse_args(argv)
    try:
        index = build_index(args.manifest, args.tier)
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
