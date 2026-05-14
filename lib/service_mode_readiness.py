"""Initial Service-Mode Readiness Gate for ADR-211."""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lib.cross_stack_secret_audit import audit as secret_audit
from lib.performance_ledger import repo_root
from lib.public_claim_gate import scan as public_claim_scan
from lib.reward_signal_quality import audit_stream, load_contract, summarize
from lib.worktree_audit import audit as worktree_audit
from scripts.private_content_audit import build_report as private_content_report
from scripts.private_content_audit import classify_path, load_manifest as load_private_manifest, projection_decision


SCHEMA_VERSION = "service-mode-readiness/v1"


@dataclass(frozen=True)
class GateStatus:
    id: str
    status: str
    summary: str
    evidence: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status,
            "summary": self.summary,
            "evidence": self.evidence,
        }


def _red(identifier: str, summary: str, **evidence: Any) -> GateStatus:
    return GateStatus(identifier, "red", summary, evidence)


def _green(identifier: str, summary: str, **evidence: Any) -> GateStatus:
    return GateStatus(identifier, "green", summary, evidence)


def _yellow(identifier: str, summary: str, **evidence: Any) -> GateStatus:
    return GateStatus(identifier, "yellow", summary, evidence)


def check_private_content(project_dir: Path) -> GateStatus:
    manifest = project_dir / "manifests" / "private-content.yaml"
    if not manifest.exists():
        return _red("private-content", "ADR-202 manifest missing", manifest=str(manifest))
    report = private_content_report(project_dir, manifest, include_unknown=False, include_secrets=False)
    summary = report["summary"]
    if summary["block"]:
        return _red("private-content", "ADR-202 manifest has blocking findings", audit_summary=summary)
    return _green("private-content", "ADR-202 private-content classification manifest is valid", audit_summary=summary)


def check_run_trace(project_dir: Path) -> GateStatus:
    latest = project_dir / ".cognitive-os" / "reports" / "run-trace-latest.json"
    if not latest.exists():
        return _red("run-flight-recorder", "ADR-205 latest run trace report missing", latest_report=str(latest))
    try:
        payload = json.loads(latest.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return _red("run-flight-recorder", "ADR-205 latest run trace report is invalid JSON", error=str(exc))
    if payload.get("schema_version") != "run-flight-recorder/v1":
        return _red("run-flight-recorder", "ADR-205 latest run trace has wrong schema", schema_version=payload.get("schema_version"))
    if int(payload.get("event_count") or 0) <= 0:
        return _red("run-flight-recorder", "ADR-205 latest run trace has no joined events", event_count=payload.get("event_count"))
    return _green("run-flight-recorder", "ADR-205 run trace latest report is present", event_count=payload.get("event_count"), streams=payload.get("streams", {}))


def check_worktree_divergence(project_dir: Path) -> GateStatus:
    try:
        report = worktree_audit(project_dir)
    except SystemExit as exc:
        return _yellow("worktree-divergence", "ADR-220 worktree divergence audit not applicable outside a git worktree", error=str(exc))
    except Exception as exc:
        return _red("worktree-divergence", "ADR-220 worktree divergence audit failed", error=str(exc))
    summary = report.get("summary", {})
    if int(summary.get("block_count") or 0):
        return _red(
            "worktree-divergence",
            "ADR-220 linked worktree divergence has blocking path overlap",
            audit_summary=summary,
            findings=report.get("findings", [])[:10],
        )
    if int(summary.get("warn_count") or 0):
        return _yellow(
            "worktree-divergence",
            "ADR-220 linked worktree divergence has warnings without dirty-path overlap",
            audit_summary=summary,
            findings=report.get("findings", [])[:10],
        )
    return _green("worktree-divergence", "ADR-220 worktree divergence audit passes", audit_summary=summary)


def check_performance_ledger(project_dir: Path) -> GateStatus:
    latest = project_dir / ".cognitive-os" / "reports" / "performance-ledger-latest.json"
    if not latest.exists():
        return _red("performance-ledger", "ADR-201 latest Performance Ledger report missing", latest_report=str(latest))
    try:
        payload = json.loads(latest.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return _red("performance-ledger", "ADR-201 latest Performance Ledger report is invalid JSON", error=str(exc))
    policy = payload.get("consumption_policy") or {}
    if not bool(policy.get("can_consume_all", False)):
        return _red("performance-ledger", "ADR-204 consumption policy blocks Performance Ledger consumers", blocked_streams=policy.get("blocked_streams", []))
    return _green("performance-ledger", "ADR-201 Performance Ledger is consumable", ledger_summary=payload.get("summary", {}))


def check_reward_signals(project_dir: Path) -> GateStatus:
    contract_path = project_dir / "manifests" / "reward-signal-contract.yaml"
    if not contract_path.exists():
        return _red("reward-signals", "ADR-204 reward signal contract missing", contract=str(contract_path))
    contract = load_contract(contract_path)
    results = []
    for stream in sorted((contract.get("streams", {}) or {}).keys()):
        results.extend(audit_stream(project_dir, contract, stream, limit=100))
    summary = summarize(results)
    if summary["total"] == 0:
        return _red("reward-signals", "No reward-signal rows available for service-mode readiness", reward_summary=summary)
    if summary["suspect"] or summary["corrupt"]:
        return _red("reward-signals", "Reward signals contain quarantined rows", reward_summary=summary)
    return _green("reward-signals", "Reward signals are present and clean", reward_summary=summary)


def check_secret_release_readiness(project_dir: Path) -> GateStatus:
    manifest = project_dir / "manifests" / "cross-stack-secret-audit.yaml"
    if not manifest.exists():
        return _red("release-secret-audit", "ADR-215 secret audit manifest missing", manifest=str(manifest))
    try:
        report = secret_audit(project_dir, verify_live=False, include_local_sensitive_surfaces=True)
    except Exception as exc:
        return _red("release-secret-audit", "ADR-215 secret audit failed to run", error=str(exc))
    if report.get("schema_version") != "cross-stack-secret-audit-report/v1":
        return _red("release-secret-audit", "ADR-215 secret audit returned wrong schema", schema_version=report.get("schema_version"))
    status = report.get("status")
    if status != "pass":
        findings = report.get("findings", [])
        if status == "warn" and findings and all(
            finding.get("classification") == "tooling" and finding.get("code") == "primary-tool-missing"
            for finding in findings
        ):
            return _green(
                "release-secret-audit",
                "ADR-215 release-readiness secret audit has no sensitive-surface findings; primary scanner tools are advisory in local smoke mode",
                status=status,
                finding_count=len(findings),
                findings=findings[:10],
            )
        return _red(
            "release-secret-audit",
            "ADR-215 release-readiness secret audit is not clean",
            status=status,
            finding_count=len(findings),
            findings=findings[:10],
        )
    return _green("release-secret-audit", "ADR-215 release-readiness secret audit passes", toolchain=report.get("primary_toolchain"))


def check_maintainer_runner(project_dir: Path) -> GateStatus:
    runner = project_dir / "scripts" / "cos-maintainer-agent"
    promoter = project_dir / "scripts" / "cos-promote-from-telemetry"
    missing = [str(path) for path in (runner, promoter) if not path.exists()]
    if missing:
        return _red("maintainer-propose-only", "ADR-201 maintainer propose-only runner missing", missing=missing)
    return _green("maintainer-propose-only", "ADR-201 propose-only Maintainer runner exists", runner=str(runner), promoter=str(promoter))


def check_experiment_contract(project_dir: Path) -> GateStatus:
    schema = project_dir / "manifests" / "maintainer-experiment-schema.yaml"
    if not schema.exists():
        return _red("maintainer-experiment-contract", "ADR-209 experiment contract schema missing", schema=str(schema))
    return _green("maintainer-experiment-contract", "ADR-209 experiment contract schema exists", schema=str(schema))


def check_mutation_boundary(project_dir: Path) -> GateStatus:
    runner = project_dir / "scripts" / "cos-maintainer-agent"
    if not runner.exists():
        return _red("mutation-authorization-boundary", "Maintainer runner missing; ADR-164 boundary cannot be inspected")
    text = runner.read_text(encoding="utf-8")
    if "ADR-164" not in text or "propose-only" not in text:
        return _red("mutation-authorization-boundary", "Maintainer runner does not declare ADR-164 propose-only boundary")
    return _green("mutation-authorization-boundary", "Maintainer runner declares ADR-164 propose-only boundary")


def check_cloud_private_content_smoke(project_dir: Path) -> GateStatus:
    manifest_path = project_dir / "manifests" / "private-content.yaml"
    if not manifest_path.exists():
        return _red("cloud-private-content-smoke", "Cannot run projection smoke without ADR-202 manifest")
    manifest = load_private_manifest(manifest_path)
    classification = classify_path(".cognitive-os/strategy/service-mode-smoke.md", manifest, project_dir)
    decision = projection_decision(classification, manifest, destination="cloud", action="export", redaction_status="raw")
    if decision["status"] != "block":
        return _red("cloud-private-content-smoke", "Local-only private strategy content was not blocked from cloud export", decision=decision)
    return _green("cloud-private-content-smoke", "Local-only private content blocks cloud export", reasons=decision.get("reasons", []))


def check_public_claim_gate(project_dir: Path) -> GateStatus:
    try:
        public_report = public_claim_scan(project_dir)
    except Exception as exc:
        return _red("public-claim-gate", "ADR-206 public claim gate failed to run", error=str(exc))
    if public_report.get("status") != "pass":
        return _red(
            "public-claim-gate",
            "ADR-206 public docs contain unbacked high-risk autonomous/self-improvement claims",
            finding_count=public_report.get("finding_count"),
            findings=public_report.get("findings", [])[:10],
        )

    scripts_dir = project_dir / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    try:
        from cos_claim_signature_audit import build_report  # type: ignore[import]
    except Exception as exc:
        return _red("public-claim-gate", "ADR-206 claim-signature audit cannot be imported", error=str(exc))
    try:
        report = build_report(project_dir / "manifests" / "primitive-lifecycle.yaml", project_dir / "manifests" / "external-adoption-evidence.yaml")
    except Exception as exc:
        return _red("public-claim-gate", "ADR-206 claim-signature audit failed to run", error=str(exc))
    if report.get("status") == "fail" or report.get("warn_count", 0):
        return _red(
            "public-claim-gate",
            "Public claims are not fully signed by repository evidence",
            status=report.get("status"),
            signed_claim_count=report.get("signed_claim_count"),
            claim_count=report.get("claim_count"),
            fail_count=report.get("fail_count"),
            warn_count=report.get("warn_count"),
        )
    return _green(
        "public-claim-gate",
        "Public claim gate passes; unsigned bilateral external-help claim remains info-only and must stay out of unqualified public copy",
        signed_claim_count=report.get("signed_claim_count"),
        claim_count=report.get("claim_count"),
        public_claim_findings=public_report.get("finding_count"),
        info_count=report.get("info_count"),
    )


def build_readiness_report(project_dir: Path | None = None) -> dict[str, Any]:
    project = (project_dir or repo_root()).resolve()
    gates = [
        check_private_content(project),
        check_run_trace(project),
        check_worktree_divergence(project),
        check_performance_ledger(project),
        check_reward_signals(project),
        check_secret_release_readiness(project),
        check_maintainer_runner(project),
        check_experiment_contract(project),
        check_mutation_boundary(project),
        check_cloud_private_content_smoke(project),
        check_public_claim_gate(project),
    ]
    counts = {"green": 0, "yellow": 0, "red": 0}
    for gate in gates:
        counts[gate.status] += 1
    return {
        "schema_version": SCHEMA_VERSION,
        "project_dir": str(project),
        "status": "red" if counts["red"] else ("yellow" if counts["yellow"] else "green"),
        "summary": counts,
        "gates": [gate.to_dict() for gate in gates],
        "policy": "No standalone/cloud service-mode claim may ship while any required gate is red.",
    }
