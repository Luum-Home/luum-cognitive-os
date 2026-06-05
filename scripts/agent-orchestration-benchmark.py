#!/usr/bin/env python3
# SCOPE: os-only
"""Run the ADR-251 agent orchestration boundary benchmark fixtures.

The benchmark is static and cheap by design. It verifies that historical
orchestration failure modes have executable evidence tests before an adapter or
substrate is treated as safe to extend.
"""
from __future__ import annotations
import os as _cos_os
import sys as _cos_sys
_cos_sys.path.insert(0, _cos_os.path.dirname(_cos_os.path.dirname(__file__)))
import sys
from lib.script_helpers import read_yaml_dict as load_yaml
from lib.script_helpers import repo_root

import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from typing import Any

import yaml

SCHEMA_VERSION = "agent-orchestration-benchmark/v1"
DEFAULT_MANIFEST = Path("manifests/agent-orchestration-adapters.yaml")


def evaluate_fixture(repo: Path, fixture: dict[str, Any]) -> dict[str, Any]:
    texts: dict[str, str] = {}
    missing_files: list[str] = []
    for relpath in fixture.get("evidence_tests", []) or []:
        path = repo / str(relpath)
        if not path.exists():
            missing_files.append(str(relpath))
            continue
        texts[str(relpath)] = path.read_text(encoding="utf-8", errors="replace")
    combined = "\n".join(texts.values())
    missing_patterns = [str(pattern) for pattern in fixture.get("required_patterns", []) or [] if str(pattern) not in combined]
    passed = not missing_files and not missing_patterns
    return {
        "id": fixture.get("id"),
        "required": bool(fixture.get("required", True)),
        "known_gap": bool(fixture.get("known_gap", False)),
        "passed": passed,
        "evidence_tests": list(texts.keys()),
        "missing_files": missing_files,
        "missing_patterns": missing_patterns,
        "rationale": fixture.get("rationale"),
    }


def benchmark(repo: Path, manifest_path: Path) -> dict[str, Any]:
    manifest = load_yaml(manifest_path)
    fixtures = list((manifest.get("benchmark") or {}).get("fixtures", []) or [])
    results = [evaluate_fixture(repo, fixture) for fixture in fixtures]
    required_failures = [r for r in results if r["required"] and not r["passed"]]
    known_gap_failures = [r for r in results if r["known_gap"] and not r["passed"]]
    optional_failures = [r for r in results if not r["required"] and not r["known_gap"] and not r["passed"]]
    status = "block" if required_failures else "warn" if known_gap_failures or optional_failures else "pass"
    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "adapter": (manifest.get("policy") or {}).get("default_adapter", "unknown"),
        "summary": {
            "fixtures": len(results),
            "passed": sum(1 for r in results if r["passed"]),
            "required_failures": len(required_failures),
            "known_gap_failures": len(known_gap_failures),
            "optional_failures": len(optional_failures),
        },
        "results": results,
        "findings": [
            {
                "severity": "block" if r["required"] else "warn",
                "code": "orchestration-benchmark-missing-proof",
                "fixture_id": r["id"],
                "message": "Agent orchestration benchmark fixture lacks required executable evidence.",
                "missing_files": r["missing_files"],
                "missing_patterns": r["missing_patterns"],
                "known_gap": r["known_gap"],
            }
            for r in results
            if not r["passed"]
        ],
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
    report = benchmark(root, manifest)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"agent-orchestration-benchmark: {report['status']} {report['summary']}")
        for result in report["results"]:
            marker = "PASS" if result["passed"] else "FAIL"
            print(f"[{marker}] {result['id']}: missing_files={result['missing_files']} missing_patterns={result['missing_patterns']}")
    return 1 if report["summary"]["required_failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
