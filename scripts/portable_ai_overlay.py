#!/usr/bin/env python3
# SCOPE: both
"""Generate a portable `.ai/` overlay for Cognitive OS agentic primitives.

The overlay is intentionally generated from existing COS sources. It is not the
canonical source of truth while ADR-258 is still proving the surface.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.primitive_contracts import load_contracts

SCHEMA_VERSION = "portable-ai-overlay.v1"
CONTEXT_SCHEMA_VERSION = "portable-ai-context.v1"
PRIMITIVE_SCHEMA_VERSION = "portable-ai-primitive.v1"
PROFILE_SCHEMA_VERSION = "portable-ai-profile.v1"
ADAPTER_SCHEMA_VERSION = "portable-ai-adapter.v1"
DEFAULT_HARNESSES = ["claude", "codex", "cursor", "windsurf", "vscode-copilot", "kiro", "opencode", "shell-ci"]
ADAPTER_DIR_NAMES = {
    "claude": "claude-code",
    "codex": "codex",
    "cursor": "cursor",
    "windsurf": "windsurf",
    "vscode-copilot": "copilot",
    "kiro": "kiro",
    "opencode": "opencode",
    "shell-ci": "shell-ci",
}
FAMILY_TO_DIR = {
    "hook": "hooks",
    "skill": "skills",
    "rule": "rules",
    "workflow": "workflows",
    "script": "tools",
    "agent": "agents",
    "memory": "memory",
}
ENFORCEMENT_FIDELITY = {"native-lifecycle-enforced", "governed-wrapper-enforced", "ci-enforced"}


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def _slug(value: str) -> str:
    safe = "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")
    safe = "-".join(part for part in safe.split("-") if part)
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:10]
    if not safe:
        safe = "primitive"
    return f"{safe[:80]}-{digest}"


def _family_dir(family: str) -> str:
    return FAMILY_TO_DIR.get(family, f"other-{_slug(family).split('-')[0]}")


def _contract_projection(contract: dict[str, Any] | None) -> dict[str, Any]:
    if not contract:
        return {}
    out: dict[str, Any] = {}
    for harness, row in sorted((contract.get("projection") or {}).items()):
        if not isinstance(row, dict):
            continue
        fidelity = str(row.get("fidelity", "unsupported"))
        out[str(harness)] = {
            "fidelity": fidelity,
            "surface": row.get("surface"),
            "claims_runtime_enforcement": fidelity in ENFORCEMENT_FIDELITY,
        }
    return out



def _derived_portable_contract(primitive_id: str, family: str, lifecycle: dict[str, Any], contract: dict[str, Any] | None) -> dict[str, Any]:
    """Return a portable contract view for both registry-backed and lifecycle-derived rows."""
    if contract:
        return {
            "source": "primitive-contract-registry",
            "contract_id": contract.get("id"),
            "intent": contract.get("intent"),
            "requires": list(contract.get("requires") or []),
            "trigger": contract.get("trigger"),
            "actions": contract.get("actions"),
            "evidence": contract.get("evidence") or {},
            "projection_fidelity": _contract_projection(contract),
            "impact": contract.get("impact"),
            "is_full_contract": True,
        }
    supported = list(lifecycle.get("supported_harnesses") or [])
    projection_fidelity = {
        harness: {
            "fidelity": "documented-only",
            "surface": "derived from primitive-lifecycle metadata; not a runtime enforcement claim",
            "claims_runtime_enforcement": False,
        }
        for harness in sorted(supported)
    }
    runtime_projection = bool(lifecycle.get("runtime_projection"))
    return {
        "source": "primitive-lifecycle-derived",
        "contract_id": None,
        "intent": lifecycle.get("behavior_evidence") or f"Lifecycle-derived portable contract for {primitive_id}.",
        "requires": ["respect_declared_scope", "preserve_evidence_commands"],
        "trigger": {
            "kind": "lifecycle_declared" if runtime_projection else "documented_or_on_demand",
            "runtime_projection": runtime_projection,
            "projection_targets": list(lifecycle.get("projection_targets") or []),
        },
        "actions": {
            "preferred": "observe" if runtime_projection else "document",
            "fallback": "document",
            "reason_codes": ["lifecycle_derived_contract"],
        },
        "evidence": {
            "behavior_evidence": lifecycle.get("behavior_evidence"),
            "evidence_commands": list(lifecycle.get("evidence_commands") or []),
            "metrics": [lifecycle.get("metrics_file")] if lifecycle.get("metrics_file") and lifecycle.get("metrics_file") != "none" else [],
        },
        "projection_fidelity": projection_fidelity,
        "impact": {
            "consumer_fleet": "unknown",
            "service_mode": "unsupported" if not runtime_projection else "harness-embedded-only",
        },
        "is_full_contract": True,
        "derived_contract_warning": "Derived from lifecycle metadata; promote to manifests/primitive-contracts.yaml before claiming contract-registry governance.",
    }

def _primitive_rows(root: Path) -> list[tuple[str, dict[str, Any]]]:
    contracts = {}
    contracts_by_id = {}
    contracts_by_lifecycle = {}
    for item in load_contracts(root):
        contracts_by_id[str(item.get("id"))] = item
        if item.get("lifecycle_ref"):
            contracts_by_lifecycle[str(item.get("lifecycle_ref"))] = item
        for key in (item.get("source"), item.get("id")):
            if key and str(key) not in contracts:
                contracts[str(key)] = item
    lifecycle = _load_yaml(root / "manifests" / "primitive-lifecycle.yaml")
    rows = lifecycle.get("primitives") or []
    out: list[tuple[str, dict[str, Any]]] = []
    seen: set[str] = set()

    for item in rows:
        if not isinstance(item, dict):
            continue
        primitive_id = str(item.get("id", "")).strip()
        if not primitive_id:
            continue
        seen.add(primitive_id)
        family = str(item.get("kind") or "unknown")
        contract = contracts_by_lifecycle.get(primitive_id) or contracts.get(primitive_id) or contracts_by_id.get(primitive_id)
        if contract:
            for key in (contract.get("id"), contract.get("source"), contract.get("lifecycle_ref")):
                if key:
                    seen.add(str(key))
        portable_id = str(contract.get("id")) if contract else primitive_id
        portable_contract = _derived_portable_contract(primitive_id, family, item, contract)
        row = {
            "schema_version": PRIMITIVE_SCHEMA_VERSION,
            "portable_id": portable_id,
            "source_id": primitive_id,
            "family": family,
            "canonical_source": str(contract.get("source")) if contract else primitive_id,
            "canonical_source_kind": "cos-internal",
            "overlay_role": "generated-reference",
            "lifecycle": {
                "owner_adr": item.get("owner_adr"),
                "lifecycle_state": item.get("lifecycle_state"),
                "maturity": item.get("maturity"),
                "distribution": item.get("distribution"),
                "governance_class": item.get("governance_class"),
                "risk_class": item.get("risk_class"),
                "runtime_projection": bool(item.get("runtime_projection")),
                "docs_claim_level": item.get("docs_claim_level"),
                "exit_behavior": item.get("exit_behavior"),
            },
            "supported_harnesses": list(item.get("supported_harnesses") or []),
            "projection_targets": list(item.get("projection_targets") or []),
            "evidence": {
                "behavior_evidence": item.get("behavior_evidence"),
                "evidence_commands": list(item.get("evidence_commands") or []),
                "metrics_file": item.get("metrics_file"),
            },
            "contract": {
                "present": bool(contract),
                "contract_id": contract.get("id") if contract else None,
                "intent": contract.get("intent") if contract else item.get("behavior_evidence"),
                "requires": list(contract.get("requires") or []) if contract else [],
                "trigger": contract.get("trigger") if contract else None,
                "actions": contract.get("actions") if contract else None,
                "projection_fidelity": _contract_projection(contract),
                "impact": contract.get("impact") if contract else None,
            },
            "portable_contract": portable_contract,
        }
        rel = Path("primitives") / _family_dir(family) / f"{_slug(portable_id)}.json"
        out.append((rel.as_posix(), row))

    # Ensure contract-only rows are still exported if the lifecycle manifest lags.
    for contract in load_contracts(root):
        source = str(contract.get("source") or contract.get("id"))
        contract_id = str(contract.get("id"))
        if source in seen or contract_id in seen:
            continue
        family = str(contract.get("family") or "unknown")
        portable_contract = _derived_portable_contract(source, family, {}, contract)
        row = {
            "schema_version": PRIMITIVE_SCHEMA_VERSION,
            "portable_id": contract_id,
            "source_id": source,
            "family": family,
            "canonical_source": source,
            "canonical_source_kind": "cos-internal",
            "overlay_role": "generated-reference",
            "lifecycle": None,
            "supported_harnesses": sorted((contract.get("projection") or {}).keys()),
            "projection_targets": [source],
            "evidence": contract.get("evidence") or {},
            "contract": {
                "present": True,
                "contract_id": contract_id,
                "intent": contract.get("intent"),
                "requires": list(contract.get("requires") or []),
                "trigger": contract.get("trigger"),
                "actions": contract.get("actions"),
                "projection_fidelity": _contract_projection(contract),
                "impact": contract.get("impact"),
            },
            "portable_contract": portable_contract,
        }
        rel = Path("primitives") / _family_dir(family) / f"{_slug(contract_id)}.json"
        out.append((rel.as_posix(), row))

    return sorted(out, key=lambda pair: pair[0])


def _harness_projection(root: Path) -> dict[str, dict[str, Any]]:
    data = _load_yaml(root / "manifests" / "harness-projection.yaml")
    out: dict[str, dict[str, Any]] = {}
    for item in data.get("harnesses") or []:
        if isinstance(item, dict) and item.get("id"):
            out[str(item["id"])] = item
    return out


def _profile_rows(root: Path, primitive_rows: list[tuple[str, dict[str, Any]]]) -> list[tuple[str, dict[str, Any]]]:
    harnesses = _harness_projection(root)
    contracts = load_contracts(root)
    all_harnesses = sorted(set(DEFAULT_HARNESSES) | set(harnesses))
    rows: list[tuple[str, dict[str, Any]]] = []
    for harness in all_harnesses:
        hp = harnesses.get(harness, {})
        contract_projection = []
        projection_fallback = hp.get("contract_projection_fallback") if isinstance(hp, dict) else None
        for contract in contracts:
            projection = (contract.get("projection") or {}).get(harness)
            derived_from_harness = None
            if not isinstance(projection, dict) and isinstance(projection_fallback, dict):
                projection = projection_fallback
                derived_from_harness = "harness-projection.yaml:contract_projection_fallback"
            if isinstance(projection, dict):
                fidelity = str(projection.get("fidelity", "unsupported"))
                item = {
                    "contract_id": contract.get("id"),
                    "fidelity": fidelity,
                    "surface": projection.get("surface"),
                    "claims_runtime_enforcement": fidelity in ENFORCEMENT_FIDELITY,
                }
                if derived_from_harness:
                    item["derived_from"] = derived_from_harness
                contract_projection.append(item)
        lifecycle_count = 0
        for _, row in primitive_rows:
            if harness in row.get("supported_harnesses", []):
                lifecycle_count += 1
        profile = {
            "schema_version": PROFILE_SCHEMA_VERSION,
            "adapter_contract_kind": "declarative-fidelity-profile",
            "native_file_emission": False,
            "native_projection_driver": "scripts/cos_init.py and harness-specific projection drivers",
            "compiler_gap_policy": "Profiles expose declared fidelity; native IDE files are emitted by governed projection drivers through the fidelity-preserving adapter compiler.",
            "harness": harness,
            "display_name": hp.get("display_name", harness),
            "status": hp.get("status", "unknown"),
            "projection_mode": hp.get("projection_mode"),
            "proof_level": hp.get("proof_level"),
            "settings_paths": list(hp.get("settings_paths") or []),
            "projected_surfaces": list(hp.get("projected_surfaces") or []),
            "limitations": list(hp.get("limitations") or []),
            "adapter_directory": f"adapters/{ADAPTER_DIR_NAMES.get(harness, harness)}",
            "lifecycle_primitives_supporting_harness": lifecycle_count,
            "contract_projection_fidelity": contract_projection,
            "fidelity_policy": "Declare adapter fidelity from primitive contracts; do not infer enforcement from advisory files.",
        }
        rows.append((f"profiles/{harness}.json", profile))
    return rows


def _adapter_manifest_rows(root: Path, primitive_rows: list[tuple[str, dict[str, Any]]]) -> list[tuple[str, dict[str, Any]]]:
    harnesses = _harness_projection(root)
    all_harnesses = sorted(set(DEFAULT_HARNESSES) | set(harnesses))
    rows: list[tuple[str, dict[str, Any]]] = []
    for harness in all_harnesses:
        dirname = ADAPTER_DIR_NAMES.get(harness, harness)
        hp = harnesses.get(harness, {})
        projected = []
        projected_ids: set[str] = set()
        projection_fallback = hp.get("contract_projection_fallback") if isinstance(hp, dict) else None
        for rel, row in primitive_rows:
            projection = ((row.get("portable_contract") or {}).get("projection_fidelity") or {}).get(harness)
            derived_from_harness = None
            if not projection and isinstance(projection_fallback, dict) and (row.get("contract") or {}).get("present"):
                projection = {
                    "fidelity": projection_fallback.get("fidelity"),
                    "surface": projection_fallback.get("surface"),
                    "claims_runtime_enforcement": False,
                }
                derived_from_harness = "harness-projection.yaml:contract_projection_fallback"
            if projection:
                portable_id = str(row.get("portable_id"))
                if portable_id in projected_ids:
                    continue
                projected_ids.add(portable_id)
                item = {
                    "portable_id": portable_id,
                    "primitive_file": rel,
                    "fidelity": projection.get("fidelity"),
                    "surface": projection.get("surface"),
                    "claims_runtime_enforcement": bool(projection.get("claims_runtime_enforcement")),
                }
                if derived_from_harness:
                    item["derived_from"] = derived_from_harness
                projected.append(item)
        manifest = {
            "schema_version": ADAPTER_SCHEMA_VERSION,
            "adapter_contract_kind": "declarative-manifest",
            "native_file_emission": False,
            "native_projection_driver": "scripts/cos_init.py and harness-specific projection drivers",
            "compiler_gap_policy": "This generated .ai adapter manifest does not install native IDE files; any compiler must preserve projection_fidelity and must not upgrade structural-advisory rows to enforcement.",
            "harness": harness,
            "display_name": hp.get("display_name", harness),
            "status": hp.get("status", "unknown"),
            "proof_level": hp.get("proof_level"),
            "projection_mode": hp.get("projection_mode"),
            "settings_paths": list(hp.get("settings_paths") or []),
            "projected_primitive_count": len(projected),
            "projected_primitives": projected,
            "fidelity_policy": "Adapter manifests translate declared portable contracts and never upgrade advisory projections to enforcement.",
        }
        rows.append((f"adapters/{dirname}/adapter.json", manifest))
    return rows


def _adapter_rows(root: Path) -> list[tuple[str, str]]:
    harnesses = _harness_projection(root)
    all_harnesses = sorted(set(DEFAULT_HARNESSES) | set(harnesses))
    rows: list[tuple[str, str]] = []
    for harness in all_harnesses:
        dirname = ADAPTER_DIR_NAMES.get(harness, harness)
        hp = harnesses.get(harness, {})
        lines = [
            f"# {hp.get('display_name', harness)} portable `.ai` adapter",
            "",
            f"Schema: `{ADAPTER_SCHEMA_VERSION}`",
            "",
            "This adapter is generated from Cognitive OS canonical primitive manifests.",
            "It must not invent primitive behavior or overclaim runtime enforcement.",
            "It is declarative: native IDE file emission is delegated to governed harness projection drivers through the adapter compiler.",
            "",
            "## Current projection",
            "",
            f"- harness id: `{harness}`",
            f"- status: `{hp.get('status', 'unknown')}`",
            f"- proof level: `{hp.get('proof_level', 'unknown')}`",
            f"- projection mode: `{hp.get('projection_mode', 'unknown')}`",
            "",
            "## Settings paths",
            "",
        ]
        settings = list(hp.get("settings_paths") or [])
        if settings:
            lines.extend(f"- `{path}`" for path in settings)
        else:
            lines.append("- none declared")
        lines.extend([
            "",
            "## Rule",
            "",
            "Read `.ai/profiles/{0}.json` for declared fidelity before projecting primitives into this host.".format(harness),
            "Structural advisory surfaces are not runtime enforcement.",
            "",
        ])
        rows.append((f"adapters/{dirname}/README.md", "\n".join(lines)))
    return rows


def build_overlay(root: Path) -> dict[str, str]:
    primitive_rows = _primitive_rows(root)
    files: dict[str, str] = {}
    summary_by_family: dict[str, int] = {}
    for rel, row in primitive_rows:
        summary_by_family[row["family"]] = summary_by_family.get(row["family"], 0) + 1
        files[rel] = json.dumps(row, indent=2, sort_keys=True) + "\n"

    skill_sources = set((root / "skills").glob("**/SKILL.md"))
    skill_sources.update((root / "packages").glob("*/skills/*/SKILL.md"))
    skill_source_count = len(skill_sources)
    skill_overlay_count = summary_by_family.get("skill", 0)
    skill_overlay_excluded_count = max(skill_source_count - skill_overlay_count, 0)

    context = {
        "schema_version": CONTEXT_SCHEMA_VERSION,
        "overlay_schema_version": SCHEMA_VERSION,
        "status": "generated-portable-overlay",
        "canonical_source_of_truth": [
            "manifests/primitive-contracts.yaml",
            "manifests/primitive-lifecycle.yaml",
            "hooks/",
            "skills/",
            "rules/",
            "scripts/",
        ],
        "policy": "The `.ai` tree is a generated maintainer overlay until ADR-258 Phase 5 decides otherwise; it is not the editable consumer primitive source.",
        "consumer_package_policy": "Consumer-friendly .ai packages and native IDE files are generated by governed projection drivers and the fidelity-preserving adapter compiler from canonical contracts, preserving projection fidelity.",
        "native_file_emission": False,
        "native_projection_drivers": [
            "scripts/cos_init.py",
            "scripts/cos-adapters",
            "harness-specific projection drivers",
        ],
        "source_manifests": [
            "manifests/primitive-contracts.yaml",
            "manifests/primitive-lifecycle.yaml",
            "manifests/harness-projection.yaml",
        ],
        "primitive_count": len(primitive_rows),
        "primitive_count_by_family": dict(sorted(summary_by_family.items())),
        "skill_source_count": skill_source_count,
        "skill_overlay_count": skill_overlay_count,
        "skill_overlay_excluded_count": skill_overlay_excluded_count,
        "skill_overlay_coverage_policy": (
            "Only lifecycle/contract-promoted skills are emitted as .ai primitive rows; "
            "other skills/*/SKILL.md files remain package/source content until promoted "
            "through primitive lifecycle and contract manifests."
        ),
        "adapter_profiles": sorted([path for path, _ in _profile_rows(root, primitive_rows)]),
        "runtime_evidence_streams": [
            ".cognitive-os/metrics/primitive-interventions.jsonl",
            ".cognitive-os/metrics/codebase-itinerary.jsonl",
        ],
    }
    files["context.json"] = json.dumps(context, indent=2, sort_keys=True) + "\n"
    for rel, row in _profile_rows(root, primitive_rows):
        files[rel] = json.dumps(row, indent=2, sort_keys=True) + "\n"
    for rel, text in _adapter_rows(root):
        files[rel] = text
    for rel, row in _adapter_manifest_rows(root, primitive_rows):
        files[rel] = json.dumps(row, indent=2, sort_keys=True) + "\n"
    files["logs/schema/primitive-interventions.schema.json"] = json.dumps({
        "schema_version": "primitive-intervention.v1",
        "description": "Runtime primitive intervention ledger rows; generated overlay reference only.",
        "required_fields": ["schema_version", "session_id", "tool_use_id", "primitive_id", "action_kind", "reason_code"],
        "privacy": "Do not store raw secrets, tool output, or unredacted command content.",
    }, indent=2, sort_keys=True) + "\n"
    files["logs/schema/codebase-itinerary.schema.json"] = json.dumps({
        "schema_version": "codebase-itinerary.v1",
        "description": "Content-free codebase access itinerary rows; generated overlay reference only.",
        "required_fields": ["schema_version", "session_id", "tool_use_id", "tool", "target"],
        "privacy": "Store hashes and metadata only; never raw file contents, grep patterns, or tool output.",
    }, indent=2, sort_keys=True) + "\n"
    files["state/.gitkeep"] = ""
    return dict(sorted(files.items()))


def write_overlay(files: dict[str, str], output: Path, clean: bool = True) -> None:
    if clean and output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    for rel, text in files.items():
        path = output / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=Path(".ai"))
    parser.add_argument("--check", action="store_true", help="fail if the on-disk overlay differs")
    parser.add_argument("--no-clean", action="store_true", help="do not remove existing output before writing")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    output = args.output if args.output.is_absolute() else root / args.output
    files = build_overlay(root)

    if args.check:
        mismatches: list[str] = []
        expected = set(files)
        existing = {p.relative_to(output).as_posix() for p in output.rglob("*") if p.is_file()} if output.exists() else set()
        for rel in sorted(expected | existing):
            expected_text = files.get(rel)
            actual_path = output / rel
            actual_text = actual_path.read_text(encoding="utf-8") if actual_path.exists() else None
            if expected_text != actual_text:
                mismatches.append(rel)
        if mismatches:
            print("Portable .ai overlay is stale:", file=sys.stderr)
            for rel in mismatches[:50]:
                print(f"  {rel}", file=sys.stderr)
            if len(mismatches) > 50:
                print(f"  ... {len(mismatches) - 50} more", file=sys.stderr)
            return 1
        print(f"Portable .ai overlay is current ({len(files)} files).")
        return 0

    write_overlay(files, output, clean=not args.no_clean)
    print(f"Wrote portable .ai overlay to {output} ({len(files)} files).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
