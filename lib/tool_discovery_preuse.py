"""Tool Discovery Pre-Use Gate for preventing ad-hoc tool reinvention."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

SCHEMA_VERSION = "tool-discovery-preuse-report/v1"
DEFAULT_MANIFEST = Path("manifests/tool-discovery-preuse.yaml")


@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: str
    intent: str
    message: str
    canonical: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "intent": self.intent,
            "message": self.message,
            "canonical": self.canonical,
        }


def load_policy(project_dir: Path) -> dict[str, Any]:
    manifest = project_dir / DEFAULT_MANIFEST
    if not manifest.exists():
        return {"schema_version": "tool-discovery-preuse/v1", "rules": []}
    return yaml.safe_load(manifest.read_text(encoding="utf-8")) or {"rules": []}


def _contains_any(command: str, needles: list[str]) -> bool:
    haystack = command.lower()
    return any(needle.lower() in haystack for needle in needles)


def evaluate_command(command: str, project_dir: Path | None = None) -> dict[str, Any]:
    root = (project_dir or Path.cwd()).resolve()
    policy = load_policy(root)
    findings: list[Finding] = []
    for rule in policy.get("rules", []):
        allow_if = list(rule.get("allow_if_contains") or [])
        if allow_if and _contains_any(command, allow_if):
            continue
        patterns = list(rule.get("command_patterns") or [])
        matched = any(re.search(pattern, command, re.IGNORECASE) for pattern in patterns)
        if not matched:
            continue
        severity = "block" if rule.get("class") == "block" else "warn"
        canonical = list(rule.get("canonical") or [])
        findings.append(
            Finding(
                rule_id=str(rule.get("id", "unknown")),
                severity=severity,
                intent=str(rule.get("intent", "tool use")),
                message=str(rule.get("reason", "Use the canonical Cognitive OS primitive before ad-hoc tooling.")),
                canonical=canonical,
            )
        )
    status = "block" if any(f.severity == "block" for f in findings) else "warn" if findings else "pass"
    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "project_dir": str(root),
        "command": command,
        "findings": [finding.to_dict() for finding in findings],
    }


def format_human(report: dict[str, Any]) -> str:
    lines = [f"tool-discovery-preuse: {report['status']}"]
    for finding in report.get("findings", []):
        lines.append(f"[{finding['severity']}] {finding['rule_id']}: {finding['message']}")
        lines.append("Canonical primitives:")
        lines.extend(f"- {item}" for item in finding.get("canonical", []))
    if not report.get("findings"):
        lines.append("No pre-use discovery findings.")
    return "\n".join(lines)


def dumps_json(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)
