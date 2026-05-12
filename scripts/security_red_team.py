#!/usr/bin/env python3
"""Unified Cognitive OS security red-team runner.

The runner is deterministic and local-only by default: it does not read blocked
secret files, does not make network calls, and does not execute optional scanners.
It inventories the SO attack surface, runs structural abuse probes, scores known
security primitives, and writes JSON/Markdown reports.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "manifests" / "security-red-team.yaml"
DEFAULT_OUT_DIR = REPO_ROOT / ".cognitive-os" / "reports" / "security-red-team"
BLOCKED_NAMES = {".env", ".git", "secrets", "node_modules", "__pycache__"}
SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW")


@dataclass(frozen=True)
class Finding:
    id: str
    severity: str
    title: str
    evidence: str
    recommendation: str


@dataclass(frozen=True)
class ProbeResult:
    id: str
    status: str
    evidence: str


@dataclass(frozen=True)
class PrimitiveScore:
    primitive: str
    score: int
    dimensions: dict[str, int]
    notes: list[str]


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _exists(path: str) -> bool:
    return (REPO_ROOT / path).exists()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_count_files(root: Path) -> int:
    if not root.exists():
        return 0
    count = 0
    for current, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in BLOCKED_NAMES]
        count += len([f for f in files if f not in BLOCKED_NAMES])
    return count


def inventory_surface() -> dict[str, Any]:
    dirs = {
        "hooks": "hooks",
        "rules": "rules",
        "skills": "skills",
        "scripts": "scripts",
        "manifests": "manifests",
        "tests_red_team": "tests/red_team",
        "tests_security": "tests/security",
        "docs_security": "docs/09-Quality/security",
    }
    return {
        name: {
            "path": rel,
            "exists": _exists(rel),
            "files": _safe_count_files(REPO_ROOT / rel),
        }
        for name, rel in dirs.items()
    }


def probe_credential_safe_integrity(findings: list[Finding]) -> ProbeResult:
    manifest_path = REPO_ROOT / "manifests" / "credential-safe-scripts.yaml"
    if not manifest_path.exists():
        findings.append(Finding(
            "credential_safe_manifest_missing",
            "HIGH",
            "Credential-safe manifest is missing",
            str(manifest_path),
            "Create manifests/credential-safe-scripts.yaml before allowing agents to load env-file credentials.",
        ))
        return ProbeResult("credential_safe_integrity", "FAIL", "manifest missing")
    data = _read_yaml(manifest_path)
    mismatches: list[str] = []
    for entry in data.get("scripts", []):
        integrity = entry.get("command_integrity") or {}
        rel = integrity.get("path")
        expected = integrity.get("sha256")
        if not rel or not expected:
            mismatches.append(f"{entry.get('id')}: missing integrity pin")
            continue
        target = REPO_ROOT / rel
        if not target.exists():
            mismatches.append(f"{entry.get('id')}: missing command {rel}")
            continue
        actual = _file_sha256(target)
        if actual != expected:
            mismatches.append(f"{entry.get('id')}: {rel} sha256={actual} expected={expected}")
    if mismatches:
        findings.append(Finding(
            "credential_safe_integrity_mismatch",
            "CRITICAL",
            "Credential-safe allowlisted command integrity mismatch",
            "; ".join(mismatches),
            "Review the script change, update the manifest hash only after security review, and rerun credential-safe tests.",
        ))
        return ProbeResult("credential_safe_integrity", "FAIL", "; ".join(mismatches))
    return ProbeResult("credential_safe_integrity", "PASS", "all credential-safe commands match pinned hashes")


def probe_credential_safe_env_boundary(findings: list[Finding]) -> ProbeResult:
    runner = REPO_ROOT / "scripts" / "cos_credential_safe_run.py"
    if not runner.exists():
        findings.append(Finding(
            "credential_safe_runner_missing",
            "HIGH",
            "Credential-safe runner is missing",
            str(runner),
            "Add scripts/cos_credential_safe_run.py and tests before allowing env-file-backed smokes.",
        ))
        return ProbeResult("credential_safe_env_boundary", "FAIL", "runner missing")
    text = runner.read_text(encoding="utf-8")
    required = ["_sanitized_child_env", "_resolve_allowed_env_file", "_secret_variants", "_bounded", "COS_ALLOW_CREDENTIAL_SAFE_ENV"]
    missing = [token for token in required if token not in text]
    if missing:
        findings.append(Finding(
            "credential_safe_boundary_incomplete",
            "HIGH",
            "Credential-safe runner boundary checks are incomplete",
            f"missing tokens: {', '.join(missing)}",
            "Keep env-file allowlisting, sanitized child env, encoded-secret redaction, and output bounding in the runner.",
        ))
        return ProbeResult("credential_safe_env_boundary", "FAIL", f"missing {missing}")
    return ProbeResult("credential_safe_env_boundary", "PASS", "runner contains env boundary, redaction, and output-bound controls")


def probe_blocked_path_policy(findings: list[Finding]) -> ProbeResult:
    candidates = [REPO_ROOT / "AGENTS.md", REPO_ROOT / "rules" / "RULES-COMPACT.md", REPO_ROOT / "rules" / "private-mode.md"]
    content = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in candidates if p.exists())
    required = [".env", "*.key", "*.pem", "secrets", ".git/config"]
    missing = [token for token in required if token not in content]
    if missing:
        findings.append(Finding(
            "blocked_path_policy_gap",
            "HIGH",
            "Blocked path policy does not document every required secret surface",
            f"missing: {', '.join(missing)}",
            "Update AGENTS.md/rules so every runtime agrees on blocked secret paths.",
        ))
        return ProbeResult("blocked_path_policy", "FAIL", f"missing {missing}")
    return ProbeResult("blocked_path_policy", "PASS", "blocked secret paths documented")


def probe_redteam_scenario_coverage(findings: list[Finding]) -> ProbeResult:
    scenario_dir = REPO_ROOT / "tests" / "red_team" / "scenarios"
    scenarios = sorted(scenario_dir.glob("*.yaml")) if scenario_dir.exists() else []
    if len(scenarios) < 5:
        findings.append(Finding(
            "redteam_scenarios_thin",
            "MEDIUM",
            "Red-team scenario coverage is thin",
            f"scenario_count={len(scenarios)}",
            "Add scenarios for secret exfiltration, MCP poisoning, env flag abuse, and provider routing abuse.",
        ))
        return ProbeResult("redteam_scenario_coverage", "WARN", f"scenario_count={len(scenarios)}")
    return ProbeResult("redteam_scenario_coverage", "PASS", f"scenario_count={len(scenarios)}")


def probe_scanner_hook_presence(findings: list[Finding]) -> ProbeResult:
    expected = ["hooks/parry-scan.sh", "hooks/aguara-scan.sh", "hooks/mcp-scan.sh", "hooks/semgrep-scan.sh"]
    missing = [rel for rel in expected if not _exists(rel)]
    if missing:
        findings.append(Finding(
            "scanner_hooks_missing",
            "HIGH",
            "Security scanner hooks are missing",
            ", ".join(missing),
            "Restore scanner hooks or explicitly retire them with ADR-backed replacement controls.",
        ))
        return ProbeResult("scanner_hook_presence", "FAIL", f"missing {missing}")
    return ProbeResult("scanner_hook_presence", "PASS", "Parry, Aguara, MCP-scan, and Semgrep hook files exist")


def probe_runtime_flag_registry(findings: list[Finding]) -> ProbeResult:
    manifest = REPO_ROOT / "manifests" / "runtime-env-flags.yaml"
    docs = REPO_ROOT / "docs" / "runtime-env-flags.md"
    if not manifest.exists() or not docs.exists():
        findings.append(Finding(
            "runtime_flag_registry_missing",
            "MEDIUM",
            "Runtime env flag registry is missing or undocumented",
            f"manifest={manifest.exists()} docs={docs.exists()}",
            "Keep manifests/runtime-env-flags.yaml and docs/04-Concepts/root/runtime-env-flags.md as the public contract for skips/bypasses.",
        ))
        return ProbeResult("runtime_flag_registry", "WARN", "registry/doc missing")
    return ProbeResult("runtime_flag_registry", "PASS", "runtime flag registry and docs exist")


def probe_mcp_security_surface(findings: list[Finding]) -> ProbeResult:
    hook = REPO_ROOT / "hooks" / "mcp-scan.sh"
    contract = REPO_ROOT / "manifests" / "host-cli-bridge-contract.yaml"
    if not hook.exists():
        findings.append(Finding(
            "mcp_scan_missing",
            "HIGH",
            "MCP security scanner hook is missing",
            str(hook),
            "Restore mcp-scan hook to catch tool poisoning and cross-origin MCP risks.",
        ))
        return ProbeResult("mcp_security_surface", "FAIL", "mcp-scan hook missing")
    evidence = "mcp-scan hook exists"
    if contract.exists():
        evidence += "; host CLI bridge contract exists"
    else:
        findings.append(Finding(
            "host_cli_bridge_contract_missing",
            "LOW",
            "Host CLI bridge contract not found",
            str(contract),
            "Keep host CLI bridge boundaries documented when MCP/tools can request host credentials.",
        ))
    return ProbeResult("mcp_security_surface", "PASS", evidence)


def probe_runtime_sensitive_file_deny(findings: list[Finding]) -> ProbeResult:
    settings = REPO_ROOT / ".claude" / "settings.json"
    if not settings.exists():
        findings.append(Finding(
            "runtime_sensitive_file_deny_missing",
            "HIGH",
            "Committed runtime settings are missing",
            str(settings),
            "Commit runtime settings with explicit sensitive-file deny rules.",
        ))
        return ProbeResult("runtime_sensitive_file_deny", "FAIL", "settings missing")
    data = json.loads(settings.read_text(encoding="utf-8"))
    deny = set(data.get("permissions", {}).get("deny", []))
    required = {"Read(./.env)", "Read(./.env.*)", "Read(./secrets/**)", "Read(./.git/config)"}
    missing = sorted(required - deny)
    if missing:
        findings.append(Finding(
            "runtime_sensitive_file_deny_incomplete",
            "HIGH",
            "Runtime settings do not deny every required sensitive path",
            f"missing={missing}",
            "Add explicit permissions.deny entries for env, secrets, and git config.",
        ))
        return ProbeResult("runtime_sensitive_file_deny", "FAIL", f"missing={missing}")
    return ProbeResult("runtime_sensitive_file_deny", "PASS", "committed settings deny .env, .env.*, secrets/**, and .git/config")


def probe_protected_config_write_guard(findings: list[Finding]) -> ProbeResult:
    hook = REPO_ROOT / "hooks" / "protected-config-write-guard.sh"
    policy = REPO_ROOT / "manifests" / "protected-config-write-policy.yaml"
    if not hook.exists() or not policy.exists():
        findings.append(Finding(
            "protected_config_write_guard_missing",
            "HIGH",
            "Protected config write guard is missing",
            f"hook={hook.exists()} policy={policy.exists()}",
            "Add a PreToolUse guard and policy for agent control-plane config writes.",
        ))
        return ProbeResult("protected_config_write_guard", "FAIL", "hook/policy missing")
    return ProbeResult("protected_config_write_guard", "PASS", "protected config write hook and manifest exist")


def probe_network_egress_guard(findings: list[Finding]) -> ProbeResult:
    hook = REPO_ROOT / "hooks" / "network-egress-guard.sh"
    policy = REPO_ROOT / "manifests" / "network-egress-policy.yaml"
    if not hook.exists() or not policy.exists():
        findings.append(Finding(
            "network_egress_guard_missing",
            "HIGH",
            "Network egress guard is missing",
            f"hook={hook.exists()} policy={policy.exists()}",
            "Add a PreToolUse network egress guard and allowlist policy.",
        ))
        return ProbeResult("network_egress_guard", "FAIL", "hook/policy missing")
    return ProbeResult("network_egress_guard", "PASS", "network egress hook and allowlist manifest exist")


def probe_mcp_tofu_pinning(findings: list[Finding]) -> ProbeResult:
    manifest = REPO_ROOT / "manifests" / "mcp-trust-pins.yaml"
    script = REPO_ROOT / "scripts" / "mcp_tofu_audit.py"
    if not manifest.exists() or not script.exists():
        findings.append(Finding(
            "mcp_tofu_pinning_missing",
            "MEDIUM",
            "MCP trust-on-first-use pinning is missing",
            f"manifest={manifest.exists()} script={script.exists()}",
            "Add MCP trust pins and an audit that fingerprints command/args/env key names.",
        ))
        return ProbeResult("mcp_tofu_pinning", "WARN", "manifest/script missing")
    return ProbeResult("mcp_tofu_pinning", "PASS", "MCP trust pins manifest and audit script exist")


def probe_dangerous_env_flag_detector(findings: list[Finding]) -> ProbeResult:
    script = REPO_ROOT / "scripts" / "dangerous_env_flag_detector.py"
    hook = REPO_ROOT / "hooks" / "dangerous-env-flag-detector.sh"
    if not script.exists() or not hook.exists():
        findings.append(Finding("dangerous_env_flag_detector_missing", "MEDIUM", "Dangerous env flag detector is missing", f"script={script.exists()} hook={hook.exists()}", "Add active dangerous env flag posture detection."))
        return ProbeResult("dangerous_env_flag_detector", "WARN", "script/hook missing")
    return ProbeResult("dangerous_env_flag_detector", "PASS", "dangerous env flag detector script and hook exist")


def probe_network_sandbox_runner(findings: list[Finding]) -> ProbeResult:
    script = REPO_ROOT / "scripts" / "network_sandbox_run.py"
    if not script.exists():
        findings.append(Finding("network_sandbox_runner_missing", "HIGH", "Network sandbox runner is missing", str(script), "Add a real no-network sandbox runner for high-risk commands."))
        return ProbeResult("network_sandbox_runner", "FAIL", "script missing")
    return ProbeResult("network_sandbox_runner", "PASS", "docker --network none sandbox runner exists")


def probe_metrics_tamper_audit(findings: list[Finding]) -> ProbeResult:
    script = REPO_ROOT / "scripts" / "metrics_tamper_audit.py"
    if not script.exists():
        findings.append(Finding("metrics_tamper_audit_missing", "MEDIUM", "Metrics tamper audit is missing", str(script), "Add JSONL tamper detection for security-relevant metrics."))
        return ProbeResult("metrics_tamper_audit", "WARN", "script missing")
    return ProbeResult("metrics_tamper_audit", "PASS", "metrics tamper audit exists")


def probe_provider_spoof_audit(findings: list[Finding]) -> ProbeResult:
    script = REPO_ROOT / "scripts" / "provider_spoof_audit.py"
    if not script.exists():
        findings.append(Finding("provider_spoof_audit_missing", "MEDIUM", "Provider spoof audit is missing", str(script), "Add provider proof spoof detection for llm-dispatch metrics."))
        return ProbeResult("provider_spoof_audit", "WARN", "script missing")
    return ProbeResult("provider_spoof_audit", "PASS", "provider spoof audit exists")


def run_probes() -> tuple[list[ProbeResult], list[Finding]]:
    findings: list[Finding] = []
    probes = [
        probe_credential_safe_integrity,
        probe_credential_safe_env_boundary,
        probe_blocked_path_policy,
        probe_redteam_scenario_coverage,
        probe_scanner_hook_presence,
        probe_runtime_flag_registry,
        probe_mcp_security_surface,
        probe_runtime_sensitive_file_deny,
        probe_protected_config_write_guard,
        probe_network_egress_guard,
        probe_mcp_tofu_pinning,
        probe_dangerous_env_flag_detector,
        probe_network_sandbox_runner,
        probe_metrics_tamper_audit,
        probe_provider_spoof_audit,
    ]
    return [probe(findings) for probe in probes], findings


def threat_model() -> list[dict[str, str]]:
    return [
        {"id": "secret_exfiltration", "attacker_goal": "Extract .env, tokens, SSH/cloud/browser credentials", "primary_controls": "blocked paths, credential-safe runner, redaction, scanner hooks", "residual_risk": "danger-full-access is not an OS sandbox"},
        {"id": "tool_poisoning", "attacker_goal": "Trick MCP/hooks/skills into executing malicious tools", "primary_controls": "mcp-scan, manifest contracts, command integrity pins", "residual_risk": "new tools need explicit allowlist review"},
        {"id": "prompt_injection", "attacker_goal": "Override system/user rules through untrusted content", "primary_controls": "Parry, Aguara, red-team skill, memory-scan", "residual_risk": "ML/rule scanners are advisory or optional when tools are absent"},
        {"id": "governance_bypass", "attacker_goal": "Disable hooks, safe modes, tests, or fallback controls", "primary_controls": "runtime env flag registry, hook profiles, audit logs", "residual_risk": "operator-set env flags remain powerful"},
        {"id": "false_done", "attacker_goal": "Claim verified/tested/done without evidence", "primary_controls": "redteam-harness, plan-claim-validator, DoD/adversarial review", "residual_risk": "manual review still needed for novel claims"},
        {"id": "supply_chain", "attacker_goal": "Install malicious packages/plugins/skills", "primary_controls": "supply-chain-defense rule, protected install surfaces, SAST", "residual_risk": "optional installers and npx/pip flows need continuous review"},
    ]


def score_primitives(probes: list[ProbeResult]) -> list[PrimitiveScore]:
    probe_status = {probe.id: probe.status for probe in probes}

    def score(name: str, dims: dict[str, int], notes: list[str]) -> PrimitiveScore:
        return PrimitiveScore(name, round(sum(dims.values()) / len(dims)), dims, notes)

    credential_integrity = 90 if probe_status.get("credential_safe_integrity") == "PASS" else 40
    credential_boundary = 90 if probe_status.get("credential_safe_env_boundary") == "PASS" else 45
    scenario_score = 80 if probe_status.get("redteam_scenario_coverage") == "PASS" else 55
    scanner_score = 75 if probe_status.get("scanner_hook_presence") == "PASS" else 35
    flags_score = 80 if probe_status.get("runtime_flag_registry") == "PASS" else 50

    return [
        score("credential-safe-runner", {
            "isolation_strength": 55,
            "secret_handling": credential_boundary,
            "auditability": 85,
            "tamper_resistance": credential_integrity,
            "least_privilege": credential_boundary,
            "test_coverage": 85,
            "failure_mode_clarity": 85,
            "operator_ergonomics": 70,
        }, ["Operational boundary only; not a substitute for OS sandboxing."]),
        score("redteam-harness", {
            "isolation_strength": 60,
            "secret_handling": 65,
            "auditability": 80,
            "tamper_resistance": 70,
            "least_privilege": 75,
            "test_coverage": scenario_score,
            "failure_mode_clarity": 80,
            "operator_ergonomics": 75,
        }, ["Strong false-done coverage; needs more security-specific scenarios."]),
        score("prompt-injection-scanners", {
            "isolation_strength": 50,
            "secret_handling": 70,
            "auditability": 75,
            "tamper_resistance": 55,
            "least_privilege": 70,
            "test_coverage": scanner_score,
            "failure_mode_clarity": 65,
            "operator_ergonomics": 65,
        }, ["Parry/Aguara availability is tool-dependent; graceful skip is useful but can hide absence."]),
        score("mcp-security-surface", {
            "isolation_strength": 55,
            "secret_handling": 65,
            "auditability": 75,
            "tamper_resistance": 70,
            "least_privilege": 65,
            "test_coverage": scanner_score,
            "failure_mode_clarity": 70,
            "operator_ergonomics": 65,
        }, ["MCP and host CLI bridges need continuous allowlist and credential-store review."]),
        score("runtime-env-flag-governance", {
            "isolation_strength": 50,
            "secret_handling": 65,
            "auditability": 70,
            "tamper_resistance": flags_score,
            "least_privilege": 60,
            "test_coverage": flags_score,
            "failure_mode_clarity": 75,
            "operator_ergonomics": 80,
        }, ["Central registry exists, but powerful bypass flags remain operator-controlled."]),
    ]


def backlog(findings: list[Finding], scores: list[PrimitiveScore]) -> list[dict[str, str]]:
    items = []
    for finding in findings:
        items.append({
            "priority": finding.severity,
            "title": finding.title,
            "action": finding.recommendation,
            "source": finding.id,
        })
    for score in scores:
        if score.score < 75:
            items.append({
                "priority": "MEDIUM",
                "title": f"Raise {score.primitive} score above 75",
                "action": "; ".join(score.notes),
                "source": f"score/{score.primitive}",
            })
    return items


def overall_score(findings: list[Finding], scores: list[PrimitiveScore], manifest: dict[str, Any]) -> int:
    base = round(sum(score.score for score in scores) / len(scores)) if scores else 0
    weights = manifest.get("severity_weights", {})
    penalty = sum(int(weights.get(finding.severity, 0)) for finding in findings)
    return max(0, min(100, base - penalty))


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Cognitive OS Security Red-Team Report",
        "",
        f"**Generated**: {report['timestamp']}",
        f"**Overall score**: {report['overall_score']}/100",
        "",
        "## Surface Inventory",
        "",
        "| Surface | Exists | Files | Path |",
        "|---|---:|---:|---|",
    ]
    for name, item in report["surface_inventory"].items():
        lines.append(f"| `{name}` | {item['exists']} | {item['files']} | `{item['path']}` |")
    lines.extend(["", "## Probe Results", "", "| Probe | Status | Evidence |", "|---|---|---|"])
    for probe in report["probes"]:
        lines.append(f"| `{probe['id']}` | **{probe['status']}** | {probe['evidence']} |")
    lines.extend(["", "## Threat Model", ""])
    for threat in report["threat_model"]:
        lines.append(f"### {threat['id']}")
        lines.append(f"- **Attacker goal**: {threat['attacker_goal']}")
        lines.append(f"- **Primary controls**: {threat['primary_controls']}")
        lines.append(f"- **Residual risk**: {threat['residual_risk']}")
        lines.append("")
    lines.extend(["## Primitive Scores", "", "| Primitive | Score | Notes |", "|---|---:|---|"])
    for score in report["primitive_scores"]:
        lines.append(f"| `{score['primitive']}` | {score['score']} | {'; '.join(score['notes'])} |")
    lines.extend(["", "## Findings", ""])
    if report["findings"]:
        for finding in report["findings"]:
            lines.append(f"### [{finding['severity']}] {finding['title']}")
            lines.append(f"- **ID**: `{finding['id']}`")
            lines.append(f"- **Evidence**: {finding['evidence']}")
            lines.append(f"- **Recommendation**: {finding['recommendation']}")
            lines.append("")
    else:
        lines.append("No blocking findings from deterministic local probes.")
        lines.append("")
    lines.extend(["## Mitigation Backlog", ""])
    if report["mitigation_backlog"]:
        for item in report["mitigation_backlog"]:
            lines.append(f"- **{item['priority']}** `{item['source']}` — {item['title']}: {item['action']}")
    else:
        lines.append("No mitigation backlog items generated.")
    lines.append("")
    return "\n".join(lines)


def build_report(manifest_path: Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    manifest = _read_yaml(manifest_path)
    probes, findings = run_probes()
    scores = score_primitives(probes)
    report = {
        "schema_version": "security-red-team-report.v1",
        "timestamp": _utc(),
        "manifest": str(manifest_path.relative_to(REPO_ROOT) if manifest_path.is_relative_to(REPO_ROOT) else manifest_path),
        "surface_inventory": inventory_surface(),
        "threat_model": threat_model(),
        "probes": [asdict(probe) for probe in probes],
        "findings": [asdict(finding) for finding in findings],
        "primitive_scores": [asdict(score) for score in scores],
        "mitigation_backlog": backlog(findings, scores),
    }
    report["overall_score"] = overall_score(findings, scores, manifest)
    return report


def write_report(report: dict[str, Any], out_dir: Path = DEFAULT_OUT_DIR) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "security-red-team-latest.json"
    md_path = out_dir / "security-red-team-latest.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run deterministic Cognitive OS security red-team probes")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--json", action="store_true", help="Print report JSON to stdout")
    parser.add_argument("--fail-on", choices=["none", "critical", "high", "medium", "low"], default="critical")
    args = parser.parse_args(argv)

    report = build_report(Path(args.manifest))
    json_path, md_path = write_report(report, Path(args.out_dir))
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"security-red-team: score={report['overall_score']} json={json_path} markdown={md_path}")

    order = {"none": 99, "critical": 0, "high": 1, "medium": 2, "low": 3}
    severity_rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    threshold = order[args.fail_on]
    if threshold != 99 and any(severity_rank[f["severity"]] <= threshold for f in report["findings"]):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
