"""Cross-stack license audit policy checks for ADR-212."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


SCHEMA_VERSION = "cross-stack-license-audit-report/v1"
DEFAULT_MANIFEST = Path("manifests/cross-stack-license-audit.yaml")
COMMIT_SHA_RE = re.compile(r"^[a-f0-9]{40}$")


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    message: str
    path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {"severity": self.severity, "code": self.code, "message": self.message}
        if self.path:
            payload["path"] = self.path
        return payload


def load_policy(project_dir: Path) -> dict[str, Any]:
    manifest = project_dir / DEFAULT_MANIFEST
    if not manifest.exists():
        return {
            "schema_version": "cross-stack-license-audit/v1",
            "primary": {"tools": ["syft", "grype"]},
            "secondary": {
                "denied_versions": ["0.69.4", "0.69.5", "0.69.6"],
                "denied_workflow_actions": ["aquasecurity/trivy-action", "aquasecurity/setup-trivy"],
                "require_immutable_workflow_pin": True,
            },
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
    tool_names = set(policy.get("primary", {}).get("tools", [])) | {"trivy"}
    versions: dict[str, dict[str, Any]] = {}
    for tool in sorted(tool_names):
        path = shutil.which(tool)
        info: dict[str, Any] = {"installed": bool(path), "path": path, "version": None}
        if path:
            if tool == "trivy":
                output = _run([tool, "--version"])
            else:
                output = _run([tool, "version"])
            info["version"] = output.splitlines()[0] if output else None
        versions[tool] = info
    return versions


def extract_version(text: str | None) -> str | None:
    if not text:
        return None
    match = re.search(r"v?(\d+\.\d+\.\d+)", text)
    return match.group(1) if match else None


def classify_trivy_version(version_output: str | None, policy: dict[str, Any]) -> Finding | None:
    version = extract_version(version_output)
    if not version:
        return None
    denied = set(policy.get("secondary", {}).get("denied_versions", []))
    if version in denied:
        return Finding(
            severity="block",
            code="blocked-trivy-version",
            message=f"Trivy version {version} is denied by ADR-212 supply-chain policy.",
        )
    return None


def _workflow_files(project_dir: Path) -> list[Path]:
    workflows = project_dir / ".github" / "workflows"
    if not workflows.exists():
        return []
    return sorted(path for path in workflows.rglob("*.y*ml") if path.is_file())


def _action_refs(text: str, action: str) -> list[str]:
    refs: list[str] = []
    pattern = re.compile(rf"uses:\s*{re.escape(action)}@([^\s#]+)")
    for match in pattern.finditer(text):
        refs.append(match.group(1).strip().strip('"\''))
    return refs


def audit_workflows(project_dir: Path, policy: dict[str, Any]) -> list[Finding]:
    secondary = policy.get("secondary", {})
    denied_actions = secondary.get("denied_workflow_actions", [])
    require_sha = bool(secondary.get("require_immutable_workflow_pin", True))
    findings: list[Finding] = []
    for workflow in _workflow_files(project_dir):
        text = workflow.read_text(encoding="utf-8", errors="replace")
        rel = str(workflow.relative_to(project_dir))
        for action in denied_actions:
            refs = _action_refs(text, action)
            for ref in refs:
                if require_sha and not COMMIT_SHA_RE.match(ref):
                    findings.append(
                        Finding(
                            severity="block",
                            code="mutable-trivy-workflow-action",
                            message=(
                                f"{action}@{ref} is not an immutable reviewed commit pin. "
                                "ADR-212 blocks mutable Trivy actions after the 2026 supply-chain incident."
                            ),
                            path=rel,
                        )
                    )
    return findings


def audit(project_dir: Path) -> dict[str, Any]:
    root = project_dir.resolve()
    policy = load_policy(root)
    tools = installed_tool_versions(policy)
    findings = audit_workflows(root, policy)
    trivy_finding = classify_trivy_version(tools.get("trivy", {}).get("version"), policy)
    if trivy_finding:
        findings.append(trivy_finding)

    primary_tools = policy.get("primary", {}).get("tools", ["syft", "grype"])
    for tool in primary_tools:
        if not tools.get(tool, {}).get("installed"):
            findings.append(
                Finding(
                    severity="warn",
                    code="primary-tool-missing",
                    message=f"Primary audit tool '{tool}' is not installed; run scripts/install-syft-grype.sh before release audit.",
                )
            )

    status = "block" if any(f.severity == "block" for f in findings) else "warn" if findings else "pass"
    return {
        "schema_version": SCHEMA_VERSION,
        "project_dir": str(root),
        "status": status,
        "primary_toolchain": policy.get("primary", {}).get("toolchain", "syft-grype"),
        "secondary_toolchain": policy.get("secondary", {}).get("toolchain", "trivy"),
        "tools": tools,
        "findings": [finding.to_dict() for finding in findings],
    }


def format_human(report: dict[str, Any]) -> str:
    lines = [f"cross-stack-license-audit: {report['status']}"]
    lines.append(f"primary={report.get('primary_toolchain')} secondary={report.get('secondary_toolchain')}")
    for finding in report.get("findings", []):
        location = f" {finding['path']}:" if finding.get("path") else ""
        lines.append(f"[{finding['severity']}] {finding['code']}:{location} {finding['message']}")
    if not report.get("findings"):
        lines.append("No policy findings.")
    return "\n".join(lines)


def dumps_json(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)
