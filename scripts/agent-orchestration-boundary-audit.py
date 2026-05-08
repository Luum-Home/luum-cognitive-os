#!/usr/bin/env python3
"""Audit the ADR-251 agent orchestration adapter boundary.

Read-only: verifies that multi-agent orchestration stays declared, adapterized,
and does not silently import optional orchestration frameworks into COS core
hot-path files.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

SCHEMA_VERSION = "agent-orchestration-boundary-audit/v1"
DEFAULT_MANIFEST = Path("manifests/agent-orchestration-adapters.yaml")


@dataclass
class Finding:
    severity: str
    code: str
    message: str
    path: str | None = None
    adapter: str | None = None
    surface: str | None = None
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"severity": self.severity, "code": self.code, "message": self.message}
        if self.path:
            payload["path"] = self.path
        if self.adapter:
            payload["adapter"] = self.adapter
        if self.surface:
            payload["surface"] = self.surface
        if self.details:
            payload["details"] = self.details
        return payload


def repo_root(start: Path) -> Path:
    proc = subprocess.run(["git", "-C", str(start), "rev-parse", "--show-toplevel"], text=True, capture_output=True, check=False)
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


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _rel(path: Path, repo: Path) -> str:
    try:
        return path.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def declared_core_paths(manifest: dict[str, Any]) -> set[str]:
    paths = {str(path) for path in manifest.get("core_file_allowlist", []) or []}
    for surface in manifest.get("core_surfaces", []) or []:
        for path in _as_list(surface.get("implementations")):
            if path:
                paths.add(str(path))
    for adapter in manifest.get("adapters", []) or []:
        for path in _as_list(adapter.get("implementation")):
            if path and str(path) != "null":
                paths.add(str(path))
    return paths


def _scan_core_files(repo: Path, manifest: dict[str, Any]) -> list[str]:
    scan = manifest.get("unmanifested_core_file_scan") or {}
    scopes = [str(s) for s in scan.get("scopes", []) or []]
    regex = re.compile(str(scan.get("filename_regex", "^$")))
    suffixes = set(str(s) for s in scan.get("allowed_suffixes", []) or [])
    matches: list[str] = []
    for scope in scopes:
        base = repo / scope
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if suffixes and path.suffix not in suffixes:
                continue
            if regex.search(path.name):
                matches.append(_rel(path, repo))
    return sorted(set(matches))


def audit(repo: Path, manifest_path: Path) -> dict[str, Any]:
    manifest = load_yaml(manifest_path)
    findings: list[Finding] = []
    if manifest.get("schema_version") != "agent-orchestration-adapters/v1":
        findings.append(Finding("block", "manifest-schema-mismatch", "Agent orchestration adapter manifest schema_version is missing or unsupported.", path=str(manifest_path)))

    policy = manifest.get("policy") or {}
    for key in ["default_adapter", "cos_owns", "launch_paths_must_pass", "handoff_paths_must_pass", "provider_calls_must_pass"]:
        if not policy.get(key):
            findings.append(Finding("block", "policy-field-missing", "Agent orchestration policy is incomplete.", details={"missing_field": key}))

    adapters = list(manifest.get("adapters", []) or [])
    if not adapters:
        findings.append(Finding("block", "adapters-missing", "No agent orchestration adapters are declared."))
    default_adapters = [a for a in adapters if bool(a.get("default", False))]
    if len(default_adapters) != 1:
        findings.append(Finding("block", "default-adapter-cardinality", "Exactly one default orchestration adapter must be declared.", details={"count": len(default_adapters)}))
    elif policy.get("default_adapter") != default_adapters[0].get("id"):
        findings.append(
            Finding(
                "block",
                "default-adapter-policy-mismatch",
                "policy.default_adapter does not match the adapter marked default.",
                details={"policy_default": policy.get("default_adapter"), "adapter_default": default_adapters[0].get("id")},
            )
        )

    required_adapter_fields = ["id", "status", "default", "license_spdx", "footprint", "hot_path_allowed", "community_pattern", "benchmark_required"]
    for adapter in adapters:
        aid = str(adapter.get("id", "unknown"))
        for field in required_adapter_fields:
            if field not in adapter or adapter.get(field) in {None, ""}:
                findings.append(Finding("block", "adapter-field-missing", "Orchestration adapter declaration is incomplete.", adapter=aid, details={"missing_field": field}))
        if adapter.get("status") in {"candidate", "lab"} and not adapter.get("references"):
            findings.append(Finding("warn", "adapter-reference-missing", "Candidate/lab orchestration adapter should cite upstream documentation.", adapter=aid))
        for impl in _as_list(adapter.get("implementation")):
            if impl and str(impl) != "null" and not (repo / str(impl)).exists():
                findings.append(Finding("block", "adapter-implementation-missing", "Declared adapter implementation path does not exist.", adapter=aid, path=str(impl)))

    declared = declared_core_paths(manifest)
    forbidden = manifest.get("forbidden_core_imports", []) or []
    for relpath in sorted(declared):
        path = repo / relpath
        if path.suffix != ".py" or not path.exists():
            continue
        try:
            roots = imported_roots(path)
        except SyntaxError as exc:
            findings.append(Finding("block", "python-parse-error", "Declared orchestration core Python file could not be parsed.", path=relpath, details={"error": str(exc)}))
            continue
        for item in forbidden:
            module = str(item.get("module", ""))
            root = module.split(".", 1)[0]
            if root and root in roots:
                findings.append(
                    Finding(
                        "block",
                        "forbidden-core-orchestration-import",
                        "Core COS orchestration file imports an optional orchestration framework directly instead of through an adapter.",
                        path=relpath,
                        details={"module": module, "rationale": item.get("rationale")},
                    )
                )

    for relpath in _scan_core_files(repo, manifest):
        if relpath not in declared:
            findings.append(
                Finding(
                    "block",
                    "unmanifested-orchestration-core-file",
                    "Potential orchestration core file is not declared in the ADR-251 manifest.",
                    path=relpath,
                )
            )

    surfaces = list(manifest.get("core_surfaces", []) or [])
    if not surfaces:
        findings.append(Finding("block", "core-surfaces-missing", "No COS-owned orchestration core surfaces are declared."))
    for surface in surfaces:
        sid = str(surface.get("id", "unknown"))
        for field in ["id", "owner_adr", "kind", "implementations", "required_tests", "required_receipts"]:
            if not surface.get(field):
                findings.append(Finding("block", "surface-field-missing", "Orchestration core surface declaration is incomplete.", surface=sid, details={"missing_field": field}))
        for impl in _as_list(surface.get("implementations")):
            if impl and not (repo / str(impl)).exists():
                findings.append(Finding("block", "surface-implementation-missing", "Declared core surface implementation path does not exist.", surface=sid, path=str(impl)))
        for test in _as_list(surface.get("required_tests")):
            if test and not (repo / str(test)).exists():
                findings.append(Finding("block", "surface-test-missing", "Declared core surface test path does not exist.", surface=sid, path=str(test)))

    bench = manifest.get("benchmark") or {}
    script = bench.get("script")
    if not script or not (repo / str(script)).exists():
        findings.append(Finding("block", "benchmark-script-missing", "Benchmark script declared by manifest is missing.", path=str(script) if script else None))
    fixtures = list(bench.get("fixtures", []) or [])
    if not fixtures:
        findings.append(Finding("block", "benchmark-fixtures-missing", "Agent orchestration benchmark has no fixtures."))
    else:
        required_ids = {"write-agent-worktree-no-stash", "handoff-cycle-detected", "receiver-kill-mid-dispatch-receipt", "dispatch-budget-pre-call-refusal", "file-ipc-cross-session-flow"}
        present_ids = {str(f.get("id")) for f in fixtures}
        for missing in sorted(required_ids - present_ids):
            findings.append(Finding("block", "benchmark-required-fixture-missing", "Required historical orchestration fixture is missing.", details={"fixture_id": missing}))
        for fixture in fixtures:
            fid = str(fixture.get("id", "unknown"))
            if not fixture.get("id") or not fixture.get("evidence_tests") or not fixture.get("required_patterns"):
                findings.append(Finding("block", "benchmark-fixture-incomplete", "Benchmark fixture must declare id, evidence_tests, and required_patterns.", details={"fixture_id": fid}))
            for test in _as_list(fixture.get("evidence_tests")):
                if test and not (repo / str(test)).exists():
                    findings.append(Finding("block", "benchmark-evidence-test-missing", "Benchmark evidence test path does not exist.", path=str(test), details={"fixture_id": fid}))

    items = [f.to_dict() for f in findings]
    block = sum(1 for f in items if f["severity"] == "block")
    warn = sum(1 for f in items if f["severity"] == "warn")
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "block" if block else "warn" if warn else "pass",
        "policy": "Read-only. Enforce agent orchestration adapter boundary; do not mutate runtime, branches, worktrees, or dispatch state.",
        "summary": {"block": block, "warn": warn, "findings": len(items), "adapters": len(adapters), "surfaces": len(surfaces), "fixtures": len(fixtures)},
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
        print(f"agent-orchestration-boundary-audit: {report['status']} {report['summary']}")
        for finding in report["findings"]:
            print(f"[{finding['severity']}] {finding['code']}: {finding['message']}")
    return 1 if report["summary"]["block"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
