"""Cross-stack secret audit policy checks for ADR-215."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


SCHEMA_VERSION = "cross-stack-secret-audit-report/v1"
DEFAULT_MANIFEST = Path("manifests/cross-stack-secret-audit.yaml")
COMMIT_SHA_RE = re.compile(r"^[a-f0-9]{40}$")


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    message: str
    path: str | None = None
    classification: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"severity": self.severity, "code": self.code, "message": self.message}
        if self.path:
            payload["path"] = self.path
        if self.classification:
            payload["classification"] = self.classification
        return payload


def load_policy(project_dir: Path) -> dict[str, Any]:
    manifest = project_dir / DEFAULT_MANIFEST
    if not manifest.exists():
        return {
            "schema_version": "cross-stack-secret-audit/v1",
            "primary": {"toolchain": "gitleaks-trufflehog", "tools": ["gitleaks", "trufflehog"]},
            "workflow_policy": {"require_immutable_workflow_pin": True, "denied_mutable_actions": []},
            "policy": {"exclude_paths": [r"(^|/)\.git($|/)"], "secret_never_touch": [r"(^|/)\.env($|\.)"]},
        }
    return yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}


def _run(command: list[str]) -> str | None:
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return (result.stdout or result.stderr).strip()


def installed_tool_versions(policy: dict[str, Any]) -> dict[str, dict[str, Any]]:
    names = set(policy.get("primary", {}).get("tools", [])) | set(policy.get("secondary", {}).get("tools", []))
    versions: dict[str, dict[str, Any]] = {}
    for tool in sorted(names):
        path = shutil.which(tool)
        info: dict[str, Any] = {"installed": bool(path), "path": path, "version": None}
        if path:
            if tool == "gitleaks":
                output = _run([tool, "version"])
            elif tool == "trufflehog":
                output = _run([tool, "--version"])
            else:
                output = _run([tool, "--version"])
            info["version"] = output.splitlines()[0] if output else None
        versions[tool] = info
    return versions


def _workflow_files(project_dir: Path) -> list[Path]:
    workflows = project_dir / ".github" / "workflows"
    if not workflows.exists():
        return []
    return sorted(path for path in workflows.rglob("*.y*ml") if path.is_file())


def _action_refs(text: str, action: str) -> list[str]:
    action = action.split("@", 1)[0]
    pattern = re.compile(rf"uses:\s*{re.escape(action)}@([^\s#]+)")
    return [match.group(1).strip().strip('"\'') for match in pattern.finditer(text)]


def audit_workflows(project_dir: Path, policy: dict[str, Any]) -> list[Finding]:
    workflow_policy = policy.get("workflow_policy", {})
    require_sha = bool(workflow_policy.get("require_immutable_workflow_pin", True))
    actions = workflow_policy.get("denied_mutable_actions", [])
    findings: list[Finding] = []
    for workflow in _workflow_files(project_dir):
        text = workflow.read_text(encoding="utf-8", errors="replace")
        rel = str(workflow.relative_to(project_dir))
        for action in actions:
            for ref in _action_refs(text, str(action)):
                if require_sha and not COMMIT_SHA_RE.match(ref):
                    findings.append(
                        Finding(
                            severity="block",
                            code="mutable-secret-scanner-workflow-action",
                            message=(
                                f"{str(action).split('@', 1)[0]}@{ref} is not an immutable reviewed commit pin. "
                                "ADR-215 blocks mutable secret-scanner actions."
                            ),
                            path=rel,
                            classification="supply-chain",
                        )
                    )
    return findings


def _compiled(patterns: list[str]) -> list[re.Pattern[str]]:
    return [re.compile(pattern) for pattern in patterns]


def _matches_any(rel: str, patterns: list[re.Pattern[str]]) -> bool:
    return any(pattern.search(rel) for pattern in patterns)


def discover_sensitive_files(project_dir: Path, policy: dict[str, Any]) -> list[Finding]:
    policy_body = policy.get("policy", {})
    excludes = _compiled(list(policy_body.get("exclude_paths", [])))
    sensitive = _compiled(list(policy_body.get("secret_never_touch", [])))
    findings: list[Finding] = []
    for root, dirnames, filenames in os.walk(project_dir):
        root_path = Path(root)
        rel_root = root_path.relative_to(project_dir).as_posix() if root_path != project_dir else ""
        dirnames[:] = [d for d in dirnames if not _matches_any(f"{rel_root}/{d}" if rel_root else d, excludes)]
        for filename in filenames:
            path = root_path / filename
            rel = path.relative_to(project_dir).as_posix()
            if _matches_any(rel, excludes) or not _matches_any(rel, sensitive):
                continue
            findings.append(
                Finding(
                    severity="warn",
                    code="secret-never-touch-file-present",
                    message="Sensitive local file exists in the working tree. Do not commit, project, or export it without explicit operator approval.",
                    path=rel,
                    classification="local-sensitive-surface",
                )
            )
    return findings


def classify_external_finding(path: str, raw_value: str | None, policy: dict[str, Any]) -> str:
    policy_body = policy.get("policy", {})
    allowlist = _compiled(list(policy_body.get("placeholder_path_allowlist", [])))
    fingerprints = [str(item) for item in policy_body.get("placeholder_fingerprints", [])]
    if _matches_any(path, allowlist):
        return "placeholder"
    if raw_value == "[REDACTED]":
        return str(policy_body.get("unknown_unclassified_findings", "suspect"))
    if raw_value and any(token in raw_value for token in fingerprints):
        return "placeholder"
    if raw_value:
        return "valid"
    return str(policy_body.get("unknown_unclassified_findings", "suspect"))


def summarize_existing_reports(project_dir: Path, policy: dict[str, Any]) -> dict[str, Any]:
    output_dir = project_dir / policy.get("primary", {}).get("output_dir", ".cognitive-os/reports/secret-audit")
    summary: dict[str, Any] = {"output_dir": str(output_dir), "reports": []}
    if not output_dir.exists():
        return summary
    for path in sorted(output_dir.glob("*.json")):
        if path.name.startswith("cross-stack-secret-audit-latest"):
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(payload, list):
            rules: dict[str, int] = {}
            files: dict[str, int] = {}
            for item in payload:
                if not isinstance(item, dict):
                    continue
                rule = str(item.get("RuleID") or item.get("DetectorName") or "unknown")
                file_path = str(item.get("File") or item.get("SourceMetadata", {}).get("Data", {}).get("Filesystem", {}).get("file") or "unknown")
                rules[rule] = rules.get(rule, 0) + 1
                files[file_path] = files.get(file_path, 0) + 1
            summary["reports"].append(
                {
                    "path": str(path.relative_to(project_dir)),
                    "finding_count": len(payload),
                    "top_rules": sorted(rules.items(), key=lambda kv: kv[1], reverse=True)[:10],
                    "top_files": sorted(files.items(), key=lambda kv: kv[1], reverse=True)[:10],
                }
            )
    for path in sorted(output_dir.glob("*.jsonl")):
        if "raw" in path.name:
            continue
        count = 0
        detectors: dict[str, int] = {}
        files: dict[str, int] = {}
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            count += 1
            detector = str(item.get("DetectorName") or item.get("detector") or "unknown")
            file_path = str(item.get("SourceMetadata", {}).get("Data", {}).get("Filesystem", {}).get("file") or item.get("path") or "unknown")
            detectors[detector] = detectors.get(detector, 0) + 1
            files[file_path] = files.get(file_path, 0) + 1
        summary["reports"].append(
            {
                "path": str(path.relative_to(project_dir)),
                "finding_count": count,
                "top_rules": sorted(detectors.items(), key=lambda kv: kv[1], reverse=True)[:10],
                "top_files": sorted(files.items(), key=lambda kv: kv[1], reverse=True)[:10],
            }
        )
    return summary


def audit(project_dir: Path, *, verify_live: bool = False, include_local_sensitive_surfaces: bool = True) -> dict[str, Any]:
    root = project_dir.resolve()
    policy = load_policy(root)
    tools = installed_tool_versions(policy)
    findings = audit_workflows(root, policy)
    if include_local_sensitive_surfaces:
        findings.extend(discover_sensitive_files(root, policy))

    for tool in policy.get("primary", {}).get("tools", []):
        if not tools.get(tool, {}).get("installed"):
            findings.append(
                Finding(
                    severity="warn",
                    code="primary-tool-missing",
                    message=f"Primary secret audit tool '{tool}' is not installed; install the ADR-215 toolchain before release audit.",
                    classification="tooling",
                )
            )
    if verify_live:
        findings.append(
            Finding(
                severity="warn",
                code="live-verification-enabled",
                message="Live secret verification was explicitly requested. Ensure operator approval because providers may receive candidate secret material.",
                classification="privacy-risk",
            )
        )

    status = "block" if any(f.severity == "block" for f in findings) else "warn" if findings else "pass"
    return {
        "schema_version": SCHEMA_VERSION,
        "project_dir": str(root),
        "status": status,
        "primary_toolchain": policy.get("primary", {}).get("toolchain", "gitleaks-trufflehog"),
        "live_verification": bool(verify_live),
        "include_local_sensitive_surfaces": bool(include_local_sensitive_surfaces),
        "tools": tools,
        "findings": [finding.to_dict() for finding in findings],
        "existing_report_summary": summarize_existing_reports(root, policy),
    }


def write_latest_report(project_dir: Path, report: dict[str, Any], policy: dict[str, Any] | None = None) -> Path:
    effective_policy = policy or load_policy(project_dir)
    latest = project_dir / effective_policy.get("reporting", {}).get(
        "latest_report", ".cognitive-os/reports/secret-audit/cross-stack-secret-audit-latest.json"
    )
    latest.parent.mkdir(parents=True, exist_ok=True)
    latest.write_text(dumps_json(report) + "\n", encoding="utf-8")
    return latest


def format_human(report: dict[str, Any]) -> str:
    lines = [f"cross-stack-secret-audit: {report['status']}"]
    lines.append(f"primary={report.get('primary_toolchain')} live_verification={report.get('live_verification')}")
    for finding in report.get("findings", [])[:30]:
        location = f" {finding['path']}:" if finding.get("path") else ""
        lines.append(f"[{finding['severity']}] {finding['code']}:{location} {finding['message']}")
    remaining = len(report.get("findings", [])) - 30
    if remaining > 0:
        lines.append(f"... {remaining} additional findings omitted; use --json for full redacted metadata.")
    reports = report.get("existing_report_summary", {}).get("reports", [])
    if reports:
        lines.append("existing scanner reports:")
        for item in reports:
            lines.append(f"- {item['path']}: {item['finding_count']} redacted findings")
    if not report.get("findings") and not reports:
        lines.append("No policy findings and no existing scanner reports found.")
    return "\n".join(lines)


def dumps_json(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)
