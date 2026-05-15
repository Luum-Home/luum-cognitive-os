#!/usr/bin/env python3
# SCOPE: os-only
"""Unified Agent Capability Coverage (ACC) pipeline.

The pipeline composes existing Cognitive OS readiness ledgers and coverage tools
into the ACC report shape described by docs/07-Capabilities/root/agent-capability-coverage.md.
It is deliberately adapter-based: existing tools remain authoritative for their
slice, while this script normalizes their outputs into capabilities, findings,
score, gate outcome, and persistence metadata.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import sys
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.script_io import read_json, write_json

import yaml

MAPPING_STATUSES = {"aligned", "missing", "partial", "stale", "overexposed", "unverified"}
DEBT_STATUSES = {"missing", "partial", "stale", "overexposed", "unverified"}
DEFAULT_WEIGHTS = {
    "script": 3,
    "hook": 3,
    "skill": 2,
    "rule": 2,
    "template": 1,
    "doc_claim": 2,
    "primitive_family": 3,
    "proof_drill": 2,
    "proof_claim": 3,
    "primitive_fitness": 2,
    "projection_fidelity": 2,
    "primitive_intervention": 2,
    "codebase_itinerary": 1,
    "authority_write_effects": 3,
    "documentation_truth": 2,
}
DEFAULT_THRESHOLDS = {
    "reconstruction": {"minimum_acc": 0.50, "minimum_effective_acc": 0.40, "critical_missing_allowed": 0},
    "stabilization": {"minimum_acc": 0.70, "minimum_effective_acc": 0.60, "critical_missing_allowed": 0},
    "production": {"minimum_acc": 0.80, "minimum_effective_acc": 0.75, "critical_missing_allowed": 0},
    "maintenance": {"minimum_acc": 0.85, "minimum_effective_acc": 0.80, "critical_missing_allowed": 0},
}
READINESS_FILES = {
    "scripts": "docs/06-Daily/reports/primitive-readiness-ledger-scripts-latest.json",
    "hooks": "docs/06-Daily/reports/primitive-readiness-ledger-hooks-latest.json",
    "skills": "docs/06-Daily/reports/primitive-readiness-ledger-skills-latest.json",
    "rules": "docs/06-Daily/reports/primitive-readiness-ledger-rules-latest.json",
    "templates": "docs/06-Daily/reports/primitive-readiness-ledger-templates-latest.json",
}
DEFAULT_PROJECTION_HARNESSES = ("claude", "codex")
DEFAULT_PROJECTION_PROFILES = ("default", "full")


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
        return AdapterStatus(
            "failed",
            name,
            " ".join(command),
            error=scrub_project_paths(str(exc), root),
        ), None
    if result.returncode != 0:
        error = scrub_project_paths((result.stderr or result.stdout)[-1000:], root)
        return AdapterStatus("failed", name, " ".join(command), error=error), None
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
    override = row.get("_consumer_availability_override", {})
    if override.get("status") in {"maintainer-only", "so-local-only"}:
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
    override = row.get("_consumer_availability_override", {})
    projection_class = projection.get("projection_class") if projection else None
    if projection_class in {"profile-driver", "maintainer-only", "so-local-only"}:
        effective_access = projection_class
    elif override.get("status") in {"maintainer-only", "so-local-only", "shell-ci-candidate", "projectable-needs-driver"}:
        effective_access = override["status"]
    elif projection:
        effective_access = "projected-consumer-surface"
    else:
        effective_access = row.get("consumer_accessibility", "so-local-only")
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
    if override:
        evidence.append(f"availability_override:{override.get('status')}")
        if override.get("_match_kind"):
            evidence.append(f"availability_match:{override['_match_kind']}")
        if override.get("_pattern"):
            evidence.append(f"availability_pattern:{override['_pattern']}")
        if override.get("rationale"):
            evidence.append(f"availability_rationale:{override['rationale'][:120]}")
    if projection:
        if projection.get("harnesses"):
            evidence.append(f"projected_harnesses:{','.join(projection['harnesses'])}")
        if projection.get("profiles"):
            evidence.append(f"projected_profiles:{','.join(projection['profiles'])}")
        if projection.get("projection_class"):
            evidence.append(f"projection_class:{projection['projection_class']}")
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


def load_readiness_capabilities(
    root: Path,
    projected: dict[str, dict[str, Any]] | None = None,
    availability: dict[str, dict[str, Any]] | None = None,
) -> tuple[dict[str, AdapterStatus], list[Capability], list[Finding]]:
    adapters: dict[str, AdapterStatus] = {}
    capabilities: list[Capability] = []
    findings: list[Finding] = []
    availability = availability or {}
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
            row_availability = consumer_availability_for(row.get("path", ""), availability)
            if row_availability:
                row = dict(row)
                row["_consumer_availability_override"] = row_availability
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
        ("family_readiness_templates", ["python3", "scripts/primitive_family_readiness_ledger.py", "--project-dir", ".", "--target-family", "templates"]),
        ("harness_coverage_refresh", ["python3", "scripts/primitive_harness_coverage.py", "--project-dir", "."]),
        ("primitive_projection_fidelity", ["python3", "scripts/primitive_projection_fidelity.py", "--project-dir", "."]),
        ("docs_execution", ["python3", "scripts/docs_execution_audit.py", "--project-dir", "."]),
        ("primitive_duplication", ["python3", "scripts/primitive_duplication_audit.py", "--project-root", "."]),
        ("primitive_gap_snapshot", ["python3", "scripts/primitive_gap_snapshot.py", "--project-root", ".", "--json"]),
        ("primitive_fitness_ledger", ["python3", "scripts/primitive_fitness_ledger.py", "--project-dir", "."]),
        ("primitive_authority_audit", ["python3", "scripts/primitive_authority_audit.py", "--project-dir", ".", "--json"]),
        ("documentation_truth_audit", ["python3", "scripts/documentation_truth_audit.py", "--project-dir", ".", "--update-generated", "--json"]),
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


def load_projection_profiles(root: Path) -> tuple[AdapterStatus, dict[str, Any]]:
    path = root / "manifests" / "primitive-projection-profiles.yaml"
    if not path.exists():
        return AdapterStatus("failed", "manifests/primitive-projection-profiles.yaml", error="missing primitive projection profile manifest"), {"profiles": {}}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    profiles = data.get("profiles", {})
    drivers = data.get("profile_driver_scripts", [])
    summary = {
        "profiles": sorted(profiles),
        "profile_driver_scripts": len(drivers),
        "projection_classes": sorted((data.get("projection_classes") or {}).keys()),
    }
    return AdapterStatus("ok", "manifests/primitive-projection-profiles.yaml", summary=summary), data


def load_consumer_availability(root: Path) -> tuple[AdapterStatus, dict[str, dict[str, Any]]]:
    path = root / "manifests" / "primitive-consumer-availability.yaml"
    if not path.exists():
        return AdapterStatus("unverified", "manifests/primitive-consumer-availability.yaml", error="missing consumer availability manifest"), {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    items = data.get("items", [])
    availability: dict[str, dict[str, Any]] = {}
    statuses: dict[str, int] = {}
    for item in items:
        item_path = item.get("path")
        status = item.get("status", "unknown")
        if not item_path:
            continue
        availability[str(item_path)] = dict(item)
        statuses[str(status)] = statuses.get(str(status), 0) + 1
    patterns = []
    for item in data.get("patterns", []):
        pattern = item.get("pattern")
        if not pattern:
            continue
        patterns.append(dict(item))
        status = item.get("status", "unknown")
        statuses[f"pattern:{status}"] = statuses.get(f"pattern:{status}", 0) + 1
    if patterns:
        availability["__patterns__"] = {"patterns": patterns}
    explicit_count = len([key for key in availability if key != "__patterns__"])
    return (
        AdapterStatus(
            "ok",
            "manifests/primitive-consumer-availability.yaml",
            summary={"items": explicit_count, "patterns": len(patterns), "statuses": dict(sorted(statuses.items()))},
        ),
        availability,
    )


def consumer_availability_for(path: str, availability: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    if path in availability:
        item = dict(availability[path])
        item["_match_kind"] = "exact"
        return item
    for item in availability.get("__patterns__", {}).get("patterns", []):
        pattern = item.get("pattern", "")
        if fnmatch.fnmatch(path, pattern):
            matched = dict(item)
            matched["_match_kind"] = "pattern"
            matched["_pattern"] = pattern
            return matched
    return None


def load_shell_ci_projection(root: Path) -> tuple[AdapterStatus, dict[str, Any]]:
    path = root / "manifests" / "shell-ci-projection.yaml"
    if not path.exists():
        return AdapterStatus("unverified", "manifests/shell-ci-projection.yaml", error="missing shell/CI projection manifest"), {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    summary = {
        "commands": len(data.get("commands", [])),
        "workflows": len(data.get("workflows", [])),
        "profiles": sorted((data.get("profiles") or {}).keys()),
    }
    return AdapterStatus("ok", "manifests/shell-ci-projection.yaml", summary=summary), data


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


def collect_consumer_projection(
    root: Path,
    harnesses: tuple[str, ...] = DEFAULT_PROJECTION_HARNESSES,
    profiles: tuple[str, ...] = DEFAULT_PROJECTION_PROFILES,
    profile_manifest: dict[str, Any] | None = None,
    shell_ci_manifest: dict[str, Any] | None = None,
) -> tuple[AdapterStatus, dict[str, dict[str, Any]]]:
    profile_manifest = profile_manifest or {"profiles": {}}
    shell_ci_manifest = shell_ci_manifest or {"commands": []}
    projected: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    counts: dict[str, int] = {}
    for harness in harnesses:
        for profile in profiles:
            mode = "--full" if profile == "full" else "--default"
            with tempfile.TemporaryDirectory(prefix=f"cos-acc-projection-{harness}-{profile}-") as temp:
                temp_root = Path(temp)
                result = subprocess.run(
                    ["python3", str(root / "scripts" / "cos_init.py"), mode, "--harness", harness],
                    cwd=temp_root,
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=80,
                )
                if result.returncode != 0:
                    errors.append(f"{harness}/{profile}:{(result.stderr or result.stdout)[-500:]}")
                    continue
                harness_profile_count = 0
                for path in (temp_root / ".cognitive-os" / "hooks" / "cos").glob("*.sh"):
                    source = f"hooks/{path.name}"
                    projected.setdefault(source, {"harnesses": [], "profiles": [], "paths": [], "projection_class": "shared"})
                    projected[source]["harnesses"].append(harness)
                    projected[source]["profiles"].append(profile)
                    projected[source]["paths"].append(path.relative_to(temp_root).as_posix())
                    harness_profile_count += 1
                for path in (temp_root / ".cognitive-os" / "skills" / "cos").glob("*/SKILL.md"):
                    source = f"skills/{path.parent.name}/SKILL.md"
                    projected.setdefault(source, {"harnesses": [], "profiles": [], "paths": [], "projection_class": "shared"})
                    projected[source]["harnesses"].append(harness)
                    projected[source]["profiles"].append(profile)
                    projected[source]["paths"].append(path.relative_to(temp_root).as_posix())
                    harness_profile_count += 1
                for path in (temp_root / ".cognitive-os" / "rules" / "cos").glob("*.md"):
                    source = f"rules/{path.name}"
                    projected.setdefault(source, {"harnesses": [], "profiles": [], "paths": [], "projection_class": "shared"})
                    projected[source]["harnesses"].append(harness)
                    projected[source]["profiles"].append(profile)
                    projected[source]["paths"].append(path.relative_to(temp_root).as_posix())
                    harness_profile_count += 1
                shell_result = subprocess.run(
                    ["python3", str(root / "scripts" / "project_shell_ci.py"), "--project-dir", str(temp_root), "--profile", profile, "--json"],
                    cwd=temp_root,
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=60,
                )
                if shell_result.returncode != 0:
                    errors.append(f"{harness}/{profile}/shell-ci:{(shell_result.stderr or shell_result.stdout)[-500:]}")
                else:
                    for item in shell_ci_manifest.get("commands", []):
                        source = item.get("path")
                        if not source:
                            continue
                        path = temp_root / ".cognitive-os" / "scripts" / "cos" / Path(source).name
                        if not path.exists():
                            errors.append(f"{harness}/{profile}/shell-ci:missing {source}")
                            continue
                        projected.setdefault(source, {"harnesses": [], "profiles": [], "paths": [], "projection_class": "shell-ci"})
                        projected[source]["harnesses"].append(harness)
                        projected[source]["profiles"].append(profile)
                        projected[source]["paths"].append(path.relative_to(temp_root).as_posix())
                        harness_profile_count += 1
                counts[f"{harness}/{profile}"] = harness_profile_count
    if not errors:
        for item in profile_manifest.get("profile_driver_scripts", []):
            path = item.get("path")
            if not path:
                continue
            projected.setdefault(path, {"harnesses": [], "profiles": [], "paths": [], "projection_class": item.get("class", "profile-driver")})
            projected[path]["harnesses"].extend(harnesses)
            projected[path]["profiles"].extend(profiles)
            projected[path]["paths"].append(item.get("source_manifest", "manifests/primitive-projection-profiles.yaml"))
    for info in projected.values():
        info["harnesses"] = sorted(set(info["harnesses"]))
        info["profiles"] = sorted(set(info.get("profiles", [])))
        info["paths"] = sorted(set(info["paths"]))
    if errors and not projected:
        return AdapterStatus("failed", "consumer_projection", summary={"harnesses": list(harnesses), "profiles": list(profiles)}, error="; ".join(errors)), {}
    status = "unverified" if errors else "ok"
    return AdapterStatus(
        status,
        "consumer_projection",
        summary={"projected_primitives": len(projected), "by_harness_profile": counts},
        error="; ".join(errors) if errors else None,
    ), projected



def finding_identity(finding: dict[str, Any]) -> str:
    return "|".join([
        str(finding.get("capability_id", "")),
        str(finding.get("status", "")),
        str(finding.get("message", "")),
    ])


def capability_statuses(payload: dict[str, Any]) -> dict[str, str]:
    return {str(cap.get("id")): str(cap.get("mapping_status", "")) for cap in payload.get("capabilities", [])}


def detect_new_debt(
    current: dict[str, Any],
    baseline: dict[str, Any],
    strict_local_defaults: bool = True,
) -> list[dict[str, Any]]:
    """Return debt that appears in current ACC but not in the baseline.

    Strict local-default mode treats newly discovered capabilities that are aligned
    only because they matched a broad consumer-availability pattern as review debt.
    This prevents `scripts/**`/`rules/**`/`skills/**` defaults from silently
    absorbing new surfaces without an explicit lifecycle/projection decision.
    """

    baseline_statuses = capability_statuses(baseline)
    baseline_finding_keys = {finding_identity(finding) for finding in baseline.get("findings", [])}
    new_items: list[dict[str, Any]] = []

    for cap in current.get("capabilities", []):
        cap_id = str(cap.get("id", ""))
        status = str(cap.get("mapping_status", ""))
        baseline_status = baseline_statuses.get(cap_id)
        evidence = [str(item) for item in cap.get("evidence", [])]
        pattern_aligned = (
            strict_local_defaults
            and status == "aligned"
            and baseline_status is None
            and "availability_match:pattern" in evidence
            and any(item.startswith("availability_override:") for item in evidence)
        )
        if status in DEBT_STATUSES and baseline_status != status:
            new_items.append({
                "kind": "capability",
                "id": cap_id,
                "status": status,
                "baseline_status": baseline_status or "absent",
                "reason": "new mapping debt",
            })
        elif pattern_aligned:
            new_items.append({
                "kind": "capability",
                "id": cap_id,
                "status": "unreviewed-local-default",
                "baseline_status": "absent",
                "reason": "new capability matched a broad local-surface default instead of an explicit row or projection proof",
            })

    for finding in current.get("findings", []):
        status = str(finding.get("status", ""))
        key = finding_identity(finding)
        if status in DEBT_STATUSES and key not in baseline_finding_keys:
            new_items.append({
                "kind": "finding",
                "id": str(finding.get("capability_id", "")),
                "status": status,
                "baseline_status": "absent",
                "reason": str(finding.get("message", "new finding debt")),
            })

    return new_items


def apply_fail_new_gate(payload: dict[str, Any], baseline: dict[str, Any], strict_local_defaults: bool = True) -> None:
    new_debt = detect_new_debt(payload, baseline, strict_local_defaults=strict_local_defaults)
    payload["new_debt"] = {
        "status": "block" if new_debt else "pass",
        "strict_local_defaults": strict_local_defaults,
        "count": len(new_debt),
        "items": new_debt[:100],
    }
    if new_debt:
        payload["gate"]["status"] = "block"
        payload["gate"].setdefault("blocks", []).append(f"new_debt:{len(new_debt)}")



def load_proof_drill_claim_map(root: Path, evidence_by_id: dict[str, dict[str, Any]]) -> tuple[AdapterStatus, list[Capability], list[Finding]]:
    path = root / "manifests" / "proof-drill-claim-map.yaml"
    if not path.exists():
        return AdapterStatus("unverified", "manifests/proof-drill-claim-map.yaml", error="missing proof drill claim map"), [], []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    claims = data.get("claims", []) if isinstance(data, dict) else []
    capabilities: list[Capability] = []
    findings: list[Finding] = []
    status_counts: dict[str, int] = {}
    for claim in claims:
        claim_id = str(claim.get("id", ""))
        proof_id = str(claim.get("proof_drill_id", ""))
        evidence_row = evidence_by_id.get(proof_id)
        proof_status = str((evidence_row or {}).get("status", "unverified"))
        status_counts[proof_status] = status_counts.get(proof_status, 0) + 1
        if proof_status == "passed":
            mapping = str(claim.get("status_when_passed", "aligned"))
        elif proof_status == "failed":
            mapping = "stale"
        else:
            mapping = "unverified"
        evidence = [
            f"proof_drill_id:{proof_id}",
            f"proof_drill_status:{proof_status}",
            f"claim_scope:{claim.get('scope', '')}",
        ]
        evidence.extend(str(item) for item in claim.get("docs", []) or [])
        if evidence_row:
            evidence.extend(str(item) for item in evidence_row.get("evidence_artifacts", []) or [])
        capabilities.append(Capability(
            id=f"proof_claim:{claim_id}",
            kind="proof_claim",
            source={"path": str(path.relative_to(root)), "proof_drill_id": proof_id},
            risk=str(claim.get("risk", "medium")),
            signature={"scope": claim.get("scope"), "proof_drill_id": proof_id, "proof_status": proof_status},
            represented_by=[{"kind": "proof_claim", "id": claim_id, "source": proof_id, "role": "claim-to-proof"}],
            mapping_status=mapping if mapping in MAPPING_STATUSES else "unverified",
            confidence=0.94 if mapping == "aligned" else 0.72,
            consumer_accessibility=str(claim.get("consumer_accessibility", "so-local-only")),
            lifecycle_status=str(claim.get("lifecycle_status", "real")),
            evidence=evidence[:12],
            weight=int(claim.get("weight", DEFAULT_WEIGHTS["proof_claim"])),
        ))
        if mapping == "stale":
            findings.append(Finding(
                f"proof_claim:{claim_id}",
                "high",
                "stale",
                "Proof-backed claim has failed evidence",
                evidence[:8],
                "repair the runtime or downgrade the claim",
            ))
        elif mapping == "unverified":
            findings.append(Finding(
                f"proof_claim:{claim_id}",
                "medium",
                "unverified",
                "Proof-backed claim lacks passing evidence",
                evidence[:8],
                "run or record the mapped proof drill",
            ))
    return AdapterStatus(
        "ok",
        str(path.relative_to(root)),
        summary={"claims": len(claims), "proof_status_counts": dict(sorted(status_counts.items()))},
    ), capabilities, findings


def load_proof_drill_evidence(root: Path) -> tuple[AdapterStatus, list[Capability], list[Finding]]:
    path = root / "docs" / "06-Daily" / "reports" / "proof-drill-evidence-latest.json"
    if not path.exists():
        return AdapterStatus("unverified", "docs/06-Daily/reports/proof-drill-evidence-latest.json", error="missing proof drill evidence report"), [], []
    data = read_json(path)
    rows = data.get("rows", []) if isinstance(data, dict) else []
    capabilities: list[Capability] = []
    findings: list[Finding] = []
    status_counts: dict[str, int] = {}
    evidence_by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        proof_id = str(row.get("id", ""))
        evidence_by_id[proof_id] = row
        status = str(row.get("status", "unverified"))
        status_counts[status] = status_counts.get(status, 0) + 1
        mapping = "aligned" if status == "passed" else "stale" if status == "failed" else "unverified"
        evidence = [
            f"proof_drill_status:{status}",
            f"command:{row.get('command', '')}",
            f"source_report:{data.get('source_report', '')}",
        ]
        evidence.extend(str(item) for item in row.get("evidence_artifacts", []))
        capabilities.append(Capability(
            id=f"proof_drill:{proof_id}",
            kind="proof_drill",
            source={"path": data.get("source_report", str(path.relative_to(root))), "proof_drill_id": proof_id},
            risk="medium" if "provider" not in str(row.get("command", "")).lower() else "high",
            signature={"scope": row.get("scope"), "exit_code": row.get("exit_code"), "status": status},
            represented_by=[{"kind": "proof_drill", "id": proof_id, "source": row.get("command", ""), "role": "evidence"}],
            mapping_status=mapping,
            confidence=0.92 if mapping == "aligned" else 0.7,
            consumer_accessibility="so-local-only" if row.get("scope") == "os-self" else "projectable-needs-driver",
            lifecycle_status="real",
            evidence=evidence[:12],
            weight=DEFAULT_WEIGHTS["proof_drill"],
        ))
        if mapping == "stale":
            findings.append(Finding(
                f"proof_drill:{proof_id}",
                "high",
                "stale",
                "Proof drill evidence recorded a failed run",
                evidence[:8],
                "repair the runtime or downgrade the claim",
            ))
    claim_status, claim_capabilities, claim_findings = load_proof_drill_claim_map(root, evidence_by_id)
    capabilities.extend(claim_capabilities)
    findings.extend(claim_findings)
    adapter_summary = {"rows": len(rows), "status_counts": dict(sorted(status_counts.items()))}
    if claim_status.status == "ok":
        adapter_summary["claim_map"] = claim_status.summary
    else:
        adapter_summary["claim_map_status"] = claim_status.status
        if claim_status.error:
            adapter_summary["claim_map_error"] = claim_status.error
    return AdapterStatus(
        "ok",
        str(path.relative_to(root)),
        summary=adapter_summary,
    ), capabilities, findings


def load_primitive_fitness_ledger(root: Path) -> tuple[AdapterStatus, list[Capability], list[Finding]]:
    path = root / "docs" / "06-Daily" / "reports" / "primitive-fitness-ledger-latest.json"
    if not path.exists():
        return AdapterStatus("unverified", "docs/06-Daily/reports/primitive-fitness-ledger-latest.json", error="missing primitive fitness ledger"), [], []
    data = read_json(path)
    rows = data.get("items", []) if isinstance(data, dict) else []
    capabilities: list[Capability] = []
    findings: list[Finding] = []
    status_counts: dict[str, int] = {}
    family_counts: dict[str, int] = {}
    for row in rows:
        primitive_id = str(row.get("primitive_id", ""))
        if not primitive_id:
            continue
        mapping = str(row.get("mapping_status") or "unverified")
        if mapping not in MAPPING_STATUSES:
            mapping = "unverified"
        family = str(row.get("family") or "other")
        verdict = str(row.get("verdict") or "needs_evidence")
        status_counts[mapping] = status_counts.get(mapping, 0) + 1
        family_counts[family] = family_counts.get(family, 0) + 1
        evidence = [
            f"fitness_verdict:{verdict}",
            f"fitness_delta:{row.get('delta')}",
            f"source_report:{row.get('source_report', '')}",
        ]
        evidence.extend(f"missing_signal:{item}" for item in row.get("missing_signals", [])[:4])
        evidence.extend(f"safety_regression:{item}" for item in row.get("safety_regressions", [])[:4])
        capabilities.append(Capability(
            id=f"primitive_fitness:{primitive_id}",
            kind="primitive_fitness",
            source={"path": row.get("source_report", ""), "primitive_id": primitive_id, "family": family},
            risk="high" if row.get("safety_regressions") else "medium",
            signature={
                "family": family,
                "verdict": verdict,
                "delta": row.get("delta"),
                "candidate_score": row.get("candidate_score"),
                "baseline_score": row.get("baseline_score"),
            },
            represented_by=[{"kind": "primitive_fitness", "id": primitive_id, "source": row.get("source_report", ""), "role": "fitness-evidence"}],
            mapping_status=mapping,
            confidence=0.9 if mapping == "aligned" else 0.76 if mapping in {"partial", "stale"} else 0.62,
            consumer_accessibility="so-local-only",
            lifecycle_status="real" if verdict == "promote" else "dormant",
            evidence=evidence[:12],
            weight=DEFAULT_WEIGHTS["primitive_fitness"],
        ))
        if verdict == "reject":
            findings.append(Finding(
                f"primitive_fitness:{primitive_id}",
                "high",
                "stale",
                "Primitive fitness report rejected the candidate",
                evidence[:8],
                "repair the candidate or keep the baseline primitive",
            ))
        elif verdict == "needs_evidence":
            findings.append(Finding(
                f"primitive_fitness:{primitive_id}",
                "medium",
                "unverified",
                "Primitive fitness report lacks enough evidence for promotion",
                evidence[:8],
                "collect core runtime metrics and rerun primitive fitness",
            ))
    summary = data.get("summary", {}) if isinstance(data.get("summary"), dict) else {}
    return AdapterStatus(
        "ok",
        str(path.relative_to(root)),
        summary={
            "reports": len(rows),
            "families": dict(sorted(family_counts.items())),
            "mapping_statuses": dict(sorted(status_counts.items())),
            "verdicts": summary.get("verdicts", {}),
        },
    ), capabilities, findings

def load_harness_coverage(root: Path) -> tuple[AdapterStatus, list[Capability], list[Finding]]:
    path = root / "docs" / "06-Daily" / "reports" / "primitive-harness-coverage-latest.json"
    if not path.exists():
        return AdapterStatus("unverified", "docs/06-Daily/reports/primitive-harness-coverage-latest.json", error="missing harness coverage report"), [], []
    data = read_json(path)
    rows = data.get("items", []) if isinstance(data, dict) else []
    capabilities: list[Capability] = []
    findings: list[Finding] = []
    policy_counts: dict[str, int] = {}
    for row in rows:
        primitive = str(row.get("primitive", ""))
        if not primitive:
            continue
        family = str(row.get("family", "unknown"))
        policy = row.get("gap_policy")
        gap_status = str(row.get("gap_status") or ("partial" if row.get("gap") else "aligned"))
        if gap_status not in MAPPING_STATUSES:
            gap_status = "partial"
        if policy:
            policy_counts[str(policy)] = policy_counts.get(str(policy), 0) + 1
        evidence = [f"harness_coverage:{row.get('coverage', 'none')}"]
        if row.get("scope"):
            evidence.append(f"scope:{row['scope']}")
        if row.get("gap"):
            evidence.append(f"gap:{str(row['gap'])[:160]}")
        if policy:
            evidence.append(f"gap_policy:{policy}")
        capabilities.append(Capability(
            id=f"harness_coverage:{primitive}",
            kind="harness_coverage",
            source={"path": str(path.relative_to(root)), "primitive": primitive, "family": family},
            risk="medium" if row.get("gap_severity") in {"medium", "high"} else "low",
            signature={"scope": row.get("scope"), "coverage": row.get("coverage"), "gap_policy": policy},
            represented_by=[{"kind": "harness_coverage", "id": primitive, "source": primitive, "role": "harness-implementation"}],
            mapping_status=gap_status,
            confidence=0.86 if gap_status == "aligned" else 0.7,
            consumer_accessibility="projected-consumer-surface" if row.get("coverage") not in {"none", None} else "so-local-only",
            lifecycle_status="real",
            evidence=evidence[:12],
            weight=1,
        ))
        if row.get("gap") and gap_status != "aligned":
            findings.append(Finding(
                f"harness_coverage:{primitive}",
                str(row.get("gap_severity") or "medium"),
                gap_status,
                "Harness implementation coverage gap",
                evidence[:8],
                "classify the gap policy or add the missing harness projection/proof",
            ))
    summary = data.get("summary", {}) if isinstance(data.get("summary"), dict) else {}
    summary = dict(summary)
    summary["gap_policies"] = dict(sorted(policy_counts.items()))
    return AdapterStatus("ok", str(path.relative_to(root)), summary=summary), capabilities, findings


def load_projection_fidelity(root: Path) -> tuple[AdapterStatus, list[Capability], list[Finding]]:
    path = root / "docs" / "06-Daily" / "reports" / "primitive-projection-fidelity-latest.json"
    if not path.exists():
        return AdapterStatus("unverified", str(path.relative_to(root)), error="missing projection fidelity report"), [], []
    data = read_json(path)
    capabilities: list[Capability] = []
    findings: list[Finding] = []
    status_counts: dict[str, int] = {}
    for item in data.get("items", []) if isinstance(data, dict) else []:
        contract_id = str(item.get("contract_id") or "")
        if not contract_id:
            continue
        rows = item.get("projection_fidelity") or []
        statuses = {str(row.get("status")) for row in rows if isinstance(row, dict)}
        for status in statuses:
            status_counts[status] = status_counts.get(status, 0) + 1
        mapping_status = "aligned" if statuses <= {"aligned", "pending-runtime-smoke"} else "partial"
        evidence = [f"projection_statuses:{','.join(sorted(statuses))}"]
        capabilities.append(Capability(
            id=f"projection_fidelity:{contract_id}",
            kind="projection_fidelity",
            source={"path": str(path.relative_to(root)), "primitive": contract_id},
            risk="medium",
            signature={"statuses": sorted(statuses), "service_mode": item.get("service_mode_impact")},
            represented_by=[{"kind": "primitive_contract", "id": contract_id, "role": "projection-fidelity"}],
            mapping_status=mapping_status,
            confidence=0.88 if mapping_status == "aligned" else 0.68,
            consumer_accessibility="projected-consumer-surface",
            lifecycle_status="real",
            evidence=evidence,
            weight=DEFAULT_WEIGHTS["projection_fidelity"],
        ))
        gap_rows = [row for row in rows if isinstance(row, dict) and row.get("status") == "gap"]
        if gap_rows:
            findings.append(Finding(
                f"projection_fidelity:{contract_id}",
                "medium",
                "partial",
                "Primitive projection fidelity has harness gaps",
                evidence,
                "repair harness projection or downgrade declared fidelity",
            ))
    return AdapterStatus("ok", str(path.relative_to(root)), summary={"contracts": len(capabilities), "statuses": status_counts}), capabilities, findings


def load_authority_write_effects(root: Path) -> tuple[AdapterStatus, list[Capability], list[Finding]]:
    path = root / "docs" / "06-Daily" / "reports" / "primitive-authority-latest.json"
    if not path.exists():
        return AdapterStatus("unverified", str(path.relative_to(root)), error="missing primitive authority audit report"), [], []
    data = read_json(path)
    summary = data.get("summary", {}) if isinstance(data, dict) else {}
    capabilities: list[Capability] = []
    findings: list[Finding] = []
    for row in data.get("items", []) if isinstance(data, dict) else []:
        primitive = str(row.get("path") or "")
        if not primitive:
            continue
        status = str(row.get("status") or "unverified")
        mapping = "aligned" if status in {"pass", "warn"} else "overexposed" if status == "block" else "unverified"
        evidence = [
            f"authority_mode:{row.get('authority_mode', '')}",
            f"authority_source:{row.get('authority_source', '')}",
            f"scope:{row.get('scope', '')}",
        ]
        evidence.extend(f"write_surface:{surface}" for surface in row.get("detected_write_surfaces", [])[:6])
        capabilities.append(Capability(
            id=f"authority_write_effects:{primitive}",
            kind="authority_write_effects",
            source={"path": str(path.relative_to(root)), "primitive": primitive},
            risk="high" if status == "block" else "medium" if row.get("detected_write_surfaces") else "low",
            signature={"mode": row.get("authority_mode"), "scope": row.get("scope"), "status": status},
            represented_by=[{"kind": "authority_contract", "id": primitive, "role": "write-effects-boundary"}],
            mapping_status=mapping,
            confidence=0.9 if mapping == "aligned" else 0.78,
            consumer_accessibility=str(row.get("consumer_accessibility") or "so-local-only"),
            lifecycle_status="real",
            evidence=evidence[:12],
            weight=DEFAULT_WEIGHTS["authority_write_effects"],
        ))
        if status == "block":
            findings.append(Finding(
                f"authority_write_effects:{primitive}",
                "high",
                "overexposed",
                "Primitive writes outside declared authority",
                evidence[:8],
                "change authority metadata, adjust projection, or fix the write path",
            ))
    for smoke in data.get("dynamic_smokes", []) if isinstance(data, dict) else []:
        smoke_id = str(smoke.get("id") or "unknown")
        status = str(smoke.get("status") or "unverified")
        mapping = "aligned" if status == "pass" else "overexposed" if status == "block" else "unverified"
        evidence = [f"dynamic_smoke:{smoke_id}", f"returncode:{smoke.get('returncode')}"]
        capabilities.append(Capability(
            id=f"authority_write_effects:dynamic:{smoke_id}",
            kind="authority_write_effects",
            source={"path": str(path.relative_to(root)), "smoke": smoke_id},
            risk="high" if status == "block" else "medium",
            signature={"status": status, "unexpected_paths": smoke.get("unexpected_paths", [])},
            represented_by=[{"kind": "dynamic_smoke", "id": smoke_id, "role": "filesystem-delta-proof"}],
            mapping_status=mapping,
            confidence=0.9 if mapping == "aligned" else 0.75,
            consumer_accessibility="projected-consumer-surface" if smoke_id in {"project-shell-ci", "cos-init-codex"} else "so-local-only",
            lifecycle_status="real",
            evidence=evidence,
            weight=DEFAULT_WEIGHTS["authority_write_effects"],
        ))
        if status == "block":
            findings.append(Finding(
                f"authority_write_effects:dynamic:{smoke_id}",
                "high",
                "overexposed",
                "Dynamic authority smoke changed paths outside declared allowlist",
                evidence + [f"unexpected:{p}" for p in smoke.get("unexpected_paths", [])[:4]],
                "tighten the command allowlist or fix the primitive writes",
            ))
    return AdapterStatus("ok", str(path.relative_to(root)), summary=summary), capabilities, findings


def load_documentation_truth(root: Path) -> tuple[AdapterStatus, list[Capability], list[Finding]]:
    path = root / "docs" / "06-Daily" / "reports" / "documentation-truth-latest.json"
    if not path.exists():
        return AdapterStatus("unverified", str(path.relative_to(root)), error="missing documentation truth report"), [], []
    data = read_json(path)
    summary = data.get("summary", {}) if isinstance(data, dict) else {}
    capabilities: list[Capability] = []
    findings: list[Finding] = []
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in data.get("rows", []) if isinstance(data, dict) else []:
        claim = str(row.get("claim_id") or "unknown")
        grouped.setdefault(claim, []).append(row)
    for claim, rows in sorted(grouped.items()):
        block_rows = [row for row in rows if row.get("status") == "block"]
        mapping = "stale" if block_rows else "aligned"
        evidence = [f"checks:{len(rows)}", f"blocks:{len(block_rows)}"]
        evidence.extend(f"block:{row.get('check')}:{row.get('doc') or ''}" for row in block_rows[:5])
        capabilities.append(Capability(
            id=f"documentation_truth:{claim}",
            kind="documentation_truth",
            source={"path": str(path.relative_to(root)), "claim": claim},
            risk="high" if any(row.get("severity") == "high" for row in rows) else "medium",
            signature={"status": mapping, "checks": len(rows), "blocks": len(block_rows)},
            represented_by=[{"kind": "documentation_truth_claim", "id": claim, "role": "stale-prose-boundary"}],
            mapping_status=mapping,
            confidence=0.9 if mapping == "aligned" else 0.82,
            consumer_accessibility="so-local-only",
            lifecycle_status="real",
            evidence=evidence[:10],
            weight=DEFAULT_WEIGHTS["documentation_truth"],
        ))
        for row in block_rows:
            findings.append(Finding(
                f"documentation_truth:{claim}",
                str(row.get("severity") or "medium"),
                "stale",
                str(row.get("message") or "Documentation truth claim is stale or contradicted"),
                [str(item) for item in row.get("evidence", [])[:8]],
                str(row.get("next_action") or "update docs, source report, or truth manifest"),
            ))
    return AdapterStatus("ok", str(path.relative_to(root)), summary=summary), capabilities, findings


def load_primitive_interventions(root: Path) -> tuple[AdapterStatus, list[Capability], list[Finding]]:
    path = root / ".cognitive-os" / "metrics" / "primitive-interventions.jsonl"
    if not path.exists():
        return AdapterStatus("unverified", str(path.relative_to(root)), error="missing primitive intervention ledger"), [], []
    primitive_counts: dict[str, int] = {}
    action_counts: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        primitive_id = str(row.get("primitive_id") or "")
        if not primitive_id:
            continue
        primitive_counts[primitive_id] = primitive_counts.get(primitive_id, 0) + 1
        action = str(row.get("action_kind") or "unknown")
        action_counts[action] = action_counts.get(action, 0) + 1
    capabilities = [
        Capability(
            id=f"primitive_intervention:{primitive_id}",
            kind="primitive_intervention",
            source={"path": str(path.relative_to(root)), "primitive": primitive_id},
            risk="medium",
            signature={"rows": count},
            represented_by=[{"kind": "runtime_evidence", "id": primitive_id, "role": "observable-self-use"}],
            mapping_status="aligned",
            confidence=0.82,
            consumer_accessibility="runtime-evidence",
            lifecycle_status="real",
            evidence=[f"intervention_rows:{count}"],
            weight=DEFAULT_WEIGHTS["primitive_intervention"],
        )
        for primitive_id, count in sorted(primitive_counts.items())
    ]
    return AdapterStatus("ok", str(path.relative_to(root)), summary={"primitive_count": len(primitive_counts), "actions": action_counts}), capabilities, []


def load_codebase_itinerary(root: Path) -> tuple[AdapterStatus, list[Capability], list[Finding]]:
    path = root / ".cognitive-os" / "metrics" / "codebase-itinerary.jsonl"
    if not path.exists():
        return AdapterStatus("unverified", str(path.relative_to(root)), error="missing codebase itinerary ledger"), [], []
    tool_counts: dict[str, int] = {}
    category_counts: dict[str, int] = {}
    session_counts: dict[str, int] = {}
    total = 0
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("schema_version") not in {"codebase-itinerary.v1", "tool-sequence.v1", None}:
            continue
        total += 1
        tool = str(row.get("tool") or row.get("tool_name") or "unknown")
        category = str(row.get("category") or row.get("target_category") or row.get("action_kind") or "unknown")
        session_id = str(row.get("session_id") or "unknown")
        tool_counts[tool] = tool_counts.get(tool, 0) + 1
        category_counts[category] = category_counts.get(category, 0) + 1
        session_counts[session_id] = session_counts.get(session_id, 0) + 1
    capabilities: list[Capability] = []
    for tool, count in sorted(tool_counts.items()):
        capabilities.append(Capability(
            id=f"codebase_itinerary:{tool}",
            kind="codebase_itinerary",
            source={"path": str(path.relative_to(root)), "tool": tool},
            risk="low",
            signature={"rows": count, "categories": category_counts},
            represented_by=[{"kind": "runtime_evidence", "id": tool, "role": "codebase-itinerary"}],
            mapping_status="aligned",
            confidence=0.78,
            consumer_accessibility="runtime-evidence",
            lifecycle_status="real",
            evidence=[f"itinerary_rows:{count}"],
            weight=DEFAULT_WEIGHTS["codebase_itinerary"],
        ))
    return AdapterStatus(
        "ok",
        str(path.relative_to(root)),
        summary={"rows": total, "tools": tool_counts, "categories": category_counts, "sessions": len(session_counts)},
    ), capabilities, []


def existing_tool_findings(root: Path) -> tuple[dict[str, AdapterStatus], list[Finding]]:
    adapters: dict[str, AdapterStatus] = {}
    findings: list[Finding] = []
    docs_report = root / "docs" / "06-Daily" / "reports" / "docs-execution-latest.json"
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
        f"- Primitive fitness reports: {payload['adapters'].get('primitive_fitness_ledger', {}).get('summary', {}).get('reports', 0)}",
        f"- New debt gate: {payload.get('new_debt', {}).get('status', 'not_evaluated')} ({payload.get('new_debt', {}).get('count', 0)})",
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
    lines += ["", "## New Debt", "", "| Capability | Status | Reason |", "|---|---|---|"]
    for item in payload.get("new_debt", {}).get("items", [])[:40]:
        lines.append(f"| `{item.get('id', '')}` | {item.get('status', '')} | {str(item.get('reason', '')).replace('|', '/')} |")
    if not payload.get("new_debt", {}).get("items"):
        lines.append("| none | pass | no new debt |")
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
        "new_debt": payload.get("new_debt", {"status": "not_evaluated", "count": 0, "items": []}),
        "context_diet": {
            "read_this_first": "docs/07-Capabilities/acc/latest-compact.md",
            "avoid_loading": ["docs/07-Capabilities/acc/latest.json", "docs/06-Daily/reports/primitive-readiness-ledger-*.json"],
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
        "> Context diet entrypoint. Read this before opening `docs/07-Capabilities/acc/latest.json`.",
        "",
        f"Generated: {compact['generated_at']}",
        f"Gate: {gate_data['status']} ({gate_data['phase']})",
        f"ACC: {summary['acc']:.4f}",
        f"ACC effective: {summary['acc_effective']:.4f}",
        f"Capabilities: {compact['capability_count']}",
        f"Findings: {compact['finding_count']}",
        f"New debt gate: {compact['new_debt'].get('status', 'not_evaluated')} ({compact['new_debt'].get('count', 0)})",
        f"Primitive fitness reports: {payload['adapters'].get('primitive_fitness_ledger', {}).get('summary', {}).get('reports', 0)}",
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
        "## New Debt",
        "",
    ]
    for item in compact["new_debt"].get("items", [])[:8]:
        lines.append(f"- `{item.get('id')}` [{item.get('status')}]: {item.get('reason')}")
    if not compact["new_debt"].get("items"):
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
    profile_status, profile_manifest = load_projection_profiles(root)
    availability_status, availability = load_consumer_availability(root)
    shell_ci_status, shell_ci_manifest = load_shell_ci_projection(root)
    projection_status, projected = collect_consumer_projection(
        root,
        implemented_harness_ids(harness_manifest),
        DEFAULT_PROJECTION_PROFILES,
        profile_manifest,
        shell_ci_manifest,
    )
    readiness_adapters, capabilities, findings = load_readiness_capabilities(root, projected, availability)
    proof_status, proof_capabilities, proof_findings = load_proof_drill_evidence(root)
    capabilities.extend(proof_capabilities)
    findings.extend(proof_findings)
    fitness_status, fitness_capabilities, fitness_findings = load_primitive_fitness_ledger(root)
    capabilities.extend(fitness_capabilities)
    findings.extend(fitness_findings)
    harness_coverage_status, harness_coverage_capabilities, harness_coverage_findings = load_harness_coverage(root)
    capabilities.extend(harness_coverage_capabilities)
    findings.extend(harness_coverage_findings)
    projection_fidelity_status, projection_fidelity_capabilities, projection_fidelity_findings = load_projection_fidelity(root)
    capabilities.extend(projection_fidelity_capabilities)
    findings.extend(projection_fidelity_findings)
    authority_status, authority_capabilities, authority_findings = load_authority_write_effects(root)
    capabilities.extend(authority_capabilities)
    findings.extend(authority_findings)
    documentation_truth_status, documentation_truth_capabilities, documentation_truth_findings = load_documentation_truth(root)
    capabilities.extend(documentation_truth_capabilities)
    findings.extend(documentation_truth_findings)
    intervention_status, intervention_capabilities, intervention_findings = load_primitive_interventions(root)
    capabilities.extend(intervention_capabilities)
    findings.extend(intervention_findings)
    itinerary_status, itinerary_capabilities, itinerary_findings = load_codebase_itinerary(root)
    capabilities.extend(itinerary_capabilities)
    findings.extend(itinerary_findings)
    existing_adapters, existing_findings = existing_tool_findings(root)
    findings.extend(existing_findings)
    adapters = {
        **refresh_statuses,
        "harness_projection": harness_status,
        "projection_profiles": profile_status,
        "consumer_availability": availability_status,
        "shell_ci_projection": shell_ci_status,
        "consumer_projection": projection_status,
        "proof_drill_evidence": proof_status,
        "primitive_fitness_ledger": fitness_status,
        "harness_coverage": harness_coverage_status,
        "projection_fidelity": projection_fidelity_status,
        "authority_write_effects": authority_status,
        "documentation_truth": documentation_truth_status,
        "primitive_interventions": intervention_status,
        "codebase_itinerary": itinerary_status,
        **readiness_adapters,
        **existing_adapters,
    }
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
        "projection_profiles": scrub_project_paths(profile_manifest, root),
        "new_debt": {"status": "not_evaluated", "strict_local_defaults": None, "count": 0, "items": []},
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
    parser.add_argument("--json-out", default="docs/07-Capabilities/acc/latest.json")
    parser.add_argument("--md-out", default="docs/07-Capabilities/acc/latest.md")
    parser.add_argument("--compact-out", default="docs/07-Capabilities/acc/latest-compact.md")
    parser.add_argument("--brief", action="store_true", help="Print compact JSON summary only; do not write reports or append history")
    parser.add_argument("--fail-on-block", action="store_true", help="Exit non-zero when gate status is block")
    parser.add_argument("--fail-on-warn", action="store_true", help="Treat warnings as blocking")
    parser.add_argument("--fail-new", action="store_true", help="Block when current ACC introduces new debt versus --baseline")
    parser.add_argument("--baseline", default="docs/07-Capabilities/acc/latest.json", help="Baseline ACC JSON used by --fail-new")
    parser.add_argument("--allow-new-local-defaults", action="store_true", help="With --fail-new, do not block new capabilities that only match broad local-default patterns")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.project_dir).resolve()
    payload = build_report(root, args.refresh, args.include_slow, args.fail_on_warn)
    baseline_missing = False
    if args.fail_new:
        baseline_path = (root / args.baseline).resolve() if not Path(args.baseline).is_absolute() else Path(args.baseline)
        if not baseline_path.exists():
            payload["new_debt"] = {"status": "block", "strict_local_defaults": not args.allow_new_local_defaults, "count": 1, "items": [{"kind": "baseline", "id": str(baseline_path), "status": "missing", "baseline_status": "absent", "reason": "--fail-new requires an existing ACC baseline"}]}
            payload["gate"]["status"] = "block"
            payload["gate"].setdefault("blocks", []).append("missing_fail_new_baseline")
            baseline_missing = True
        else:
            apply_fail_new_gate(payload, read_json(baseline_path), strict_local_defaults=not args.allow_new_local_defaults)
    if args.brief:
        print(json.dumps(compact_summary(payload), sort_keys=True))
        if args.fail_new and (baseline_missing or payload.get("new_debt", {}).get("status") == "block"):
            return 1
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
    if args.fail_new and (baseline_missing or payload.get("new_debt", {}).get("status") == "block"):
        return 1
    if args.fail_on_block and payload["gate"]["status"] == "block":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
