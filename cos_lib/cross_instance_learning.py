# SCOPE: both
"""Cross-instance learning runway for Shape-B readiness.

The module implements portable evidence exchange, deterministic registry locks,
Engram bundle import/export, and federation trigger auditing without creating a
distributed system. All risky imports are propose-only.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ConsumerEvidence:
    project: str
    reporter: str
    maintainer_owned: bool
    relationship: str
    profile: str
    duration_days: int
    cos_version: str
    generated_at: str
    incident_evidence: dict[str, Any]
    dx_evidence: dict[str, Any]
    provenance: dict[str, Any]
    independence: dict[str, Any]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return loaded if isinstance(loaded, dict) else {}


def _write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _json_hash(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _read_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
        if limit is not None and len(rows) >= limit:
            break
    return rows


def build_consumer_evidence(
    project_root: Path,
    *,
    project: str,
    reporter: str,
    profile: str,
    duration_days: int,
    cos_version: str,
    maintainer_owned: bool,
    relationship: str,
    cognitive_cost: str,
    producer_type: str = "human",
    producer_identity: str | None = None,
    source_repo: str | None = None,
    machine_id: str | None = None,
    signature: str | None = None,
    same_machine: bool | None = None,
    same_repo: bool | None = None,
) -> dict[str, Any]:
    """Build portable consumer evidence from local metrics and operator input."""

    metrics = project_root / ".cognitive-os" / "metrics"
    blocked_incidents = 0
    for path in metrics.glob("*.jsonl") if metrics.exists() else []:
        for event in _read_jsonl(path):
            if event.get("blocked") is True or event.get("decision") == "blocked" or event.get("exit_code") == 2:
                blocked_incidents += 1

    false_positive_count = 0
    for event in _read_jsonl(metrics / "git-op-blocks.jsonl"):
        if event.get("operator_bypass") or event.get("false_positive"):
            false_positive_count += 1
    ratio = 0.0 if blocked_incidents == 0 else false_positive_count / blocked_incidents

    evidence = ConsumerEvidence(
        project=project,
        reporter=reporter,
        maintainer_owned=maintainer_owned,
        relationship=relationship,
        profile=profile,
        duration_days=duration_days,
        cos_version=cos_version,
        generated_at=_utc_now(),
        incident_evidence={
            "prevented_incidents": blocked_incidents,
            "false_positive_count": false_positive_count,
            "false_positive_ratio": round(ratio, 4),
        },
        dx_evidence={"cognitive_cost": cognitive_cost},
        provenance={
            "producer": {
                "type": producer_type,
                "identity": producer_identity or reporter,
                "repo": source_repo or str(project_root),
                "machine_id": machine_id or "unknown",
                "signature": signature or "",
                "generated_at": _utc_now(),
            }
        },
        independence={
            "maintainer_owned": maintainer_owned,
            "same_machine": same_machine,
            "same_repo": same_repo,
            "self_reported": maintainer_owned or relationship in {"self", "same-maintainer", "internal-self-deployment"},
        },
    )
    return asdict(evidence)


def import_consumer_evidence(manifest_path: Path, report_paths: list[Path]) -> dict[str, Any]:
    """Import consumer evidence into the claim-signature manifest."""

    manifest = _load_yaml(manifest_path)
    manifest.setdefault("schema_version", 1)
    manifest.setdefault(
        "policy",
        "External-help claims require bilateral evidence from a non-maintainer project.",
    )
    reports = manifest.setdefault("reports", [])
    if not isinstance(reports, list):
        reports = []
        manifest["reports"] = reports

    existing_keys = {
        (
            str(item.get("project")),
            str(item.get("reporter")),
            str(item.get("generated_at")),
        )
        for item in reports
        if isinstance(item, dict)
    }
    imported = 0
    skipped = 0
    invalid: list[dict[str, str]] = []
    for path in report_paths:
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            invalid.append({"path": str(path), "reason": str(exc)})
            continue
        required = ("project", "reporter", "profile", "duration_days", "incident_evidence", "dx_evidence")
        missing = [field for field in required if field not in report]
        if missing:
            invalid.append({"path": str(path), "reason": f"missing fields: {', '.join(missing)}"})
            continue
        key = (str(report.get("project")), str(report.get("reporter")), str(report.get("generated_at")))
        if key in existing_keys:
            skipped += 1
            continue
        reports.append(report)
        existing_keys.add(key)
        imported += 1

    _write_yaml(manifest_path, manifest)
    return {
        "status": "pass" if not invalid else "warn",
        "manifest": str(manifest_path),
        "imported": imported,
        "skipped": skipped,
        "invalid": invalid,
        "report_count": len(reports),
    }


def _primitive_lock_entries(project_root: Path) -> list[dict[str, Any]]:
    manifest = _load_yaml(project_root / "manifests" / "primitive-lifecycle.yaml")
    entries = []
    for item in manifest.get("primitives", []) if isinstance(manifest.get("primitives"), list) else []:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        lock_payload = {
            "id": item.get("id"),
            "kind": item.get("kind"),
            "owner_adr": item.get("owner_adr"),
            "lifecycle_state": item.get("lifecycle_state"),
            "maturity": item.get("maturity"),
            "distribution": item.get("distribution"),
            "runtime_projection": item.get("runtime_projection"),
            "projection_targets": item.get("projection_targets", []),
        }
        entries.append({**lock_payload, "sha256": _json_hash(lock_payload)})
    return sorted(entries, key=lambda item: item["id"])


def _skill_lock_entries(project_root: Path) -> list[dict[str, Any]]:
    entries = []
    for skill in sorted((project_root / "skills").glob("*/SKILL.md")):
        rel = str(skill.relative_to(project_root))
        entries.append({"path": rel, "sha256": hashlib.sha256(skill.read_bytes()).hexdigest()})
    return entries


def build_registry_lock(project_root: Path) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "generated_at": _utc_now(),
        "policy": "Deterministic cross-instance lock; drift must be explicit before Shape-B federation.",
        "primitives": _primitive_lock_entries(project_root),
        "skills": _skill_lock_entries(project_root),
    }


def write_registry_locks(project_root: Path) -> dict[str, Any]:
    lock = build_registry_lock(project_root)
    primitive_path = project_root / "manifests" / "agentic-primitive-registry.lock.yaml"
    skill_path = project_root / "skills" / "REGISTRY.lock"
    _write_yaml(primitive_path, {k: v for k, v in lock.items() if k != "skills"})
    _write_yaml(skill_path, {
        "schema_version": lock["schema_version"],
        "generated_at": lock["generated_at"],
        "policy": lock["policy"],
        "skills": lock["skills"],
    })
    return {"primitive_lock": str(primitive_path), "skill_lock": str(skill_path), "primitive_count": len(lock["primitives"]), "skill_count": len(lock["skills"])}


def audit_registry_locks(project_root: Path) -> dict[str, Any]:
    current = build_registry_lock(project_root)
    primitive_path = project_root / "manifests" / "agentic-primitive-registry.lock.yaml"
    skill_path = project_root / "skills" / "REGISTRY.lock"
    primitive_lock = _load_yaml(primitive_path)
    skill_lock = _load_yaml(skill_path)
    findings = []
    if primitive_lock.get("primitives") != current["primitives"]:
        findings.append({"id": "primitive-lock-drift", "severity": "fail", "path": str(primitive_path)})
    if skill_lock.get("skills") != current["skills"]:
        findings.append({"id": "skill-lock-drift", "severity": "fail", "path": str(skill_path)})
    return {
        "status": "pass" if not findings else "fail",
        "findings": findings,
        "primitive_count": len(current["primitives"]),
        "skill_count": len(current["skills"]),
    }


def export_engram_bundle(project_root: Path, *, project: str, max_entries: int = 500) -> dict[str, Any]:
    source = project_root / ".engram" / "exports" / f"{project}.jsonl"
    if not source.exists():
        candidates = sorted((project_root / ".engram" / "exports").glob("*.jsonl"))
        source = candidates[0] if candidates else source
    entries = _read_jsonl(source, limit=max_entries)
    bundle = {
        "schema_version": 1,
        "project": project,
        "source": str(source),
        "generated_at": _utc_now(),
        "mode": "portable-propose-only",
        "entry_count": len(entries),
        "entries": entries,
    }
    target_dir = project_root / ".cognitive-os" / "engram-bundles"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{project}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    target.write_text(json.dumps(bundle, indent=2, sort_keys=True), encoding="utf-8")
    return {"status": "pass", "bundle": str(target), "entry_count": len(entries)}


def propose_engram_import(project_root: Path, bundle_path: Path) -> dict[str, Any]:
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    incoming = bundle.get("entries", [])
    local_topic_keys: set[str] = set()
    for path in (project_root / ".engram" / "exports").glob("*.jsonl"):
        for entry in _read_jsonl(path):
            topic_key = entry.get("topic_key")
            if topic_key:
                local_topic_keys.add(str(topic_key))
    conflicts = []
    imports = []
    for entry in incoming if isinstance(incoming, list) else []:
        topic_key = entry.get("topic_key")
        if topic_key and str(topic_key) in local_topic_keys:
            conflicts.append({"topic_key": str(topic_key), "title": str(entry.get("title", ""))})
        else:
            imports.append({"topic_key": str(topic_key or ""), "title": str(entry.get("title", ""))})
    proposal = {
        "status": "proposed",
        "runtime_effect": "none",
        "bundle": str(bundle_path),
        "incoming_count": len(incoming) if isinstance(incoming, list) else 0,
        "conflict_count": len(conflicts),
        "proposed_import_count": len(imports),
        "conflicts": conflicts[:100],
        "proposed_imports": imports[:100],
        "policy": "Engram bundle imports are propose-only; no memory store is mutated.",
    }
    target_dir = project_root / ".cognitive-os" / "engram-import-proposals"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"engram-import-proposal-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    target.write_text(json.dumps(proposal, indent=2, sort_keys=True), encoding="utf-8")
    return {**proposal, "written_to": str(target)}


def audit_federation_triggers(config_path: Path) -> dict[str, Any]:
    config = _load_yaml(config_path)
    observed = config.get("observed", {}) if isinstance(config.get("observed"), dict) else {}
    triggers = config.get("shape_b_triggers", {}) if isinstance(config.get("shape_b_triggers"), dict) else {}
    fired = []
    for key, threshold in triggers.items():
        value = observed.get(key, 0)
        try:
            if int(value) >= int(threshold):
                fired.append({"id": key, "observed": value, "threshold": threshold})
        except (TypeError, ValueError):
            if value == threshold:
                fired.append({"id": key, "observed": value, "threshold": threshold})
    return {
        "status": "triggered" if fired else "deferred",
        "shape": "Shape B" if fired else "Shape A",
        "fired": fired,
        "policy": "Do not build distributed federation until Shape-B triggers fire.",
    }


def write_shape_b_governance_checklist(target_dir: Path) -> Path:
    """Write a manual Shape-B governance checklist for review drills."""

    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "shape-b-governance-checklist.md"
    target.write_text(
        """# Shape-B Governance Checklist

This checklist is a manual drill artifact. It does not activate Shape B.

## Required before full federation

- [ ] CODEOWNERS for agentic primitive surfaces.
- [ ] ADR quorum policy for governance changes.
- [ ] External owners for silent-failure allowlist classifications.
- [ ] Engram permission scopes for project/personal/imported memories.
- [ ] Promotion authority for `core` and `team`.
- [ ] Warning-budget extension authority.
- [ ] Distributed lock/lease owner and recovery policy.
- [ ] Cross-machine incident review cadence.

## Non-goals

- Do not turn this checklist into a pass condition without actual second
  maintainer participation.
- Do not use this checklist to claim Shape B readiness.
""",
        encoding="utf-8",
    )
    return target
