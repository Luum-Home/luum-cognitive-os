# SCOPE: both
"""ADR-234 YAML policy-as-code evaluator for simple tool/action gates."""
from __future__ import annotations

import fnmatch
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

SCHEMA_VERSION = "policy-eval/v1"


@dataclass(frozen=True)
class PolicyDecision:
    schema_version: str
    decision: str
    policy_id: str
    rule_id: str
    reason: str

    def to_dict(self) -> dict[str, str]:
        return {
            "schema_version": self.schema_version,
            "decision": self.decision,
            "policy_id": self.policy_id,
            "rule_id": self.rule_id,
            "reason": self.reason,
        }


def _load_policy_file(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_policies(project_dir: str | Path) -> list[dict[str, Any]]:
    root = Path(project_dir).resolve()
    policy_dir = root / "policies"
    if not policy_dir.is_dir():
        return []
    policies = []
    for path in sorted(policy_dir.glob("*.yaml")):
        policy = _load_policy_file(path)
        if policy.get("schema_version") == SCHEMA_VERSION:
            policies.append(policy)
    return policies


def _matches(value: str, patterns: list[str]) -> bool:
    if not patterns:
        return True
    return any(fnmatch.fnmatch(value, pattern) for pattern in patterns)


def _input_match(action: dict[str, Any], conditions: dict[str, Any]) -> bool:
    for key, expected in conditions.items():
        actual = str(action.get(key) or "")
        if isinstance(expected, list):
            if not _matches(actual, [str(item) for item in expected]):
                return False
        elif str(expected) != actual:
            return False
    return True


def evaluate_action(project_dir: str | Path, action: dict[str, Any]) -> PolicyDecision:
    """Evaluate action against all simple YAML policies.

    Deny/block wins, then ask, then allow; default is allow for Slice A so this
    evaluator can be introduced without silently breaking existing hooks.
    """
    best: PolicyDecision | None = None
    rank = {"block": 3, "deny": 3, "ask": 2, "warn": 1, "allow": 0}
    for policy in load_policies(project_dir):
        policy_id = str(policy.get("id") or "unknown")
        for rule in policy.get("rules", []) or []:
            if not isinstance(rule, dict):
                continue
            if not _matches(str(action.get("tool") or ""), [str(item) for item in rule.get("tools", []) or []]):
                continue
            if not _input_match(action, rule.get("match") or {}):
                continue
            decision = str(rule.get("decision") or "allow")
            candidate = PolicyDecision(
                SCHEMA_VERSION,
                decision,
                policy_id,
                str(rule.get("id") or "unknown"),
                str(rule.get("reason") or "policy matched"),
            )
            if best is None or rank.get(candidate.decision, 0) > rank.get(best.decision, 0):
                best = candidate
    return best or PolicyDecision(SCHEMA_VERSION, "allow", "default", "default-allow", "no policy matched")


def dumps_json(payload: Any) -> str:
    if hasattr(payload, "to_dict"):
        payload = payload.to_dict()
    return json.dumps(payload, indent=2, sort_keys=True)
