#!/usr/bin/env python3
# SCOPE: both
"""Audit AI resource economy governance primitives.

This audit verifies that declared token/cost controls are not merely prose: the
repo must have a manifest, budget config, local fallback doctrine, and projected
hooks/scripts that can enforce or report resource use.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifests" / "ai-resource-economy.yaml"
REQUIRED_LEDGER_FIELDS = {
    "session_id", "agent_id", "task_id", "model", "tokens_in", "tokens_out",
    "estimated_cost_usd", "actual_cost_usd", "retry_count", "tool_calls",
    "reasoning_effort",
}
REQUIRED_PREFLIGHT = {
    "context_tokens", "file_count", "expected_agents", "expected_tests",
    "estimated_cost_usd", "loop_risk",
}
REQUIRED_ACTIONS = {
    "split_task", "use_cheaper_model", "local_search_first",
    "ask_for_confirmation", "plan_without_execution",
}
REQUIRED_HOOKS = [
    "hooks/token-budget-monitor.sh",
    "hooks/context-budget-meter.sh",
    "hooks/context-watchdog.sh",
    "hooks/subagent-budget-enforcer.sh",
    "hooks/rate-limit-detector.sh",
]


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return data if isinstance(data, dict) else {}


def build_report(root: Path = ROOT) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    manifest_path = root / "manifests" / "ai-resource-economy.yaml"
    manifest = _load_yaml(manifest_path) if manifest_path.exists() else {}
    config = _load_yaml(root / "cognitive-os.yaml")

    if not manifest:
        findings.append({"id": "missing-manifest", "path": str(manifest_path), "message": "AI resource economy manifest is missing or empty"})

    ledger_fields = set((manifest.get("ledger") or {}).get("required_fields") or [])
    missing_ledger = sorted(REQUIRED_LEDGER_FIELDS - ledger_fields)
    if missing_ledger:
        findings.append({"id": "ledger-fields", "path": "manifests/ai-resource-economy.yaml", "message": "missing ledger fields: " + ", ".join(missing_ledger)})

    preflight = set((manifest.get("preflight") or {}).get("required_estimates") or [])
    missing_preflight = sorted(REQUIRED_PREFLIGHT - preflight)
    if missing_preflight:
        findings.append({"id": "preflight-estimates", "path": "manifests/ai-resource-economy.yaml", "message": "missing preflight estimates: " + ", ".join(missing_preflight)})

    actions = set((manifest.get("preflight") or {}).get("actions_when_over_budget") or [])
    missing_actions = sorted(REQUIRED_ACTIONS - actions)
    if missing_actions:
        findings.append({"id": "degradation-actions", "path": "manifests/ai-resource-economy.yaml", "message": "missing degradation actions: " + ", ".join(missing_actions)})

    if not config.get("context_budget"):
        findings.append({"id": "context-budget", "path": "cognitive-os.yaml", "message": "context_budget is not declared"})
    if not (((config.get("resources") or {}).get("tokens") or {})):
        findings.append({"id": "resource-token-policy", "path": "cognitive-os.yaml", "message": "resources.tokens policy is not declared"})
    if not ((config.get("efficiency") or {}).get("profiles") or {}):
        findings.append({"id": "efficiency-profiles", "path": "cognitive-os.yaml", "message": "efficiency profiles are not declared"})
    if not ((config.get("sdd") or {}).get("phases") or {}):
        findings.append({"id": "sdd-phase-budget", "path": "cognitive-os.yaml", "message": "SDD phase cost budgets are not declared"})

    for rel in REQUIRED_HOOKS:
        if not (root / rel).exists():
            findings.append({"id": "missing-hook", "path": rel, "message": "required resource governance hook missing"})

    primitive = (manifest.get("language_token_economy") or {}).get("primitive")
    if not primitive or not (root / str(primitive)).exists():
        findings.append({"id": "language-token-economy", "path": str(primitive), "message": "language token economy primitive missing"})
    elif "## Contextual Trigger" not in (root / str(primitive)).read_text(encoding="utf-8"):
        findings.append({"id": "language-token-trigger", "path": str(primitive), "message": "language token economy rule lacks Contextual Trigger"})

    status = "pass" if not findings else "fail"
    return {
        "schema_version": "ai-resource-economy-audit/v1",
        "status": status,
        "finding_count": len(findings),
        "findings": findings,
        "summary": {
            "ledger_field_count": len(ledger_fields),
            "preflight_estimate_count": len(preflight),
            "degradation_action_count": len(actions),
            "required_hook_count": len(REQUIRED_HOOKS),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    report = build_report(ROOT)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"ai-resource-economy-audit: {report['status']} findings={report['finding_count']}")
        for finding in report["findings"]:
            print(f"- {finding['id']} {finding['path']}: {finding['message']}")
    return 1 if args.strict and report["status"] != "pass" else 0


if __name__ == "__main__":
    raise SystemExit(main())
