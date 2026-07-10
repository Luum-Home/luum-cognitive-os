"""ADR-206 public claim decommission gate."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


SCHEMA_VERSION = "public-claim-gate-report/v1"


@dataclass(frozen=True)
class ClaimFinding:
    path: str
    line: int
    pattern: str
    text: str
    severity: str = "block"

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "line": self.line,
            "pattern": self.pattern,
            "text": self.text,
            "severity": self.severity,
        }


def load_manifest(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if payload.get("schema_version") != "public-claim-evidence/v1":
        raise ValueError(f"invalid public claim evidence manifest: {path}")
    return payload


def _matches(text: str, patterns: list[str]) -> str | None:
    lowered = text.lower()
    for pattern in patterns:
        if re.search(re.escape(pattern.lower()), lowered):
            return pattern
    return None


def scan(project_dir: Path, manifest_path: Path | None = None) -> dict[str, Any]:
    manifest_file = manifest_path or project_dir / "manifests" / "public-claim-evidence.yaml"
    manifest = load_manifest(manifest_file)
    scope = manifest.get("scope", {}) or {}
    policy = manifest.get("policy", {}) or {}
    include = [str(item) for item in scope.get("include", [])]
    exclude = {str(item) for item in scope.get("exclude", [])}
    high_risk = [str(item) for item in policy.get("high_risk_patterns", [])]
    allowed = [str(item) for item in policy.get("allowed_context_patterns", [])]
    findings: list[ClaimFinding] = []
    scanned: list[str] = []

    for rel in include:
        if rel in exclude:
            continue
        path = project_dir / rel
        if not path.exists() or not path.is_file():
            continue
        scanned.append(rel)
        for line_number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            matched = _matches(line, high_risk)
            if matched is None:
                continue
            if _matches(line, allowed) is not None:
                continue
            findings.append(ClaimFinding(rel, line_number, matched, line.strip()))

    return {
        "schema_version": SCHEMA_VERSION,
        "status": "fail" if findings else "pass",
        "project_dir": str(project_dir),
        "manifest": str(manifest_file),
        "scanned_paths": scanned,
        "finding_count": len(findings),
        "findings": [finding.to_dict() for finding in findings],
        "policy": "High-risk autonomous/self-improvement claims must be removed, demoted, or explicitly bounded by REAL/propose-only/governed context.",
    }

