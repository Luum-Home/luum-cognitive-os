#!/usr/bin/env python3
# SCOPE: os-only
"""Audit the ADR-250 skill-router retrieval adapter boundary.

Read-only: verifies that router retrieval/ranking remains declared, adapterized,
and not silently replaced by heavy community stacks in the hot-path router.
"""
from __future__ import annotations

import argparse
import ast
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

SCHEMA_VERSION = "skill-router-retrieval-audit/v1"
DEFAULT_MANIFEST = Path("manifests/skill-router-retrieval.yaml")


@dataclass
class Finding:
    severity: str
    code: str
    message: str
    path: str | None = None
    adapter: str | None = None
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"severity": self.severity, "code": self.code, "message": self.message}
        if self.path:
            payload["path"] = self.path
        if self.adapter:
            payload["adapter"] = self.adapter
        if self.details:
            payload["details"] = self.details
        return payload


def repo_root(start: Path) -> Path:
    proc = subprocess.run(["git", "-C", str(start), "rev-parse", "--show-toplevel"], text=True, capture_output=True, check=False, timeout=60)
    if proc.returncode == 0 and proc.stdout.strip():
        return Path(proc.stdout.strip()).resolve()
    return start.resolve()


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


def audit(repo: Path, manifest_path: Path) -> dict[str, Any]:
    manifest = load_yaml(manifest_path)
    findings: list[Finding] = []
    if manifest.get("schema_version") != "skill-router-retrieval/v1":
        findings.append(Finding("block", "manifest-schema-mismatch", "Skill-router retrieval manifest schema_version is missing or unsupported.", path=str(manifest_path)))

    policy = manifest.get("policy") or {}
    core_router = repo / str(policy.get("core_router", "lib/skill_router.py"))
    if not core_router.exists():
        findings.append(Finding("block", "core-router-missing", "Declared core skill router file does not exist.", path=str(core_router)))
    else:
        roots = imported_roots(core_router)
        forbidden = manifest.get("forbidden_core_imports", []) or []
        for item in forbidden:
            module = str(item.get("module", ""))
            root = module.split(".", 1)[0]
            if root and root in roots:
                findings.append(
                    Finding(
                        "block",
                        "forbidden-core-retrieval-import",
                        "Core skill router imports an optional retrieval stack directly instead of through an adapter.",
                        path=str(policy.get("core_router", "lib/skill_router.py")),
                        details={"module": module, "rationale": item.get("rationale")},
                    )
                )

    adapters = list(manifest.get("adapters", []) or [])
    if not adapters:
        findings.append(Finding("block", "adapters-missing", "No retrieval adapters are declared."))
    default_adapters = [a for a in adapters if bool(a.get("default", False))]
    if len(default_adapters) != 1:
        findings.append(Finding("block", "default-adapter-cardinality", "Exactly one default retrieval adapter must be declared.", details={"count": len(default_adapters)}))
    default_id = policy.get("default_adapter")
    if default_adapters and default_id != default_adapters[0].get("id"):
        findings.append(Finding("block", "default-adapter-policy-mismatch", "policy.default_adapter does not match the adapter marked default.", details={"policy_default": default_id, "adapter_default": default_adapters[0].get("id")}))

    required_fields = ["id", "status", "default", "license_spdx", "footprint", "hot_path_allowed", "community_pattern", "benchmark_required"]
    for adapter in adapters:
        aid = str(adapter.get("id", "unknown"))
        for field in required_fields:
            if field not in adapter or adapter.get(field) in {None, ""}:
                findings.append(Finding("block", "adapter-field-missing", "Retrieval adapter declaration is incomplete.", adapter=aid, details={"missing_field": field}))
        if adapter.get("status") in {"candidate", "lab"} and not adapter.get("references") and aid not in {"bm25_local"}:
            findings.append(Finding("warn", "adapter-reference-missing", "Candidate/lab community adapter should cite upstream documentation.", adapter=aid))
        impl = adapter.get("implementation")
        if impl and str(impl) != "null" and not (repo / str(impl)).exists():
            findings.append(Finding("block", "adapter-implementation-missing", "Declared adapter implementation path does not exist.", adapter=aid, path=str(impl)))

    bench = manifest.get("benchmark") or {}
    script = bench.get("script")
    if not script or not (repo / str(script)).exists():
        findings.append(Finding("block", "benchmark-script-missing", "Benchmark script declared by manifest is missing.", path=str(script) if script else None))
    fixtures = list(bench.get("fixtures", []) or [])
    if not fixtures:
        findings.append(Finding("block", "benchmark-fixtures-missing", "Skill-router retrieval benchmark has no fixtures."))
    else:
        has_false_positive = any(f.get("expected") == "none" for f in fixtures)
        has_positive = any(f.get("expected_command") for f in fixtures)
        if not has_false_positive:
            findings.append(Finding("block", "benchmark-false-positive-fixture-missing", "Benchmark must include at least one expected-none false-positive fixture."))
        if not has_positive:
            findings.append(Finding("block", "benchmark-positive-fixture-missing", "Benchmark must include at least one positive routing fixture."))
        for fixture in fixtures:
            if not fixture.get("id") or not fixture.get("prompt"):
                findings.append(Finding("block", "benchmark-fixture-incomplete", "Benchmark fixture is missing id or prompt.", details={"fixture": fixture}))
            if fixture.get("expected") != "none" and not fixture.get("expected_command"):
                findings.append(Finding("block", "benchmark-fixture-expectation-missing", "Benchmark fixture must declare expected:none or expected_command.", details={"id": fixture.get("id")}))

    items = [f.to_dict() for f in findings]
    block = sum(1 for f in items if f["severity"] == "block")
    warn = sum(1 for f in items if f["severity"] == "warn")
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "block" if block else "warn" if warn else "pass",
        "policy": "Read-only. Enforce skill-router retrieval adapter boundary; do not mutate router or benchmarks.",
        "summary": {"block": block, "warn": warn, "findings": len(items), "adapters": len(adapters), "fixtures": len(fixtures)},
        "findings": items,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = repo_root(Path(args.project_dir))
    manifest = Path(args.manifest)
    if not manifest.is_absolute():
        manifest = root / manifest
    report = audit(root, manifest)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"skill-router-retrieval-audit: {report['status']} {report['summary']}")
        for finding in report["findings"]:
            print(f"[{finding['severity']}] {finding['code']}: {finding['message']}")
    return 1 if report["summary"]["block"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
