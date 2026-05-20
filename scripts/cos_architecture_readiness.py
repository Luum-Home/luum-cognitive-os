#!/usr/bin/env python3
# SCOPE: os-only
"""Architecture readiness report for Cognitive OS governance.

This command converts external architecture review findings into a concrete gate report. It is not a
marketing score; warnings are intentionally visible so governance can be demoted,
wired, or reduced when it does not earn its cost.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import active_primitive_index
import yaml
import cos_governance_roi
import primitive_lifecycle
import runtime_hook_reality
import silent_failure_audit
import session_start_budget
import lab_first_promotion_gate
import cos_tier_claim_audit
import cos_manifest_tier_claim_audit
import cos_demotion_loop_audit
import cos_preamble_budget
import python_stdin_antipattern_audit

REPO_ROOT = SCRIPT_DIR.parents[0]
REQUIRED_RUNTIME_PRIMITIVES = {
    "branch_writer_lease": ["scripts/cos_branch_lease.py", "scripts/cos-branch-lease"],
    "headless_safe_mode": ["scripts/cos_headless_safe_mode.py", "scripts/cos-headless-safe-mode"],
    "headless_publication": ["scripts/cos_headless_publication.py", "scripts/cos-headless-publication"],
    "headless_run_task": ["scripts/cos_run_task.py", "scripts/cos-run-task"],
}
PHASE2_WIRING_PROBES = [
    {
        "id": "branch-lease-prelaunch-wiring",
        "path": "scripts/cos-governed-agent.sh",
        "needles": ["cos_branch_lease.py", "acquire_branch_lease", "release_branch_lease"],
        "severity": "warn",
        "message": "branch writer lease exists but is not yet enforced by agent prelaunch/governed-agent flow",
        "phase": "Phase 2",
    },
    {
        "id": "headless-safe-mode-run-task-wiring",
        "path": "scripts/cos_run_task.py",
        "needles": ["read_state", "admits_new_tasks", "OUTCOME_DIR"],
        "severity": "warn",
        "message": "headless safe-mode exists but is not yet wired into cos run-task / worker admission",
        "phase": "Phase 2",
    },
    {
        "id": "headless-publication-flow-wiring",
        "path": "scripts/cos_run_task.py",
        "needles": ["check_publication_policy", "publication_target", "publication_decision.allowed"],
        "severity": "warn",
        "message": "protected-publication checker exists but is not yet wired into real headless publication orchestration",
        "phase": "Phase 2",
    },
]


STALE_MODEL_NAMING_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"cos[_-]opus[_-]readiness",
        r"Opus Objection",
        r"Opus critique",
        r"COS Opus",
        r"claude-opus-[0-9]",
        r"claude-sonnet-[0-9]",
        r"claude-haiku-[0-9]",
    )
]
PRODUCT_FACING_DOCS = [
    "README.md",
    "docs/00-MOCs/entrypoints/README.md",
    "docs/08-References/business",
    ".cognitive-os/plans/architecture",
]
REQUIRED_MATURITY_LABELS = {
    "hooks/trust-score-validator.sh",
    "hooks/blast-radius.sh",
}
DISCOVERY_VISIBLE_WARN_THRESHOLD = 12
DISCOVERY_VISIBLE_FAIL_THRESHOLD = 25



@dataclass(frozen=True)
class Check:
    id: str
    status: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)


def run_git_stash_list(root: Path) -> list[str]:
    result = subprocess.run(["git", "stash", "list"], cwd=root, text=True, capture_output=True, check=False, timeout=60)
    if result.returncode != 0:
        return [f"<error:{result.stderr.strip()}>"]
    return [line for line in result.stdout.splitlines() if line.strip()]


def check_repo_hygiene(root: Path) -> Check:
    stashes = run_git_stash_list(root)
    markers = sorted(str(path.relative_to(root)) for path in (root / ".cognitive-os" / "runtime").glob("pre-agent-snapshot-*.json"))
    status = "pass" if not stashes and not markers else "fail"
    return Check(
        id="repo-hygiene",
        status=status,
        message="no stashes or pre-agent snapshot markers" if status == "pass" else "stash/snapshot residue can hide or lose WIP",
        details={"stash_count": len(stashes), "marker_count": len(markers), "markers": markers},
    )


def check_adoption_tiers(root: Path) -> Check:
    result = subprocess.run(
        ["python3", "scripts/render_adoption_tiers.py", "--check"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,  # timeout per ADR-278 (default - review)
    )
    return Check(
        id="adoption-tiers-derived",
        status="pass" if result.returncode == 0 else "fail",
        message="adoption tiers are derived and in sync" if result.returncode == 0 else "adoption tiers doc is stale",
        details={"stdout": result.stdout.strip(), "stderr": result.stderr.strip()},
    )


def check_lifecycle_manifest(root: Path) -> Check:
    report = primitive_lifecycle.build_report(root / "manifests" / "primitive-lifecycle.yaml")
    return Check(
        id="primitive-lifecycle-manifest",
        status="pass" if report["valid"] else "fail",
        message="primitive lifecycle manifest is valid" if report["valid"] else "primitive lifecycle manifest has findings",
        details=report,
    )


def check_active_surface(root: Path) -> Check:
    try:
        index = active_primitive_index.build_index(root / "manifests" / "primitive-lifecycle.yaml")
    except active_primitive_index.ActivePrimitiveIndexError as exc:
        return Check(
            id="active-primitive-surface",
            status="fail",
            message="active primitive index could not be built",
            details={"error": str(exc)},
        )
    summary = index["summary"]
    status = summary["status"]
    coverage = summary["runtime_coverage"]
    return Check(
        id="active-primitive-surface",
        status=status,
        message=(
            "active primitive surface and runtime coverage are within DX thresholds"
            if status == "pass"
            else "active primitive surface or lifecycle/runtime coverage exceeds DX threshold"
        ),
        details={
            "counts_by_tier": summary["counts_by_tier"],
            "active_counts_by_tier": summary["active_counts_by_tier"],
            "default_visible_counts_by_tier": summary["default_visible_counts_by_tier"],
            "active_surface_count": summary["active_surface_count"],
            "runtime_active_surface_count": summary.get("runtime_active_surface_count"),
            "default_visible_count": summary["default_visible_count"],
            "runtime_coverage": coverage,
            "thresholds": summary["thresholds"],
            "findings": summary["findings"],
        },
    )


def discovery_overload_signal(active_surface_check: Check) -> dict[str, Any]:
    """Return the default-discovery overload signal for readiness JSON."""
    summary = active_surface_check.details
    current = int(summary.get("default_visible_count") or 0)
    thresholds = summary.get("thresholds") if isinstance(summary.get("thresholds"), dict) else {}
    fail_threshold = int(thresholds.get("default_visible_fail") or DISCOVERY_VISIBLE_FAIL_THRESHOLD)
    warn_threshold = int(thresholds.get("default_visible_warn") or DISCOVERY_VISIBLE_WARN_THRESHOLD)
    overloaded = current > fail_threshold
    near_limit = current > warn_threshold
    return {
        "overloaded": overloaded,
        "near_limit": near_limit,
        "current_count": current,
        "threshold": fail_threshold,
        "warn_threshold": warn_threshold,
        "recommended_action": (
            "demote/archive low-value default-visible primitives or move them behind maintainer/lab opt-in"
            if overloaded
            else (
                "review default-visible primitives before adding more core/team discovery surface"
                if near_limit
                else "no action required"
            )
        ),
    }


def token_context_estimate(root: Path) -> dict[str, Any]:
    """Estimate governance context tax from default-loaded rule/docs files.

    This is intentionally explicit when approximate: agents need to know whether
    the number is measured, heuristic, or unavailable instead of treating a
    missing estimate as zero cost.
    """
    candidates = [
        root / "rules" / "RULES-COMPACT.md",
        root / "AGENTS.md",
        root / ".claude" / "rules" / "RULES-COMPACT.md",
    ]
    files: list[dict[str, Any]] = []
    total_chars = 0
    for path in candidates:
        if not path.exists() or path.is_dir():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
        total_chars += len(text)
        files.append({"path": rel, "chars": len(text), "estimated_tokens": round(len(text) / 4)})
    if not files:
        return {
            "estimate_unavailable": True,
            "reason": "no default governance context files found",
        }
    return {
        "estimate_unavailable": False,
        "method": "heuristic_chars_div_4",
        "estimated_tokens": round(total_chars / 4),
        "estimated_chars": total_chars,
        "files": files,
    }


def active_safety_layer_summary(root: Path, active_surface_check: Check) -> dict[str, Any]:
    phase_policy = cos_governance_roi.phase_policy_for(cos_governance_roi.read_project_phase(root))
    details = active_surface_check.details
    return {
        "phase": phase_policy["phase"],
        "active_profile": "core/team default discovery; maintainer and lab are opt-in",
        "hard_blocking_guards": sorted(phase_policy["block"]),
        "advisory_guards": sorted(phase_policy["advisory"]),
        "maintainer_opt_ins": {
            "active_count": (details.get("active_counts_by_tier") or {}).get("maintainer", 0),
            "command": "scripts/cos-active-primitive-index --tier maintainer --list",
        },
        "lab_opt_ins": {
            "recoverable_count": (details.get("counts_by_tier") or {}).get("lab", 0),
            "command": "scripts/cos-active-primitive-index --tier lab --list",
        },
    }



def check_core_preamble_budget(root: Path) -> Check:
    try:
        report = cos_preamble_budget.build_budget("core", root)
    except Exception as exc:  # noqa: BLE001
        return Check(
            id="core-preamble-budget",
            status="fail",
            message="core preamble budget could not be evaluated",
            details={"error": str(exc)},
        )
    status = "pass" if report["status"] == "pass" else "fail"
    return Check(
        id="core-preamble-budget",
        status=status,
        message=(
            "core full-context preamble is below token budget"
            if status == "pass"
            else "core full-context preamble exceeds token budget"
        ),
        details=report,
    )


def check_runtime_hook_reality(root: Path) -> Check:
    try:
        report = runtime_hook_reality.build_report(project_root=root)
    except runtime_hook_reality.RuntimeHookRealityError as exc:
        return Check(
            id="runtime-hook-reality",
            status="fail",
            message="runtime hook reality audit could not run",
            details={"error": str(exc)},
        )
    status = "pass" if report["summary"]["status"] == "pass" else "fail"
    return Check(
        id="runtime-hook-reality",
        status=status,
        message="runtime hooks match lifecycle metadata and observable behavior" if status == "pass" else "runtime hook reality audit has findings",
        details={"summary": report["summary"], "findings": report["findings"]},
    )



def check_core_session_start_budget(root: Path) -> Check:
    try:
        report = session_start_budget.build_report("core", root)
    except Exception as exc:  # noqa: BLE001
        return Check(
            id="core-session-start-budget",
            status="fail",
            message="core SessionStart budget could not be evaluated",
            details={"error": str(exc)},
        )
    status = "pass" if report["fail_count"] == 0 else "fail"
    return Check(
        id="core-session-start-budget",
        status=status,
        message="core SessionStart projection is below budget and contains no lab hooks" if status == "pass" else "core SessionStart projection exceeds budget or contains lab hooks",
        details={
            "profile": report["profile"],
            "session_start_hook_count": report["session_start_hook_count"],
            "projection_source": report.get("projection_source"),
            "active_session_start_hook_count": report.get("active_session_start_hook_count"),
            "active_projection_matches_profile": report.get("active_projection_matches_profile"),
            "counts_by_tier": report["counts_by_tier"],
            "budget": report["budget"],
            "findings": report["findings"],
            "candidates_to_move": report["candidates_to_move"][:20],
        },
    )

def check_silent_failure_audit(root: Path) -> Check:
    report = silent_failure_audit.build_report(
        repo_root=root,
        scan_root=root / "hooks",
        allowlist_path=root / "manifests" / "silent-failure-allowlist.yaml",
    )
    status = "fail" if report["fail_count"] else "pass"
    return Check(
        id="silent-failure-audit",
        status=status,
        message=(
            "shell silent-failure surface is classified and has not grown; ADR-132 transferability debt remains tracked in details"
            if status == "pass"
            else "shell silent-failure surface has unclassified or increased patterns"
        ),
        details={
            "file_count": report["file_count"],
            "occurrence_count": report["occurrence_count"],
            "fail_count": report["fail_count"],
            "warn_count": report["warn_count"],
            "counts_by_transferability_state": report["counts_by_transferability_state"],
            "occurrences_by_transferability_state": report["occurrences_by_transferability_state"],
            "maintainer_cache_file_count": report["maintainer_cache_file_count"],
            "maintainer_cache_occurrence_count": report["maintainer_cache_occurrence_count"],
            "findings": report["findings"][:50],
        },
    )

def check_python_stdin_antipattern_audit(root: Path) -> Check:
    report = python_stdin_antipattern_audit.build_report(root)
    status = "pass" if report["status"] == "pass" else "fail"
    return Check(
        id="python-stdin-antipattern-audit",
        status=status,
        message=(
            "no pipe-into-python-heredoc stdin traps found"
            if status == "pass"
            else "pipe-into-python-heredoc pattern drops piped stdin and must be rewritten"
        ),
        details=report,
    )

def check_roi(root: Path, window_hours: int) -> Check:
    report = cos_governance_roi.build_report(root, window_hours)
    roi = report["roi"]
    demotion_report = cos_demotion_loop_audit.build_report(root / "manifests" / "primitive-lifecycle.yaml")
    roi_actioned = int(demotion_report.get("roi_signed_demotion_count") or 0) > 0
    status = "pass" if roi["status"] == "positive" or roi_actioned else "warn"
    return Check(
        id="governance-roi",
        status=status,
        message=(
            "governance ROI is non-negative in the selected window"
            if roi["status"] == "positive"
            else (
                "governance ROI is negative, but an ROI-signed demotion/reduction has actioned it"
                if roi_actioned
                else "governance ROI is negative; demotion/reduction required"
            )
        ),
        details={
            "roi": roi,
            "recommendations": report.get("recommendations", []),
            "roi_signed_demotion_count": demotion_report.get("roi_signed_demotion_count"),
            "demotion_loop_status": demotion_report.get("status"),
        },
    )




def check_lifecycle_recommendations(root: Path, window_hours: int) -> Check:
    roi_report = cos_governance_roi.build_report(root, window_hours)
    lifecycle_report = primitive_lifecycle.build_report(
        root / "manifests" / "primitive-lifecycle.yaml",
        roi_report,
    )
    recommendations = lifecycle_report.get("recommendations", [])
    has_schema = isinstance(recommendations, list)
    return Check(
        id="friction-demotion-gate",
        status="pass" if has_schema else "fail",
        message="ROI/friction produces lifecycle recommendations" if has_schema else "lifecycle recommendations are unavailable",
        details={
            "recommendation_count": len(recommendations) if has_schema else 0,
            "recommendations": recommendations,
        },
    )


def check_runtime_primitives(root: Path) -> Check:
    missing: dict[str, list[str]] = {}
    for primitive_id, rel_paths in REQUIRED_RUNTIME_PRIMITIVES.items():
        absent = [rel for rel in rel_paths if not (root / rel).exists()]
        if absent:
            missing[primitive_id] = absent
    return Check(
        id="runtime-safety-primitives-present",
        status="pass" if not missing else "fail",
        message="branch lease, safe-mode, and protected-publication primitives exist" if not missing else "required runtime-safety primitive files are missing",
        details={"missing": missing, "required": REQUIRED_RUNTIME_PRIMITIVES},
    )


def check_wiring_gaps(root: Path) -> Check:
    gaps: list[dict[str, Any]] = []
    passed: list[str] = []
    for probe in PHASE2_WIRING_PROBES:
        path = root / str(probe["path"])
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            gaps.append(probe)
            continue
        if all(needle in content for needle in probe["needles"]):
            passed.append(str(probe["id"]))
        else:
            gaps.append(probe)
    return Check(
        id="known-wiring-gaps",
        status="warn" if gaps else "pass",
        message="known phase gaps remain visible" if gaps else "Phase 2 wiring probes are present",
        details={"gaps": gaps, "passed": passed},
    )



def _iter_product_facing_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for rel in PRODUCT_FACING_DOCS:
        path = root / rel
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(path.rglob("*.md")))
    return files


def check_product_claims(root: Path) -> Check:
    findings: list[dict[str, Any]] = []
    readme = root / "README.md"
    if readme.exists():
        content = readme.read_text(encoding="utf-8", errors="ignore")
        for match in re.finditer(r"`([^`]+\.sh)`", content):
            claim = match.group(1)
            shell_paths = [token for token in re.split(r"\s+", claim) if token.endswith(".sh")]
            for shell_path in shell_paths:
                candidate_paths = [root / shell_path, root / "hooks" / shell_path, root / "scripts" / shell_path]
                if not any(path.exists() for path in candidate_paths):
                    findings.append({
                        "id": "readme-missing-shell-claim",
                        "severity": "fail",
                        "file": "README.md",
                        "claim": claim,
                        "missing_path": shell_path,
                        "message": "README references a shell hook/script that does not exist",
                    })
    for path in _iter_product_facing_files(root):
        rel = str(path.relative_to(root))
        text = path.read_text(encoding="utf-8", errors="ignore")
        for line_no, line in enumerate(text.splitlines(), 1):
            for pattern in STALE_MODEL_NAMING_PATTERNS:
                if pattern.search(line):
                    findings.append({
                        "id": "stale-model-branded-product-copy",
                        "severity": "fail",
                        "file": rel,
                        "line": line_no,
                        "pattern": pattern.pattern,
                        "message": "product-facing docs contain stale model/vendor-branded readiness or direct model IDs",
                    })
    return Check(
        id="product-claim-integrity",
        status="fail" if findings else "pass",
        message="product-facing claims reference existing files and neutral naming" if not findings else "product-facing claims contain missing files or stale model-branded names",
        details={"findings": findings},
    )


def _load_lifecycle_maturity_labels(root: Path) -> dict[str, dict[str, Any]]:
    manifest = root / "manifests" / "primitive-lifecycle.yaml"
    try:
        data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return {}
    primitives = data.get("primitives") if isinstance(data, dict) else None
    if not isinstance(primitives, list):
        return {}
    return {str(item.get("id")): item for item in primitives if isinstance(item, dict) and item.get("id")}


def _load_governance_maturity_overlay(root: Path) -> dict[str, dict[str, Any]]:
    manifest = root / "manifests" / "governance-maturity.yaml"
    if not manifest.exists():
        return {}
    return {
        "<overlay>": {
            "maturity": "duplicate-source",
            "path": str(manifest.relative_to(root)),
        }
    }


def check_governance_maturity_labels(root: Path) -> Check:
    lifecycle_labels = _load_lifecycle_maturity_labels(root)
    overlay_labels = _load_governance_maturity_overlay(root)
    missing = sorted(REQUIRED_MATURITY_LABELS - set(lifecycle_labels))
    invalid = []
    contradictions = []
    for primitive_id in REQUIRED_MATURITY_LABELS:
        item = lifecycle_labels.get(primitive_id, {})
        if item.get("maturity") not in {"observe", "advisory", "blocking"}:
            invalid.append(primitive_id)
        overlay = overlay_labels.get(primitive_id)
        if overlay and overlay.get("maturity") != item.get("maturity"):
            contradictions.append(primitive_id)
    if "<overlay>" in overlay_labels:
        contradictions.append("manifests/governance-maturity.yaml")
    status = "pass" if not missing and not invalid and not contradictions else "fail"
    return Check(
        id="governance-maturity-labels",
        status=status,
        message="trust/blast governance maturity labels are explicit in lifecycle metadata" if status == "pass" else "required governance maturity labels are missing, invalid, or duplicated",
        details={
            "missing": missing,
            "invalid": sorted(invalid),
            "contradictions": sorted(contradictions),
            "labels": {primitive_id: lifecycle_labels.get(primitive_id) for primitive_id in sorted(REQUIRED_MATURITY_LABELS)},
            "overlay_labels": overlay_labels,
        },
    )


def check_lab_first_promotion_gate(root: Path) -> Check:
    report = lab_first_promotion_gate.build_report(
        manifest_path=root / "manifests" / "primitive-lifecycle.yaml",
        repo_root=root,
        base_ref="origin/main",
    )
    status = "pass" if report["status"] == "pass" else "fail"
    return Check(
        id="lab-first-promotion-gate",
        status=status,
        message=(
            "new/promoted non-lab primitives carry control-plane evidence"
            if status == "pass"
            else "new/promoted core/team/blocking/default-on primitives lack promotion evidence"
        ),
        details=report,
    )


def check_adr_tier_claim_audit(root: Path) -> Check:
    report = cos_tier_claim_audit.build_report(root / "docs" / "02-Decisions" / "adrs", root)
    status = "pass" if report["status"] == "pass" else "fail"
    return Check(
        id="adr-tier-claim-audit",
        status=status,
        message=(
            "core/team ADR tier claims carry boring-reliability evidence"
            if status == "pass"
            else "core/team ADR tier claims lack boring-reliability evidence"
        ),
        details=report,
    )


def check_manifest_tier_claim_audit(root: Path) -> Check:
    manifest_path = root / "manifests" / "primitive-lifecycle.yaml"
    if not manifest_path.exists():
        return Check(
            id="manifest-tier-claim-audit",
            status="warn",
            message="primitive lifecycle manifest is missing; manifest tier claims could not be evaluated",
            details={"manifest": str(manifest_path)},
        )
    report = cos_manifest_tier_claim_audit.build_report(manifest_path)
    status = "pass" if report["status"] == "pass" else "warn"
    return Check(
        id="manifest-tier-claim-audit",
        status=status,
        message=(
            "primitive lifecycle distribution claims are evidence-backed"
            if status == "pass"
            else "primitive lifecycle distribution claims still expose maintainer-knowledge or demotion candidates"
        ),
        details={
            "finding_count": report["finding_count"],
            "counts_by_category": report["counts_by_category"],
            "candidate_second_demote_count": report["candidate_second_demote_count"],
            "candidate_second_demotes": report["candidate_second_demotes"][:10],
        },
    )


def check_demotion_loop_maturity(root: Path) -> Check:
    manifest_path = root / "manifests" / "primitive-lifecycle.yaml"
    if not manifest_path.exists():
        return Check(
            id="demotion-loop-maturity",
            status="warn",
            message="primitive lifecycle manifest is missing; demotion loop maturity could not be evaluated",
            details={"manifest": str(manifest_path)},
        )
    report = cos_demotion_loop_audit.build_report(manifest_path)
    status = report["status"] if report["status"] in {"pass", "warn", "fail"} else "warn"
    return Check(
        id="demotion-loop-maturity",
        status=status,
        message=(
            "ADR-126 demotion loop has repeated and ROI-signed evidence"
            if status == "pass"
            else (
                "ADR-126 demotion loop warning budget expired without ROI-signed demotion"
                if status == "fail"
                else "ADR-126 demotion loop is visible but not yet proven by a second/ROI-signed demotion"
            )
        ),
        details=report,
    )


def build_report(root: Path, window_hours: int) -> dict[str, Any]:
    repo_hygiene = check_repo_hygiene(root)
    adoption_tiers = check_adoption_tiers(root)
    lifecycle_manifest = check_lifecycle_manifest(root)
    active_surface = check_active_surface(root)
    checks = [
        repo_hygiene,
        adoption_tiers,
        lifecycle_manifest,
        active_surface,
        check_core_preamble_budget(root),
        check_runtime_hook_reality(root),
        check_core_session_start_budget(root),
        check_silent_failure_audit(root),
        check_python_stdin_antipattern_audit(root),
        check_roi(root, window_hours),
        check_lifecycle_recommendations(root, window_hours),
        check_runtime_primitives(root),
        check_wiring_gaps(root),
        check_product_claims(root),
        check_governance_maturity_labels(root),
        check_lab_first_promotion_gate(root),
        check_adr_tier_claim_audit(root),
        check_manifest_tier_claim_audit(root),
        check_demotion_loop_maturity(root),
    ]
    fail_count = sum(1 for check in checks if check.status == "fail")
    warn_count = sum(1 for check in checks if check.status == "warn")
    pass_count = sum(1 for check in checks if check.status == "pass")
    score = round((pass_count / len(checks)) * 100) if checks else 0
    return {
        "project": str(root),
        "window_hours": window_hours,
        "score": score,
        "status": "fail" if fail_count else ("warn" if warn_count else "pass"),
        "pass_count": pass_count,
        "warn_count": warn_count,
        "fail_count": fail_count,
        "discovery_overload": discovery_overload_signal(active_surface),
        "active_safety_layer": active_safety_layer_summary(root, active_surface),
        "token_context_estimate": token_context_estimate(root),
        "checks": [asdict(check) for check in checks],
        "next_phases": [
            "Phase 1: friction budget and demotion gate",
            "Phase 2: wire branch lease, safe-mode, and protected-publication into real flows",
            "Phase 3: active surface reduction by distribution/profile",
            "Phase 4: production border-case suite",
            "Phase 5: product packaging proof",
        ],
    }


def print_human(report: dict[str, Any]) -> None:
    print("COS Architecture Readiness")
    print(f"status: {report['status']} score={report['score']} pass={report['pass_count']} warn={report['warn_count']} fail={report['fail_count']}")
    safety = report["active_safety_layer"]
    print("active safety layer:")
    print(f"- phase={safety['phase']} profile={safety['active_profile']}")
    print(f"- hard-blocking guards: {', '.join(safety['hard_blocking_guards']) or '(none)'}")
    print(f"- advisory guards: {', '.join(safety['advisory_guards']) or '(none)'}")
    print(f"- maintainer opt-in: {safety['maintainer_opt_ins']['command']}")
    print(f"- lab recovery: {safety['lab_opt_ins']['command']}")
    overload = report["discovery_overload"]
    print(
        "discovery overload: "
        f"current={overload['current_count']} threshold={overload['threshold']} "
        f"overloaded={overload['overloaded']} action={overload['recommended_action']}"
    )
    estimate = report["token_context_estimate"]
    if estimate.get("estimate_unavailable"):
        print(f"context tax estimate: unavailable ({estimate['reason']})")
    else:
        print(f"context tax estimate: ~{estimate['estimated_tokens']} tokens ({estimate['method']})")
    for check in report["checks"]:
        marker = {"pass": "PASS", "warn": "WARN", "fail": "FAIL"}[check["status"]]
        print(f"- {marker} {check['id']}: {check['message']}")
    if report["status"] != "pass":
        print("next phases:")
        for phase in report["next_phases"]:
            print(f"- {phase}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", default=str(REPO_ROOT))
    parser.add_argument("--window-hours", type=int, default=24)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = build_report(Path(args.project_dir).resolve(), args.window_hours)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_human(report)
    return 0 if report["fail_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
