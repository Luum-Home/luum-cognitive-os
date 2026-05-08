#!/usr/bin/env python3
"""Audit whether critical primitive tests prove behavior, not just existence.

ADR-249 Slice A is intentionally static and read-only. It scans declared proof
files for manifest-declared falsification evidence. It does not run heavy test
lanes and it does not repair tests.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

SCHEMA_VERSION = "primitive-behavior-audit/v1"
DEFAULT_MANIFEST = Path("manifests/primitive-behavior-contracts.yaml")

OVERFIT_SMELL_PATTERNS: dict[str, str] = {
    "existence-only": r"\.exists\(\)|Path\(",
    "syntax-only": r"bash[\"'],\s*[\"']-n|shellcheck",
    "grep-only": r"\bgrep\b|grep\s+-R|git\s+grep",
    "manifest-only": r"yaml\.safe_load|json\.loads|read_text\(",
}

BEHAVIOR_HINT_PATTERNS = [
    r"returncode\s*==\s*[12]",
    r"status\"?\]?\s*==\s*[\"']block",
    r"pytest\.raises",
    r"BLOCKED",
    r"fail[s]? closed",
    r"falsification",
]


@dataclass
class Finding:
    severity: str
    code: str
    message: str
    contract: str | None = None
    path: str | None = None
    evidence_id: str | None = None
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
        }
        if self.contract:
            payload["contract"] = self.contract
        if self.path:
            payload["path"] = self.path
        if self.evidence_id:
            payload["evidence_id"] = self.evidence_id
        if self.details:
            payload["details"] = self.details
        return payload


def repo_root(start: Path) -> Path:
    proc = subprocess.run(
        ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode == 0 and proc.stdout.strip():
        return Path(proc.stdout.strip()).resolve()
    return start.resolve()


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def regex_found(pattern: str, text: str) -> bool:
    try:
        return re.search(pattern, text, flags=re.MULTILINE | re.DOTALL) is not None
    except re.error:
        # Manifest regexes are part of the contract; invalid regex blocks.
        return False


def evidence_matches(evidence: dict[str, Any], aggregate: str) -> tuple[bool, list[str]]:
    patterns = [str(p) for p in evidence.get("patterns", []) or []]
    mode = str(evidence.get("match", "all"))
    matched = [pattern for pattern in patterns if regex_found(pattern, aggregate)]
    if mode == "any":
        return bool(matched), matched
    return len(matched) == len(patterns), matched


def file_has_behavior_hint(text: str) -> bool:
    return any(regex_found(pattern, text) for pattern in BEHAVIOR_HINT_PATTERNS)


def file_smells(text: str) -> list[str]:
    return [name for name, pattern in OVERFIT_SMELL_PATTERNS.items() if regex_found(pattern, text)]


def audit_contract(repo: Path, contract: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    cid = str(contract.get("id", "unknown"))
    proof_tests = [str(p) for p in contract.get("proof_tests", []) or []]
    if not proof_tests:
        findings.append(Finding("block", "proof-tests-missing", "Critical primitive contract declares no proof_tests.", contract=cid))
        return findings

    aggregate_parts: list[str] = []
    existing_files = 0
    for rel in proof_tests:
        path = repo / rel
        if not path.exists():
            findings.append(
                Finding(
                    "block",
                    "proof-test-file-missing",
                    "Declared behavioral proof test file does not exist.",
                    contract=cid,
                    path=rel,
                )
            )
            continue
        existing_files += 1
        text = read_text(path)
        aggregate_parts.append(f"\n# FILE: {rel}\n{text}")
        # File-level smells are collected after aggregate proof is evaluated.
        # Supplemental audit tests may intentionally validate manifests; they
        # are suspicious only when the whole contract lacks behavioral proof.
    if existing_files == 0:
        return findings

    aggregate = "\n".join(aggregate_parts)
    required = list(contract.get("required_evidence", []) or [])
    if not required:
        findings.append(
            Finding(
                "block",
                "required-evidence-missing",
                "Behavioral proof contract declares proof tests but no required_evidence.",
                contract=cid,
            )
        )
        return findings

    for evidence in required:
        eid = str(evidence.get("id", "unknown"))
        ok, matched = evidence_matches(evidence, aggregate)
        if not ok:
            findings.append(
                Finding(
                    str(evidence.get("severity", "block")),
                    "behavioral-evidence-missing",
                    "Declared behavioral proof evidence was not found in proof tests.",
                    contract=cid,
                    evidence_id=eid,
                    details={
                        "description": evidence.get("description"),
                        "patterns": evidence.get("patterns", []),
                        "matched": matched,
                        "match": evidence.get("match", "all"),
                    },
                )
            )

    # Cross-contract guard: every high criticality contract should have some
    # textual proof of failure semantics, even if the manifest forgot to ask.
    if str(contract.get("criticality", "")).lower() in {"high", "critical"} and not file_has_behavior_hint(aggregate):
        findings.append(
            Finding(
                "block",
                "fail-closed-proof-absent",
                "High-criticality primitive proof has no obvious fail-closed assertion.",
                contract=cid,
            )
        )
        for rel in proof_tests:
            path = repo / rel
            if path.exists():
                smells = file_smells(read_text(path))
                if smells:
                    findings.append(
                        Finding(
                            "warn",
                            "proof-test-overfit-smell",
                            "Proof file appears to test structure/existence without an obvious fail-closed behavioral assertion.",
                            contract=cid,
                            path=rel,
                            details={"smells": smells},
                        )
                    )
    return findings


def audit(repo: Path, manifest_path: Path) -> dict[str, Any]:
    manifest = load_yaml(manifest_path)
    findings: list[Finding] = []
    if manifest.get("schema_version") != "primitive-behavior-contracts/v1":
        findings.append(
            Finding(
                "block",
                "manifest-schema-mismatch",
                "Primitive behavior manifest schema_version is missing or unsupported.",
                details={"expected": "primitive-behavior-contracts/v1", "actual": manifest.get("schema_version")},
            )
        )
    contracts = list(manifest.get("contracts", []) or [])
    if not contracts:
        findings.append(Finding("block", "contracts-missing", "Primitive behavior manifest declares no contracts."))
    for contract in contracts:
        findings.extend(audit_contract(repo, contract))

    items = [finding.to_dict() for finding in findings]
    block = sum(1 for f in items if f.get("severity") == "block")
    warn = sum(1 for f in items if f.get("severity") == "warn")
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "block" if block else "warn" if warn else "pass",
        "policy": "Read-only. Verify behavioral proof and falsification evidence; do not auto-repair tests or primitives.",
        "manifest": str(manifest_path.relative_to(repo) if manifest_path.is_relative_to(repo) else manifest_path),
        "summary": {"block": block, "warn": warn, "findings": len(items), "contracts": len(contracts)},
        "findings": items,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = repo_root(Path(args.project_dir))
    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = root / manifest_path
    report = audit(root, manifest_path)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"primitive-behavior-audit: {report['status']} {report['summary']}")
        for finding in report["findings"]:
            print(f"[{finding['severity']}] {finding['code']}: {finding['message']}")
    return 1 if report["summary"]["block"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
