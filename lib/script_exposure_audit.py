"""ADR-283 script exposure audit for agentic primitives and maintainer tools."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "script-exposure-audit/v1"
DEFAULT_LEDGER = Path("docs/reports/primitive-readiness-ledger-scripts-latest.json")
ALLOWED_NO_SKILL_ROLES = {"lab", "migration-only", "driver-specific"}


@dataclass(frozen=True)
class ScriptExposureAuditError(Exception):
    """Raised when the script exposure audit input is invalid."""

    message: str

    def __str__(self) -> str:
        return self.message


def load_scripts_ledger(path: Path) -> dict[str, Any]:
    """Load the primitive readiness scripts ledger."""
    if not path.exists():
        raise ScriptExposureAuditError(f"scripts ledger not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ScriptExposureAuditError(f"scripts ledger must be a JSON object: {path}")
    scripts = payload.get("scripts")
    if not isinstance(scripts, list):
        raise ScriptExposureAuditError(f"scripts ledger has no scripts list: {path}")
    return payload


def _as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _family_count(row: dict[str, Any], family: str) -> int:
    families = row.get("consumer_families") or {}
    if not isinstance(families, dict):
        return 0
    return _as_int(families.get(family))


def _consumers(row: dict[str, Any]) -> list[dict[str, str]]:
    consumers = row.get("consumers") or []
    if not isinstance(consumers, list):
        return []
    normalized: list[dict[str, str]] = []
    for consumer in consumers:
        if isinstance(consumer, dict):
            normalized.append(
                {
                    "family": str(consumer.get("family") or "unknown"),
                    "path": str(consumer.get("path") or ""),
                }
            )
    return normalized


def _router_consumers(row: dict[str, Any]) -> int:
    """Count explicit command/router consumers when visible in the ledger."""
    count = 0
    for consumer in _consumers(row):
        path = consumer["path"]
        if path.startswith("cmd/") or path in {"scripts/cos", "scripts/cos.sh"}:
            count += 1
        elif path.startswith("scripts/cos-") and consumer["family"] == "script":
            count += 1
    return count


def _channels(row: dict[str, Any]) -> dict[str, int]:
    return {
        "skill": _as_int(row.get("skill_consumers")),
        "hook": _family_count(row, "hook"),
        "router": _router_consumers(row),
        "script": _family_count(row, "script"),
        "test": _family_count(row, "test"),
        "doc": _family_count(row, "doc"),
        "config": _family_count(row, "config"),
    }


def classify_script(row: dict[str, Any]) -> dict[str, Any]:
    """Classify one scripts-ledger row into ADR-283 exposure priorities."""
    path = str(row.get("path") or "")
    role = str(row.get("role") or "unknown")
    skill_consumers = _as_int(row.get("skill_consumers"))
    total_consumers = _as_int(row.get("total_consumers"))
    channels = _channels(row)
    has_agent_facing_route = channels["skill"] > 0 or channels["hook"] > 0 or channels["router"] > 0

    if role == "agentic-primitive" and skill_consumers == 0:
        priority = "P0"
        finding = "agentic-primitive-without-skill-consumer"
        recommendation = "add-skill-consumer-or-explicit-demotion"
        if has_agent_facing_route:
            recommendation = "add-skill-consumer-or-document-equivalent-agent-route"
        rationale = (
            "Agentic primitives must be callable through a skill, hook, command router, "
            "or explicitly demoted; otherwise they become scripts nobody reliably calls."
        )
    elif role == "maintainer-tool" and total_consumers == 0:
        priority = "P1"
        finding = "maintainer-tool-with-zero-consumers"
        recommendation = "archive-register-or-wire-maintainer-entrypoint"
        rationale = "Maintainer tools with no observed consumers are likely loose tools unless deliberately registered."
    elif role == "maintainer-tool" and skill_consumers == 0:
        priority = "P2"
        finding = "maintainer-tool-without-skill-consumer"
        recommendation = "classify-internal-or-add-skill-consumer"
        rationale = "Maintainer tools can be internal, but should be classified when only docs/tests/scripts consume them."
    elif role in ALLOWED_NO_SKILL_ROLES and skill_consumers == 0:
        priority = "P3"
        finding = "role-allows-no-skill-consumer"
        recommendation = "keep-role-exception-if-lifecycle-is-correct"
        rationale = "Lab, migration-only, and driver-specific scripts may intentionally have no skill consumer."
    else:
        priority = "OK"
        finding = "exposure-accounted-for"
        recommendation = "no-action"
        rationale = "Observed exposure is consistent with the declared role."

    return {
        "path": path,
        "role": role,
        "priority": priority,
        "finding": finding,
        "recommendation": recommendation,
        "rationale": rationale,
        "channels": channels,
        "has_agent_facing_route": has_agent_facing_route,
        "skill_consumers": skill_consumers,
        "total_consumers": total_consumers,
        "consumer_accessibility": row.get("consumer_accessibility"),
        "consumer_access_next_action": row.get("consumer_access_next_action"),
        "lifecycle_id": row.get("lifecycle_id"),
        "lifecycle_state": row.get("lifecycle_state"),
        "supported_harnesses": row.get("supported_harnesses") or [],
        "evidence": row.get("evidence") or [],
        "consumers": _consumers(row),
    }


def build_audit(project_dir: Path, ledger_path: Path | None = None, *, limit_per_priority: int | None = None) -> dict[str, Any]:
    """Build an ADR-283 script exposure audit report."""
    ledger_file = ledger_path or project_dir / DEFAULT_LEDGER
    if not ledger_file.is_absolute():
        ledger_file = project_dir / ledger_file
    ledger = load_scripts_ledger(ledger_file)
    findings = [classify_script(row) for row in ledger["scripts"] if isinstance(row, dict)]
    priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "OK": 4}
    findings.sort(key=lambda item: (priority_order.get(item["priority"], 99), item["path"]))

    summary: dict[str, Any] = {
        "total_scripts": len(findings),
        "by_priority": {priority: 0 for priority in ["P0", "P1", "P2", "P3", "OK"]},
        "by_role": {},
        "agentic_without_skill": 0,
        "maintainer_zero_consumers": 0,
        "maintainer_without_skill_with_consumers": 0,
        "allowed_no_skill_roles": 0,
    }
    for finding in findings:
        priority = finding["priority"]
        role = finding["role"]
        summary["by_priority"][priority] = summary["by_priority"].get(priority, 0) + 1
        summary["by_role"][role] = summary["by_role"].get(role, 0) + 1
        if finding["finding"] == "agentic-primitive-without-skill-consumer":
            summary["agentic_without_skill"] += 1
        if finding["finding"] == "maintainer-tool-with-zero-consumers":
            summary["maintainer_zero_consumers"] += 1
        if finding["finding"] == "maintainer-tool-without-skill-consumer":
            summary["maintainer_without_skill_with_consumers"] += 1
        if finding["finding"] == "role-allows-no-skill-consumer":
            summary["allowed_no_skill_roles"] += 1

    report_findings = findings
    if limit_per_priority is not None and limit_per_priority >= 0:
        limited: list[dict[str, Any]] = []
        for priority in ["P0", "P1", "P2", "P3", "OK"]:
            limited.extend([f for f in findings if f["priority"] == priority][:limit_per_priority])
        report_findings = limited

    return {
        "schema_version": SCHEMA_VERSION,
        "adr": "ADR-283",
        "status": "warn" if summary["by_priority"].get("P0", 0) else "pass",
        "ledger_path": str(ledger_file.relative_to(project_dir) if ledger_file.is_relative_to(project_dir) else ledger_file),
        "ledger_schema_version": ledger.get("schema_version"),
        "summary": summary,
        "findings": report_findings,
    }


def render_markdown(report: dict[str, Any]) -> str:
    """Render a compact Markdown audit report."""
    summary = report["summary"]
    lines = [
        "# Script Exposure Audit",
        "",
        f"Schema: `{report['schema_version']}`  ",
        f"ADR: `{report['adr']}`  ",
        f"Status: `{report['status']}`  ",
        f"Ledger: `{report['ledger_path']}`",
        "",
        "## Summary",
        "",
        f"- Total scripts: {summary['total_scripts']}",
        f"- P0 agentic primitives without skill consumer: {summary['by_priority'].get('P0', 0)}",
        f"- P1 maintainer tools with zero consumers: {summary['by_priority'].get('P1', 0)}",
        f"- P2 maintainer tools without skill consumer: {summary['by_priority'].get('P2', 0)}",
        f"- P3 allowed no-skill roles: {summary['by_priority'].get('P3', 0)}",
        "",
        "## Findings",
        "",
    ]
    for priority in ["P0", "P1", "P2", "P3"]:
        rows = [row for row in report["findings"] if row["priority"] == priority]
        if not rows:
            continue
        lines.extend([f"### {priority}", ""])
        for row in rows:
            channels = ", ".join(f"{key}={value}" for key, value in row["channels"].items() if value)
            channels = channels or "none"
            lines.append(
                f"- `{row['path']}` — {row['finding']}; recommendation: `{row['recommendation']}`; channels: {channels}"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
