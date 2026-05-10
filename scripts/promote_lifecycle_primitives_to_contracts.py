#!/usr/bin/env python3
# SCOPE: both
"""Promote lifecycle-derived primitives into conservative ADR-256 contracts.

This is intentionally conservative: it makes every primitive registry-backed
without claiming runtime enforcement for harnesses that do not have signed proof.
Runtime promotion remains explicit through per-harness smoke evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "manifests" / "primitive-contracts.yaml"
LIFECYCLE = ROOT / "manifests" / "primitive-lifecycle.yaml"
INTERVENTION_LEDGER = ".cognitive-os/metrics/primitive-interventions.jsonl"
REQUIRED_HARNESSES = ["claude", "codex", "opencode", "cursor", "vscode-copilot", "shell-ci"]
SIGNED_OPENCODE = {
    "destructive-git-blocker",
    "destructive-rm-blocker",
    "reinvention-check",
    "large-file-advisor",
    "skill-router",
    "aci-observation-capture",
    "adr-relevance-suggest",
    "adr-section-validator",
    "agent-bash-cwd-enforcer",
    "agent-control-inbound-guard",
    "auto-rollback-trigger",
    "auto-verify",
    "claim-validator",
    "confidence-gate",
    "confidentiality-enforcer",
    "content-policy",
    "context-watchdog",
    "cosd-auth-guard",
    "dispatch-gate",
    "doc-sync-detector",
}


def _safe_id(value: str) -> str:
    path = Path(value)
    if path.name == "SKILL.md" and len(path.parts) >= 2:
        base = f"{path.parts[-2]}-skill"
    else:
        base = path.name
    for suffix in (".sh", ".py", ".md", ".yaml", ".yml", ".json"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
    if path.parts and path.parts[0] == "rules" and not base.endswith("-rule"):
        base = f"{base}-rule"
    if path.parts and path.parts[0] == "scripts" and not base.startswith("script-"):
        base = f"script-{base}"
    safe = re.sub(r"[^a-zA-Z0-9]+", "-", base).strip("-").lower() or "primitive"
    return safe


def _unique_id(source: str, used: set[str]) -> str:
    candidate = _safe_id(source)
    if candidate not in used:
        used.add(candidate)
        return candidate
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()[:8]
    candidate = f"{candidate}-{digest}"
    used.add(candidate)
    return candidate


def _proof_tests(commands: list[str]) -> list[str]:
    tests: list[str] = []
    for command in commands:
        for match in re.findall(r"tests/[A-Za-z0-9_./-]+\.py", str(command)):
            if (ROOT / match).exists() and match not in tests:
                tests.append(match)
    if not tests:
        tests.append("tests/contracts/test_primitive_contract_registry.py")
    return tests


def _preferred_action(row: dict[str, Any]) -> str:
    state = str(row.get("lifecycle_state") or "")
    exit_behavior = str(row.get("exit_behavior") or "")
    risk = str(row.get("risk_class") or "")
    if state == "blocking" or exit_behavior == "exit_2" or risk == "blocking":
        return "block"
    if str(row.get("runtime_projection")).lower() == "true":
        return "observe"
    return "observe"


def _trigger(row: dict[str, Any]) -> dict[str, Any]:
    family = str(row.get("kind") or "unknown")
    runtime_projection = bool(row.get("runtime_projection"))
    targets = list(row.get("projection_targets") or [row.get("id")])
    if family == "hook":
        return {
            "kind": "lifecycle_declared_tool_event" if runtime_projection else "documented_or_dependency",
            "runtime_projection": runtime_projection,
            "projection_targets": targets,
        }
    return {
        "kind": "documented_or_on_demand",
        "runtime_projection": runtime_projection,
        "projection_targets": targets,
    }


def _projection(contract_id: str, row: dict[str, Any]) -> dict[str, Any]:
    runtime_projection = bool(row.get("runtime_projection"))
    supported = set(row.get("supported_harnesses") or [])
    out = {
        "claude": {
            "fidelity": "native-lifecycle-enforced" if runtime_projection and "claude" in supported else "documented-only",
            "surface": "Claude lifecycle projection declared by primitive-lifecycle" if runtime_projection and "claude" in supported else "contract/documentation only",
        },
        "codex": {
            "fidelity": "structural-advisory",
            "surface": "generated AGENTS/.ai advisory projection unless a governed wrapper is separately signed",
        },
        "opencode": {
            "fidelity": "governed-wrapper-enforced" if contract_id in SIGNED_OPENCODE else "structural-advisory",
            "surface": "OpenCode project plugin cos-primitive-guard.js tool.execute.before/after smoke" if contract_id in SIGNED_OPENCODE else "generated .ai/OpenCode advisory projection; no runtime enforcement claimed",
        },
        "cursor": {"fidelity": "structural-advisory", "surface": "generated Cursor rules/context only"},
        "vscode-copilot": {"fidelity": "structural-advisory", "surface": "generated Copilot instructions only"},
        "shell-ci": {"fidelity": "documented-only", "surface": "evidence commands documented; no generic CI enforcement claimed"},
    }
    return out


def _existing_source(source_ref: str) -> str | None:
    base = source_ref.split("#", 1)[0]
    candidates = [base]
    if base == "scripts/cos-doctor-preserve":
        candidates.append("scripts/cos-doctor-preserve.sh")
    if base == "scripts/cos_primitive_harvester":
        candidates.append("scripts/cos_primitive_harvester.py")
    for candidate in candidates:
        if (ROOT / candidate).exists():
            return candidate
    return None


def promote(limit: int | None = None) -> int:
    registry = yaml.safe_load(REGISTRY.read_text(encoding="utf-8")) or {}
    lifecycle = yaml.safe_load(LIFECYCLE.read_text(encoding="utf-8")) or {}
    contracts: list[dict[str, Any]] = list(registry.get("contracts") or [])
    used_ids = {str(c.get("id")) for c in contracts if c.get("id")}
    covered_sources = {str(c.get("source")) for c in contracts if c.get("source")} | {str(c.get("lifecycle_ref")) for c in contracts if c.get("lifecycle_ref")}
    added = 0

    # First update existing OpenCode rows now covered by the signed smoke.
    for contract in contracts:
        cid = str(contract.get("id") or "")
        if cid in SIGNED_OPENCODE:
            projection = contract.setdefault("projection", {})
            projection.setdefault("opencode", {})
            projection["opencode"] = {
                "fidelity": "governed-wrapper-enforced",
                "surface": "OpenCode project plugin cos-primitive-guard.js tool.execute.before/after smoke",
            }

    for row in lifecycle.get("primitives") or []:
        if not isinstance(row, dict):
            continue
        lifecycle_ref = str(row.get("id") or "").strip()
        source = _existing_source(lifecycle_ref) if lifecycle_ref else None
        if not source or lifecycle_ref in covered_sources:
            continue
        contract_id = _unique_id(lifecycle_ref, used_ids)
        commands = [str(item) for item in row.get("evidence_commands") or []]
        metrics = []
        metric = row.get("metrics_file")
        if metric and str(metric) != "none":
            metrics.append(str(metric))
        action = _preferred_action(row)
        contract = {
            "id": contract_id,
            "family": str(row.get("kind") or "unknown"),
            "source": source,
            "lifecycle_ref": lifecycle_ref,
            "generated_from_lifecycle": True,
            "intent": str(row.get("behavior_evidence") or f"Conservative portable contract for {source}."),
            "trigger": _trigger(row),
            "requires": ["respect_declared_scope", "preserve_privacy", "emit_intervention"],
            "actions": {
                "preferred": action,
                "fallback": "document",
                "reason_codes": ["lifecycle_promoted_contract"],
            },
            "evidence": {
                "metrics": metrics,
                "interventions": [INTERVENTION_LEDGER],
                "proof_tests": _proof_tests(commands),
                "evidence_commands": commands,
            },
            "projection": _projection(contract_id, row),
            "impact": {
                "consumer_fleet": "unknown" if bool(row.get("runtime_projection")) else "none",
                "service_mode": "harness-embedded-only" if bool(row.get("runtime_projection")) else "unsupported",
            },
        }
        contracts.append(contract)
        covered_sources.add(source)
        covered_sources.add(lifecycle_ref)
        added += 1
        if limit is not None and added >= limit:
            break

    registry["contracts"] = contracts
    REGISTRY.write_text(yaml.safe_dump(registry, sort_keys=False, allow_unicode=True, width=120), encoding="utf-8")
    return added


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    added = promote(args.limit)
    print(f"promote-lifecycle-primitives: added={added}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
