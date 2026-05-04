#!/usr/bin/env python3
# SCOPE: both
"""Unified Agent Capability Coverage (ACC) pipeline.

The pipeline composes existing Cognitive OS readiness ledgers and coverage tools
into the ACC report shape described by docs/agent-capability-coverage.md.
It is deliberately adapter-based: existing tools remain authoritative for their
slice, while this script normalizes their outputs into capabilities, findings,
score, gate outcome, and persistence metadata.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

MAPPING_STATUSES = {"aligned", "missing", "partial", "stale", "overexposed", "unverified"}
DEFAULT_WEIGHTS = {
    "script": 3,
    "hook": 3,
    "skill": 2,
    "rule": 2,
    "doc_claim": 2,
    "primitive_family": 3,
}
DEFAULT_THRESHOLDS = {
    "reconstruction": {"minimum_acc": 0.50, "minimum_effective_acc": 0.40, "critical_missing_allowed": 0},
    "stabilization": {"minimum_acc": 0.70, "minimum_effective_acc": 0.60, "critical_missing_allowed": 0},
    "production": {"minimum_acc": 0.80, "minimum_effective_acc": 0.75, "critical_missing_allowed": 0},
    "maintenance": {"minimum_acc": 0.85, "minimum_effective_acc": 0.80, "critical_missing_allowed": 0},
}
READINESS_FILES = {
    "scripts": "docs/reports/primitive-readiness-ledger-scripts-latest.json",
    "hooks": "docs/reports/primitive-readiness-ledger-hooks-latest.json",
    "skills": "docs/reports/primitive-readiness-ledger-skills-latest.json",
    "rules": "docs/reports/primitive-readiness-ledger-rules-latest.json",
}
DEFAULT_PROJECTION_HARNESSES = ("claude", "codex")


@dataclass(frozen=True)
class AdapterStatus:
    status: str
    source: str
    command: str | None = None
    summary: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass(frozen=True)
class Capability:
    id: str
    kind: str
    source: dict[str, Any]
    risk: str
    signature: dict[str, Any]
    represented_by: list[dict[str, Any]]
    mapping_status: str
    confidence: float
    consumer_accessibility: str
    lifecycle_status: str
    evidence: list[str]
    weight: int


@dataclass(frozen=True)
class Finding:
    capability_id: str
    severity: str
    status: str
    message: str
    evidence: list[str] = field(default_factory=list)
    next_action: str = ""


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def scrub_project_paths(value: Any, root: Path) -> Any:
    root_text = str(root)
    if isinstance(value, str):
        return value.replace(root_text, "<repo-root>")
    if isinstance(value, list):
        return [scrub_project_paths(item, root) for item in value]
    if isinstance(value, dict):
        return {key: scrub_project_paths(item, root) for key, item in value.items()}
    return value


def run_json_command(root: Path, name: str, command: list[str], timeout: int = 120) -> tuple[AdapterStatus, dict[str, Any] | None]:
    try:
        result = subprocess.run(command, cwd=root, text=True, capture_output=True, check=False, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return AdapterStatus("failed", name, " ".join(command), error=str(exc)), None
    if result.returncode != 0:
        return AdapterStatus("failed", name, " ".join(command), error=(result.stderr or result.stdout)[-1000:]), None
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return AdapterStatus("unverified", name, " ".join(command), error=f"non-json output: {exc}"), None
    summary = data.get("summary", data if isinstance(data, dict) else {})
    return AdapterStatus("ok", name, " ".join(command), summary=scrub_project_paths(summary, root) if isinstance(summary, dict) else {}), data


def phase_for(root: Path) -> str:
    config = root / "cognitive-os.yaml"
    if not config.exists():
        return "reconstruction"
    data = yaml.safe_load(config.read_text(encoding="utf-8")) or {}
    return str(data.get("project", {}).get("phase", "reconstruction"))


def lifecycle_status(row: dict[str, Any]) -> str:
    state = row.get("lifecycle_state")
    if state in {"blocking", "default-on", "advisory"}:
        return "real"
    if state in {"candidate", "sandbox"}:
        return "dormant"
    if state in {"demoted", "archived", "deleted"}:
        return "dormant"
    return "aspirational" if not row.get("lifecycle_id") else "dormant"


def risk_for(row: dict[str, Any], family: str) -> str:
    role = row.get("role", "")
    access = row.get("consumer_accessibility", "")
    if role in {"runtime-safety", "memory-lifecycle"} or access == "projected-consumer-surface":
        return "high"
    if role in {"agentic-primitive", "install-profile-managed", "hook-enforced"} or access.startswith("lifecycle-declared"):
        return "medium"
    if family in {"hooks", "scripts"}:
        return "medium"
    return "low"


def status_for(row: dict[str, Any], family: str, projected: dict[str, dict[str, Any]] | None = None) -> str:
    projected = projected or {}
    if row.get("path") in projected:
        return "aligned"
    access = row.get("consumer_accessibility", "so-local-only")
    role = row.get("role", "")
    if family == "scripts" and role == "agentic-primitive" and not row.get("lifecycle_id"):
        return "missing"
    if access == "projected-consumer-surface":
        return "aligned"
    if access in {"install-profile-managed", "lifecycle-declared-consumer-candidate"}:
        return "partial"
    if access == "lifecycle-declared-maintainer":
        return "aligned"
    if access in {"repo-skill-not-projectable", "skill-referenced-not-projectable", "so-local-only"}:
        return "unverified"
    return "unverified"


def capability_from_readiness(row: dict[str, Any], family: str, projected: dict[str, dict[str, Any]] | None = None) -> Capability:
    projected = projected or {}
    kind = "script" if family == "scripts" else family[:-1]
    projection = projected.get(row.get("path", ""))
    status = status_for(row, family, projected)
    effective_access = "projected-consumer-surface" if projection else row.get("consumer_accessibility", "so-local-only")
    represented = []
    if row.get("role") not in {"archive"}:
        represented.append({
            "kind": kind,
            "id": row.get("path", ""),
            "source": row.get("path", ""),
            "role": row.get("role"),
            "consumer_accessibility": effective_access,
        })
    evidence = list(row.get("evidence", []))
    if row.get("role_source"):
        evidence.append(f"role_source:{row['role_source']}")
    if row.get("lifecycle_state"):
        evidence.append(f"lifecycle_state:{row['lifecycle_state']}")
    if row.get("consumer_accessibility"):
        evidence.append(f"consumer_accessibility:{row['consumer_accessibility']}")
    if projection:
        evidence.append(f"projected_harnesses:{','.join(projection['harnesses'])}")
    return Capability(
        id=f"{kind}:{row.get('path', '')}",
        kind=kind,
        source={"path": row.get("path", ""), "family": family},
        risk=risk_for(row, family),
        signature={
            "role": row.get("role"),
            "supported_harnesses": row.get("supported_harnesses", []),
            "distribution": row.get("distribution"),
        },
        represented_by=represented,
        mapping_status=status,
        confidence={"aligned": 0.9, "partial": 0.68, "missing": 0.82, "stale": 0.8, "overexposed": 0.76, "unverified": 0.45}[status],
        consumer_accessibility=effective_access,
        lifecycle_status=lifecycle_status(row),
        evidence=evidence[:12],
        weight=DEFAULT_WEIGHTS[kind],
    )


def load_readiness_capabilities(root: Path, projected: dict[str, dict[str, Any]] | None = None) -> tuple[dict[str, AdapterStatus], list[Capability], list[Finding]]:
    adapters: dict[str, AdapterStatus] = {}
    capabilities: list[Capability] = []
    findings: list[Finding] = []
    for family, rel in READINESS_FILES.items():
        path = root / rel
        name = f"readiness:{family}"
        if not path.exists():
            adapters[name] = AdapterStatus("failed", rel, error="missing readiness report")
            findings.append(Finding(f"adapter:{family}", "high", "missing", f"Missing readiness report {rel}", [rel], "regenerate readiness ledgers"))
            continue
        data = read_json(path)
        rows = data.get("scripts") if family == "scripts" else data.get("items")
        if not isinstance(rows, list):
            adapters[name] = AdapterStatus("failed", rel, error="missing row list")
            continue
        adapters[name] = AdapterStatus("ok", rel, summary=data.get("summary", {}))
        for row in rows:
            cap = capability_from_readiness(row, family, projected)
            capabilities.append(cap)
            if cap.mapping_status == "missing":
                findings.append(Finding(cap.id, "high", "missing", "Agentic primitive lacks lifecycle metadata", cap.evidence, "add lifecycle metadata or downgrade role"))
            elif cap.mapping_status == "partial" and cap.consumer_accessibility in {"install-profile-managed", "lifecycle-declared-consumer-candidate"}:
                findings.append(Finding(cap.id, "medium", "partial", "Candidate/projectable surface needs consumer projection proof", cap.evidence, "add harness projection proof before promotion"))
            elif cap.mapping_status == "unverified" and cap.consumer_accessibility != "so-local-only":
                findings.append(Finding(cap.id, "medium", "unverified", "Represented locally but not proven projectable", cap.evidence, "add package/profile projection metadata"))
    return adapters, capabilities, findings


def refresh_adapters(root: Path, include_slow: bool) -> dict[str, AdapterStatus]:
    adapters: dict[str, AdapterStatus] = {}
    commands = [
        ("cos_coverage", ["python3", "scripts/cos_coverage.py", "--project-dir", ".", "--json", "--refresh"]),
        ("script_readiness_refresh", ["python3", "scripts/primitive_readiness_ledger.py", "--project-dir", ".", "--fail-low-confidence"]),
        ("family_readiness_hooks", ["python3", "scripts/primitive_family_readiness_ledger.py", "--project-dir", ".", "--target-family", "hooks"]),
        ("family_readiness_skills", ["python3", "scripts/primitive_family_readiness_ledger.py", "--project-dir", ".", "--target-family", "skills"]),
        ("family_readiness_rules", ["python3", "scripts/primitive_family_readiness_ledger.py", "--project-dir", ".", "--target-family", "rules"]),
        ("docs_execution", ["python3", "scripts/docs_execution_audit.py", "--project-dir", "."]),
        ("primitive_gap_snapshot", ["python3", "scripts/primitive_gap_snapshot.py", "--project-root", ".", "--json"]),
    ]
    if include_slow:
        commands.append(("primitive_coverage", ["python3", "scripts/primitive_coverage.py", "--project-dir", ".", "--adapter", "cognitive-os", "--format", "json"]))
    for name, command in commands:
        status, _data = run_json_command(root, name, command, timeout=180 if name == "primitive_coverage" else 90)
        adapters[name] = status
    return adapters


def load_harness_projection(root: Path) -> tuple[AdapterStatus, dict[str, Any]]:
    path = root / "manifests" / "harness-projection.yaml"
    if not path.exists():
        return AdapterStatus("failed", "manifests/harness-projection.yaml", error="missing harness projection manifest"), {"harnesses": []}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    harnesses = data.get("harnesses", [])
    summary = {
        "total": len(harnesses),
        "implemented": sum(1 for item in harnesses if item.get("status") == "implemented"),
        "planned": sum(1 for item in harnesses if item.get("status") == "planned"),
        "unsupported": sum(1 for item in harnesses if item.get("status") == "unsupported"),
    }
    return AdapterStatus("ok", "manifests/harness-projection.yaml", summary=summary), data


def implemented_harness_ids(manifest: dict[str, Any]) -> tuple[str, ...]:
    ids = [
        str(item["id"])
        for item in manifest.get("harnesses", [])
        if item.get("status") == "implemented" and item.get("id")
    ]
    return tuple(ids or DEFAULT_PROJECTION_HARNESSES)


def harness_projection_summary(manifest: dict[str, Any], projection_status: AdapterStatus) -> dict[str, Any]:
    rows = {}
    for item in manifest.get("harnesses", []):
        status = item.get("status", "planned")
        proof_status = "ok" if status == "implemented" and projection_status.status == "ok" else "unverified"
        rows[item["id"]] = {
            "display_name": item.get("display_name", item["id"]),
            "status": status,
            "projection_mode": item.get("projection_mode", "unknown"),
            "proof_status": proof_status,
            "projected_surfaces": item.get("projected_surfaces", []),
            "settings_paths": item.get("settings_paths", []),
            "limitations": item.get("limitations", []),
            "next_action": item.get("next_action", ""),
        }
    return rows


def collect_consumer_projection(root: Path, harnesses: tuple[str, ...] = DEFAULT_PROJECTION_HARNESSES) -> tuple[AdapterStatus, dict[str, dict[str, Any]]]:
    projected: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    counts: dict[str, int] = {}
    for harness in harnesses:
        with tempfile.TemporaryDirectory(prefix=f"cos-acc-projection-{harness}-") as temp:
            temp_root = Path(temp)
            result = subprocess.run(
                ["python3", str(root / "scripts" / "cos_init.py"), "--default", "--harness", harness],
                cwd=temp_root,
                text=True,
                capture_output=True,
                check=False,
                timeout=60,
            )
            if result.returncode != 0:
                errors.append(f"{harness}:{(result.stderr or result.stdout)[-500:]}")
                continue
            harness_count = 0
            for path in (temp_root / ".cognitive-os" / "hooks" / "cos").glob("*.sh"):
                source = f"hooks/{path.name}"
                projected.setdefault(source, {"harnesses": [], "paths": []})
                projected[source]["harnesses"].append(harness)
                projected[source]["paths"].append(path.relative_to(temp_root).as_posix())
                harness_count += 1
            for path in (temp_root / ".cognitive-os" / "skills" / "cos").glob("*/SKILL.md"):
                source = f"skills/{path.parent.name}/SKILL.md"
                projected.setdefault(source, {"harnesses": [], "paths": []})
                projected[source]["harnesses"].append(harness)
                projected[source]["paths"].append(path.relative_to(temp_root).as_posix())
                harness_count += 1
            for path in (temp_root / ".cognitive-os" / "rules" / "cos").glob("*.md"):
                source = f"rules/{path.name}"
                projected.setdefault(source, {"harnesses": [], "paths": []})
                projected[source]["harnesses"].append(harness)
                projected[source]["paths"].append(path.relative_to(temp_root).as_posix())
                harness_count += 1
            counts[harness] = harness_count
    for info in projected.values():
        info["harnesses"] = sorted(set(info["harnesses"]))
        info["paths"] = sorted(set(info["paths"]))
    if errors and not projected:
        return AdapterStatus("failed", "consumer_projection", summary={"harnesses": list(harnesses)}, error="; ".join(errors)), {}
    status = "unverified" if errors else "ok"
    return AdapterStatus(status, "consumer_projection", summary={"projected_primitives": len(projected), "by_harness": counts}, error="; ".join(errors) if errors else None), projected


def existing_tool_findings(root: Path) -> tuple[dict[str, AdapterStatus], list[Finding]]:
    adapters: dict[str, AdapterStatus] = {}
    findings: list[Finding] = []
    docs_report = root / "docs" / "reports" / "docs-execution-latest.json"
    if docs_report.exists():
        data = read_json(docs_report)
        summary = data.get("summary", {})
        adapters["docs_execution_report"] = AdapterStatus("ok", str(docs_report.relative_to(root)), summary=summary)
        for row in data.get("rows", []):
            if row.get("inferred_status") in {"stale", "claimed_done_no_proof", "contradicted"}:
                status = "stale" if row.get("inferred_status") == "stale" else "unverified"
                findings.append(Finding(
                    f"doc_claim:{row.get('path')}:{row.get('line')}",
                    "high" if status == "stale" else "medium",
                    status,
                    row.get("item", "documentation claim needs proof"),
                    row.get("evidence", []),
                    row.get("next_action", "update documentation or add proof"),
                ))
    else:
        adapters["docs_execution_report"] = AdapterStatus("unverified", str(docs_report.relative_to(root)), error="report not generated")
    return adapters, findings


def score(capabilities: list[Capability], findings: list[Finding]) -> dict[str, Any]:
    totals = {status: 0 for status in sorted(MAPPING_STATUSES)}
    for cap in capabilities:
        totals[cap.mapping_status] += cap.weight
    # Docs/gap findings without capability rows still affect stale/missing penalties.
    stale_extra = sum(2 for finding in findings if finding.status == "stale" and not finding.capability_id.startswith(("script:", "hook:", "skill:", "rule:")))
    missing_extra = sum(2 for finding in findings if finding.status == "missing" and not finding.capability_id.startswith(("script:", "hook:", "skill:", "rule:")))
    totals["stale"] += stale_extra
    totals["missing"] += missing_extra
    total_weight = sum(totals.values())
    aligned_weight = totals["aligned"]
    partial_weight = totals["partial"]
    stale_weight = totals["stale"]
    overexposed_weight = totals["overexposed"]
    acc = aligned_weight / total_weight if total_weight else 0.0
    effective = (aligned_weight + 0.5 * partial_weight - stale_weight - overexposed_weight) / total_weight if total_weight else 0.0
    return {
        "acc": round(max(acc, 0.0), 4),
        "acc_effective": round(max(effective, 0.0), 4),
        "total_weight": total_weight,
        "aligned_weight": aligned_weight,
        "partial_weight": partial_weight,
        "missing_weight": totals["missing"],
        "stale_weight": stale_weight,
        "overexposed_weight": overexposed_weight,
        "unverified_weight": totals["unverified"],
        "mapping_weight_by_status": totals,
    }


def gate(summary: dict[str, Any], findings: list[Finding], phase: str, fail_on_warn: bool) -> dict[str, Any]:
    thresholds = DEFAULT_THRESHOLDS.get(phase, DEFAULT_THRESHOLDS["reconstruction"])
    critical_missing = sum(1 for finding in findings if finding.status == "missing" and finding.severity == "critical")
    hard_findings = [finding for finding in findings if finding.status in {"stale", "overexposed"}]
    blocks = []
    warnings = []
    if critical_missing > thresholds["critical_missing_allowed"]:
        blocks.append(f"critical_missing:{critical_missing}")
    if phase in {"production", "maintenance", "stabilization"} and hard_findings:
        blocks.append(f"hard_findings:{len(hard_findings)}")
    if phase in {"production", "maintenance"} and summary["acc_effective"] < thresholds["minimum_effective_acc"]:
        blocks.append(f"acc_effective_below_threshold:{summary['acc_effective']}<{thresholds['minimum_effective_acc']}")
    warn_findings = [finding for finding in findings if finding.status in {"partial", "unverified", "missing"}]
    if warn_findings:
        warnings.append(f"coverage_debt:{len(warn_findings)}")
    if summary["acc"] < thresholds["minimum_acc"]:
        warnings.append(f"acc_below_threshold:{summary['acc']}<{thresholds['minimum_acc']}")
    if summary["acc_effective"] < thresholds["minimum_effective_acc"]:
        warnings.append(f"acc_effective_below_threshold:{summary['acc_effective']}<{thresholds['minimum_effective_acc']}")
    if fail_on_warn and warnings:
        blocks.extend(warnings)
    return {"phase": phase, "status": "block" if blocks else "pass", "blocks": blocks, "warnings": warnings, "thresholds": thresholds}


def append_history(root: Path, payload: dict[str, Any]) -> None:
    history = root / ".cognitive-os" / "metrics" / "acc-pipeline-history.jsonl"
    history.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": payload["generated_at"],
        "source": "acc_pipeline",
        "event_type": "acc_report",
        "payload": {
            "summary": payload["summary"],
            "gate": payload["gate"],
            "capability_count": len(payload["capabilities"]),
            "finding_count": len(payload["findings"]),
        },
    }
    with history.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    gate_data = payload["gate"]
    lines = [
        "# Agent Capability Coverage — Latest",
        "",
        f"Generated: {payload['generated_at']}",
        f"Phase: {gate_data['phase']}",
        f"Gate: {gate_data['status']}",
        "",
        "## Summary",
        "",
        f"- ACC: {summary['acc']:.4f}",
        f"- ACC effective: {summary['acc_effective']:.4f}",
        f"- Total weight: {summary['total_weight']}",
        f"- Capabilities: {len(payload['capabilities'])}",
        f"- Findings: {len(payload['findings'])}",
        f"- Mapping weights: {summary['mapping_weight_by_status']}",
        "",
        "## Adapter Status",
        "",
        "| Adapter | Status | Source | Summary |",
        "|---|---|---|---|",
    ]
    for name, status in sorted(payload["adapters"].items()):
        lines.append(f"| {name} | {status['status']} | `{status.get('source', '')}` | `{json.dumps(status.get('summary', {}), sort_keys=True)[:240]}` |")
    lines += ["", "## Findings", "", "| Capability | Severity | Status | Message | Next action |", "|---|---|---|---|---|"]
    for finding in payload["findings"][:80]:
        lines.append(f"| `{finding['capability_id']}` | {finding['severity']} | {finding['status']} | {finding['message'].replace('|', '/')} | {finding.get('next_action', '').replace('|', '/')} |")
    lines += ["", "## Consumer Accessibility Counts", ""]
    counts: dict[str, int] = {}
    for cap in payload["capabilities"]:
        key = cap.get("consumer_accessibility", "unknown")
        counts[key] = counts.get(key, 0) + 1
    for key, value in sorted(counts.items()):
        lines.append(f"- {key}: {value}")
    lines += ["", "## Persistence", "", f"- Local history: `{payload['persistence']['local_history']}`", f"- Engram: {payload['persistence']['engram']['status']}"]
    return "\n".join(lines) + "\n"


def compact_summary(payload: dict[str, Any], max_findings: int = 8) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for cap in payload["capabilities"]:
        key = cap.get("consumer_accessibility", "unknown")
        counts[key] = counts.get(key, 0) + 1
    finding_counts: dict[str, int] = {}
    for finding in payload["findings"]:
        key = finding["status"]
        finding_counts[key] = finding_counts.get(key, 0) + 1
    top_findings = [
        {
            "capability_id": finding["capability_id"],
            "severity": finding["severity"],
            "status": finding["status"],
            "message": finding["message"][:180],
            "next_action": finding.get("next_action", "")[:180],
        }
        for finding in payload["findings"][:max_findings]
    ]
    return {
        "schema_version": "acc.compact.v1",
        "generated_at": payload["generated_at"],
        "summary": payload["summary"],
        "gate": payload["gate"],
        "capability_count": len(payload["capabilities"]),
        "finding_count": len(payload["findings"]),
        "finding_counts": dict(sorted(finding_counts.items())),
        "consumer_accessibility": dict(sorted(counts.items())),
        "top_findings": top_findings,
        "context_diet": {
            "read_this_first": "docs/acc/latest-compact.md",
            "avoid_loading": ["docs/acc/latest.json", "docs/reports/primitive-readiness-ledger-*.json"],
            "query_json_instead": "Use small Python/jq queries for selected rows; do not cat full JSON reports into agent context.",
        },
    }


def render_compact_markdown(payload: dict[str, Any]) -> str:
    compact = compact_summary(payload)
    summary = compact["summary"]
    gate_data = compact["gate"]
    lines = [
        "# Agent Capability Coverage — Compact",
        "",
        "> Context diet entrypoint. Read this before opening `docs/acc/latest.json`.",
        "",
        f"Generated: {compact['generated_at']}",
        f"Gate: {gate_data['status']} ({gate_data['phase']})",
        f"ACC: {summary['acc']:.4f}",
        f"ACC effective: {summary['acc_effective']:.4f}",
        f"Capabilities: {compact['capability_count']}",
        f"Findings: {compact['finding_count']}",
        "",
        "## Warnings",
        "",
    ]
    for warning in gate_data.get("warnings", []):
        lines.append(f"- {warning}")
    if not gate_data.get("warnings"):
        lines.append("- none")
    lines += [
        "",
        "## Mapping Weights",
        "",
    ]
    for key, value in sorted(summary["mapping_weight_by_status"].items()):
        lines.append(f"- {key}: {value}")
    lines += [
        "",
        "## Consumer Accessibility",
        "",
    ]
    for key, value in compact["consumer_accessibility"].items():
        lines.append(f"- {key}: {value}")
    lines += [
        "",
        "## Top Findings",
        "",
    ]
    for finding in compact["top_findings"]:
        lines.append(f"- `{finding['capability_id']}` [{finding['status']}/{finding['severity']}]: {finding['message']} → {finding['next_action']}")
    if not compact["top_findings"]:
        lines.append("- none")
    lines += [
        "",
        "## Context Diet Rule",
        "",
        "- Do not open full JSON ledgers unless debugging the pipeline itself.",
        "- Prefer this compact file, `python3 scripts/acc_pipeline.py --brief`, or targeted JSON queries.",
        "- Subagents should receive only selected rows/findings, not complete ACC/readiness reports.",
    ]
    return "\n".join(lines) + "\n"


def build_report(root: Path, refresh: bool, include_slow: bool, fail_on_warn: bool) -> dict[str, Any]:
    refresh_statuses = refresh_adapters(root, include_slow) if refresh else {}
    harness_status, harness_manifest = load_harness_projection(root)
    projection_status, projected = collect_consumer_projection(root, implemented_harness_ids(harness_manifest))
    readiness_adapters, capabilities, findings = load_readiness_capabilities(root, projected)
    existing_adapters, existing_findings = existing_tool_findings(root)
    findings.extend(existing_findings)
    adapters = {**refresh_statuses, "harness_projection": harness_status, "consumer_projection": projection_status, **readiness_adapters, **existing_adapters}
    summary = score(capabilities, findings)
    phase = phase_for(root)
    gate_data = gate(summary, findings, phase, fail_on_warn)
    payload = {
        "schema_version": "acc.report.v1",
        "generated_at": utc_now(),
        "project": {"root": "<repo-root>", "phase": phase},
        "weights": DEFAULT_WEIGHTS,
        "mapping_statuses": sorted(MAPPING_STATUSES),
        "summary": summary,
        "gate": gate_data,
        "adapters": {key: asdict(value) for key, value in sorted(adapters.items())},
        "capabilities": [asdict(cap) for cap in capabilities],
        "findings": [asdict(finding) for finding in findings],
        "consumer_projection": scrub_project_paths(projected, root),
        "harness_projection": harness_projection_summary(harness_manifest, projection_status),
        "persistence": {
            "local_history": ".cognitive-os/metrics/acc-pipeline-history.jsonl",
            "engram": {
                "status": "unavailable",
                "reason": "ACC pipeline runs out-of-process; agent must call mem_save when Engram tools are surfaced.",
                "suggested_topic_key": "acc/pipeline/latest",
            },
        },
    }
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the unified Agent Capability Coverage pipeline")
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--refresh", action="store_true", help="Run source adapters before reading reports")
    parser.add_argument("--include-slow", action="store_true", help="Include slower primitive coverage adapter")
    parser.add_argument("--json-out", default="docs/acc/latest.json")
    parser.add_argument("--md-out", default="docs/acc/latest.md")
    parser.add_argument("--compact-out", default="docs/acc/latest-compact.md")
    parser.add_argument("--brief", action="store_true", help="Print compact JSON summary only; do not write reports or append history")
    parser.add_argument("--fail-on-block", action="store_true", help="Exit non-zero when gate status is block")
    parser.add_argument("--fail-on-warn", action="store_true", help="Treat warnings as blocking")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.project_dir).resolve()
    payload = build_report(root, args.refresh, args.include_slow, args.fail_on_warn)
    if args.brief:
        print(json.dumps(compact_summary(payload), sort_keys=True))
        return 0
    write_json(root / args.json_out, payload)
    md_path = root / args.md_out
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    compact_path = root / args.compact_out
    compact_path.parent.mkdir(parents=True, exist_ok=True)
    compact_path.write_text(render_compact_markdown(payload), encoding="utf-8")
    append_history(root, payload)
    print(json.dumps({"json": args.json_out, "markdown": args.md_out, "compact": args.compact_out, "gate": payload["gate"], "summary": payload["summary"]}, sort_keys=True))
    if args.fail_on_block and payload["gate"]["status"] == "block":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
