"""ADR-283 script exposure audit for agentic primitives and maintainer tools."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

SCHEMA_VERSION = "script-exposure-audit/v1"
DEFAULT_LEDGER = Path("docs/reports/primitive-readiness-ledger-scripts-latest.json")
DEFAULT_DISPOSITIONS = Path("manifests/script-exposure-dispositions.yaml")
ALLOWED_NO_SKILL_ROLES = {"lab", "migration-only", "driver-specific"}
COMMAND_ROUTER_CONSUMER_PATHS = {"scripts/cos"}


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



def load_dispositions(path: Path) -> dict[str, dict[str, Any]]:
    """Load manual ADR-283 exposure dispositions keyed by script path."""
    if not path.exists():
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ScriptExposureAuditError(f"script exposure dispositions must be a mapping: {path}")
    dispositions: dict[str, dict[str, Any]] = {}
    for section in ("routes", "scripts"):
        rows = payload.get(section) or []
        if not isinstance(rows, list):
            raise ScriptExposureAuditError(f"script exposure dispositions section must be a list: {section}")
        for row in rows:
            if not isinstance(row, dict) or not row.get("path"):
                continue
            dispositions[str(row["path"])] = row
    return dispositions


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
        if path.startswith("cmd/") or path in COMMAND_ROUTER_CONSUMER_PATHS:
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


def classify_script(row: dict[str, Any], disposition: dict[str, Any] | None = None) -> dict[str, Any]:
    """Classify one scripts-ledger row into ADR-283 exposure priorities."""
    path = str(row.get("path") or "")
    role = str(row.get("role") or "unknown")
    skill_consumers = _as_int(row.get("skill_consumers"))
    total_consumers = _as_int(row.get("total_consumers"))
    channels = _channels(row)
    has_agent_facing_route = channels["skill"] > 0 or channels["hook"] > 0 or channels["router"] > 0
    disposition = disposition or {}
    disposition_resolution = str(disposition.get("resolution") or "")

    if role in {"agentic-primitive", "maintainer-tool"} and skill_consumers == 0 and disposition_resolution == "documented_route":
        priority = "OK"
        finding = "documented-route"
        exposure_class = "OK-documented-route"
        recommendation = "no-action"
        route = str(disposition.get("route") or "documented route")
        rationale = f"Manual ADR-283 disposition records an equivalent route: {route}."
    elif role == "maintainer-tool" and skill_consumers == 0 and disposition_resolution == "internal_backend":
        priority = "OK"
        finding = "maintainer-tool-internal-backend"
        exposure_class = "OK-internal-backend"
        recommendation = "no-action"
        owner = str(disposition.get("owner") or "script orchestration")
        rationale = f"Manual ADR-283 disposition classifies this as an internal backend owned by {owner}."
    elif role == "agentic-primitive" and skill_consumers == 0:
        priority = "P0"
        finding = "agentic-primitive-without-skill-consumer"
        if channels["hook"] > 0 or channels["router"] > 0:
            exposure_class = "P0-route-undocumented"
            recommendation = "document-equivalent-agent-route-or-add-skill-consumer"
            rationale = (
                "This agentic primitive has no skill consumer, but it is reachable through a hook or command router. "
                "Document that equivalent route or add a skill so agents can discover it without rereading ledgers."
            )
        elif channels["script"] > 0 or channels["test"] > 0 or channels["doc"] > 0 or channels["config"] > 0:
            exposure_class = "P0-promotion-candidate"
            recommendation = "add-skill-consumer-or-explicit-demotion"
            rationale = (
                "This agentic primitive is evidenced by docs/tests/config/scripts but has no direct agent-facing route. "
                "Promote it through a skill/router or demote it out of agentic-primitive status."
            )
        else:
            exposure_class = "P0-unrouted"
            recommendation = "wire-skill-hook-router-or-demote"
            rationale = (
                "This agentic primitive has no skill consumer and no observed hook/router/script/doc/test/config consumers. "
                "It is a likely orphan unless deliberately demoted or wired."
            )
    elif role == "maintainer-tool" and total_consumers == 0:
        priority = "P1"
        finding = "maintainer-tool-with-zero-consumers"
        recommendation = "archive-register-or-wire-maintainer-entrypoint"
        exposure_class = "P1-zero-consumers"
        rationale = "Maintainer tools with no observed consumers are likely loose tools unless deliberately registered."
    elif role == "maintainer-tool" and skill_consumers == 0:
        role_source = str(row.get("role_source") or "")
        is_explicit_internal = bool(row.get("lifecycle_id")) or bool(row.get("override_rationale")) or role_source in {"override", "lifecycle"}
        if is_explicit_internal:
            priority = "OK"
            finding = "maintainer-tool-explicitly-classified"
            recommendation = "no-action"
            exposure_class = "OK-classified-maintainer"
            rationale = "This maintainer tool has explicit lifecycle or override classification, so it does not need a skill consumer by default."
        else:
            priority = "P2"
            finding = "maintainer-tool-without-skill-consumer"
            recommendation = "classify-internal-or-add-skill-consumer"
            if channels["hook"] > 0 or channels["router"] > 0:
                exposure_class = "P2-runtime-route-undocumented"
                rationale = "Maintainer tool has hook/router exposure but no explicit internal classification or skill consumer."
            elif channels["script"] > 0:
                exposure_class = "P2-script-orchestrated"
                rationale = "Maintainer tool is orchestrated by scripts but lacks explicit internal classification or skill consumer."
            elif channels["test"] > 0 and channels["doc"] > 0:
                exposure_class = "P2-evidence-only"
                rationale = "Maintainer tool has docs/tests evidence but no runtime route, explicit internal classification, or skill consumer."
            elif channels["test"] > 0:
                exposure_class = "P2-test-only"
                rationale = "Maintainer tool is only test-referenced and needs classification as internal/test fixture or promotion."
            elif channels["doc"] > 0:
                exposure_class = "P2-doc-only"
                rationale = "Maintainer tool is only doc-referenced and needs classification as internal, stale, or promotion."
            elif channels["config"] > 0:
                exposure_class = "P2-config-only"
                rationale = "Maintainer tool is only config-referenced and needs explicit internal classification or promotion."
            else:
                exposure_class = "P2-other-consumer"
                rationale = "Maintainer tool has consumers but no skill consumer or explicit internal classification."
    elif role in ALLOWED_NO_SKILL_ROLES and skill_consumers == 0:
        priority = "P3"
        finding = "role-allows-no-skill-consumer"
        recommendation = "keep-role-exception-if-lifecycle-is-correct"
        exposure_class = "P3-role-exception"
        rationale = "Lab, migration-only, and driver-specific scripts may intentionally have no skill consumer."
    else:
        priority = "OK"
        finding = "exposure-accounted-for"
        recommendation = "no-action"
        exposure_class = "OK-accounted"
        rationale = "Observed exposure is consistent with the declared role."

    return {
        "path": path,
        "role": role,
        "priority": priority,
        "finding": finding,
        "exposure_class": exposure_class,
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
        "role_source": row.get("role_source"),
        "override_rationale": row.get("override_rationale"),
        "wrapper_for": row.get("wrapper_for"),
        "protected_install_surface": bool(row.get("protected_install_surface")),
        "supported_harnesses": row.get("supported_harnesses") or [],
        "evidence": row.get("evidence") or [],
        "consumers": _consumers(row),
        "disposition": disposition or None,
    }


def build_audit(
    project_dir: Path,
    ledger_path: Path | None = None,
    *,
    dispositions_path: Path | None = None,
    limit_per_priority: int | None = None,
) -> dict[str, Any]:
    """Build an ADR-283 script exposure audit report."""
    ledger_file = ledger_path or project_dir / DEFAULT_LEDGER
    if not ledger_file.is_absolute():
        ledger_file = project_dir / ledger_file
    ledger = load_scripts_ledger(ledger_file)
    disposition_file = dispositions_path or project_dir / DEFAULT_DISPOSITIONS
    if not disposition_file.is_absolute():
        disposition_file = project_dir / disposition_file
    dispositions = load_dispositions(disposition_file)
    findings = [
        classify_script(row, dispositions.get(str(row.get("path") or "")))
        for row in ledger["scripts"]
        if isinstance(row, dict)
    ]
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
        "by_exposure_class": {},
    }
    for finding in findings:
        priority = finding["priority"]
        role = finding["role"]
        summary["by_priority"][priority] = summary["by_priority"].get(priority, 0) + 1
        summary["by_role"][role] = summary["by_role"].get(role, 0) + 1
        exposure_class = finding["exposure_class"]
        summary["by_exposure_class"][exposure_class] = summary["by_exposure_class"].get(exposure_class, 0) + 1
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
        "dispositions_path": str(disposition_file.relative_to(project_dir) if disposition_file.exists() and disposition_file.is_relative_to(project_dir) else disposition_file),
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
        f"- P0 unrouted: {summary['by_exposure_class'].get('P0-unrouted', 0)}",
        f"- P0 route undocumented: {summary['by_exposure_class'].get('P0-route-undocumented', 0)}",
        f"- P0 promotion candidates: {summary['by_exposure_class'].get('P0-promotion-candidate', 0)}",
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
                f"- `{row['path']}` — {row['exposure_class']}; finding: {row['finding']}; "
                f"recommendation: `{row['recommendation']}`; channels: {channels}"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
