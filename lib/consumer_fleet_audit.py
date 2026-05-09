# SCOPE: both
"""Consumer-fleet audit for projects that implement Cognitive OS.

This module joins the existing registry, install metadata, registry-lock audit,
and claim-signature audit into one read-only operational report. It does not run
project tests, mutate consumer repositories, or promote evidence into claims.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from lib.cross_instance_learning import audit_registry_locks

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import cos_claim_signature_audit  # noqa: E402

REQUIRED_TEST_LANES = [
    "python3 -m pytest tests/behavior/test_auto_update.py tests/integration/test_auto_update_safety.py -q",
    "python3 -m pytest tests/behavior/test_consumer_project_projection.py -q",
    "python3 -m pytest tests/unit/test_consumer_improvement_proposals.py tests/unit/test_cross_stack_adoption_truth.py tests/behavior/test_cross_stack_adoption_truth_cli.py -q",
]


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _source_version(source_dir: Path) -> str:
    if (source_dir / ".git").is_dir():
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            cwd=source_dir,
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
        version = result.stdout.strip().removeprefix("v")
        if version:
            return version
    version_file = source_dir / "VERSION"
    if version_file.is_file():
        return version_file.read_text(encoding="utf-8", errors="replace").strip()
    if (source_dir / ".git").is_dir():
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=source_dir,
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
        version = result.stdout.strip()
        if version:
            return version
    return "unknown"


def _default_registry_path() -> Path:
    explicit = os.environ.get("COS_REGISTRY_FILE")
    if explicit:
        return Path(explicit).expanduser()
    return Path.home() / ".cognitive-os" / "installations.json"


def _project_row(entry: dict[str, Any], *, source_version: str) -> dict[str, Any]:
    project_path = Path(str(entry.get("path") or "")).expanduser()
    install_meta_path = project_path / ".cognitive-os" / "install-meta.json"
    install_meta = _load_json_object(install_meta_path)
    exists = project_path.is_dir()
    meta_exists = install_meta_path.is_file()
    registry_version = str(entry.get("version") or "unknown")
    meta_version = str(install_meta.get("version") or "unknown")
    effective_version = meta_version if meta_version != "unknown" else registry_version
    findings: list[dict[str, str]] = []
    if not exists:
        findings.append({"id": "project-missing", "severity": "fail", "message": "Registered project path does not exist."})
    if exists and not meta_exists:
        findings.append({"id": "install-meta-missing", "severity": "warn", "message": "Registered project lacks .cognitive-os/install-meta.json."})
    if source_version != "unknown" and effective_version != "unknown" and effective_version != source_version:
        findings.append({"id": "version-drift", "severity": "warn", "message": "Project version differs from source version."})
    if install_meta.get("source") and entry.get("source") and str(install_meta.get("source")) != str(entry.get("source")):
        findings.append({"id": "source-mismatch", "severity": "warn", "message": "Registry source and install-meta source differ."})
    return {
        "project_name": str(entry.get("project_name") or project_path.name or "unknown"),
        "path": str(project_path),
        "exists": exists,
        "install_meta_exists": meta_exists,
        "registry_mode": str(entry.get("mode") or "unknown"),
        "registry_version": registry_version,
        "install_meta_version": meta_version,
        "effective_version": effective_version,
        "harness": str(install_meta.get("harness") or "unknown"),
        "rules_installed": install_meta.get("rules_installed"),
        "hooks_installed": install_meta.get("hooks_installed"),
        "skills_installed": install_meta.get("skills_installed"),
        "findings": findings,
        "status": "fail" if any(f["severity"] == "fail" for f in findings) else ("warn" if findings else "pass"),
    }


def build_report(source_dir: Path = ROOT, registry_path: Path | None = None) -> dict[str, Any]:
    """Build a read-only report for the COS consumer fleet registered to source_dir."""
    source = source_dir.resolve()
    registry = (registry_path or _default_registry_path()).expanduser()
    registry_doc = _load_json_object(registry)
    installations = registry_doc.get("installations", [])
    if not isinstance(installations, list):
        installations = []
    matching = [item for item in installations if isinstance(item, dict) and str(item.get("source")) == str(source)]
    version = _source_version(source)
    projects = [_project_row(item, source_version=version) for item in matching]
    registry_lock = audit_registry_locks(source)
    claim_signature = cos_claim_signature_audit.build_report(
        source / "manifests" / "primitive-lifecycle.yaml",
        source / "manifests" / "external-adoption-evidence.yaml",
    )
    project_failures = sum(1 for project in projects if project["status"] == "fail")
    project_warnings = sum(1 for project in projects if project["status"] == "warn")
    fleet_findings: list[dict[str, Any]] = []
    if not registry.is_file():
        fleet_findings.append({"id": "registry-missing", "severity": "warn", "message": "COS installations registry does not exist."})
    if registry_lock.get("status") == "fail":
        fleet_findings.append({"id": "registry-lock-drift", "severity": "fail", "message": "Primitive or skill registry locks differ from current source."})
    if claim_signature.get("status") == "fail":
        fleet_findings.append({"id": "claim-signature-failure", "severity": "fail", "message": "Claim-signature audit has a failing evidence condition."})
    elif claim_signature.get("status") == "warn":
        fleet_findings.append({"id": "claim-signature-warning", "severity": "warn", "message": "Claim-signature audit has unsigned or time-bounded evidence warnings."})
    helps = next((claim for claim in claim_signature.get("claims", []) if claim.get("id") == "helps-projects"), None)
    if helps and not helps.get("signed"):
        fleet_findings.append({"id": "helps-projects-unsigned", "severity": "info", "message": "No qualifying external adoption evidence signs the helps-projects claim."})
    status = "fail" if project_failures or any(f["severity"] == "fail" for f in fleet_findings) else ("warn" if project_warnings or any(f["severity"] == "warn" for f in fleet_findings) else "pass")
    return {
        "schema_version": "cos-consumer-fleet-audit.v1",
        "status": status,
        "source_dir": str(source),
        "source_version": version,
        "registry_path": str(registry),
        "summary": {
            "registered_total": len(installations),
            "matching_source": len(matching),
            "project_failures": project_failures,
            "project_warnings": project_warnings,
            "fleet_findings": len(fleet_findings),
        },
        "projects": projects,
        "registry_lock_audit": registry_lock,
        "claim_signature_audit": {
            "status": claim_signature.get("status"),
            "signed_claim_count": claim_signature.get("signed_claim_count"),
            "claim_count": claim_signature.get("claim_count"),
            "helps_projects_signed": bool(helps and helps.get("signed")),
            "findings": claim_signature.get("findings", []),
        },
        "required_test_lanes": REQUIRED_TEST_LANES,
        "auto_update_dry_run_command": "bash scripts/auto-update-projects.sh --dry-run",
        "findings": fleet_findings,
    }


def dumps_json(report: dict[str, Any]) -> str:
    """Return stable JSON for a fleet audit report."""
    return json.dumps(report, indent=2, sort_keys=True)
