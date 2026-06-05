#!/usr/bin/env python3
# SCOPE: os-only
"""Run the ADR-250 minimal skill-router benchmark fixtures."""
from __future__ import annotations
import os as _cos_os
import sys as _cos_sys
_cos_sys.path.insert(0, _cos_os.path.dirname(_cos_os.path.dirname(__file__)))
from lib.script_helpers import read_yaml_dict as load_yaml
from lib.script_helpers import repo_root

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT_FOR_IMPORTS = Path(__file__).resolve().parents[1]
if str(ROOT_FOR_IMPORTS) not in sys.path:
    sys.path.insert(0, str(ROOT_FOR_IMPORTS))

from lib.skill_router import SkillRouter

SCHEMA_VERSION = "skill-router-benchmark/v1"
DEFAULT_MANIFEST = Path("manifests/skill-router-retrieval.yaml")


def evaluate_fixture(router: SkillRouter, fixture: dict[str, Any]) -> dict[str, Any]:
    prompt = str(fixture.get("prompt", ""))
    match = router.best_match(prompt)
    actual_command = match.invoke_command if match else None
    expected_none = fixture.get("expected") == "none"
    expected_command = fixture.get("expected_command")
    if expected_none:
        passed = actual_command is None
    else:
        passed = actual_command == expected_command
    return {
        "id": fixture.get("id"),
        "prompt": prompt,
        "required": bool(fixture.get("required", True)),
        "known_gap": bool(fixture.get("known_gap", False)),
        "expected": None if expected_none else expected_command,
        "actual": actual_command,
        "confidence": round(match.confidence, 3) if match else None,
        "skill_name": match.skill_name if match else None,
        "passed": passed,
        "rationale": fixture.get("rationale"),
    }


def benchmark(repo: Path, manifest_path: Path) -> dict[str, Any]:
    manifest = load_yaml(manifest_path)
    fixtures = list((manifest.get("benchmark") or {}).get("fixtures", []) or [])
    router = SkillRouter(project_root=repo)
    results = [evaluate_fixture(router, fixture) for fixture in fixtures]
    required_failures = [r for r in results if r["required"] and not r["passed"]]
    known_gap_failures = [r for r in results if r["known_gap"] and not r["passed"]]
    optional_failures = [r for r in results if not r["required"] and not r["known_gap"] and not r["passed"]]
    false_positive_failures = [r for r in required_failures if r["expected"] is None]
    positive_failures = [r for r in required_failures if r["expected"] is not None]
    status = "block" if required_failures else "warn" if known_gap_failures or optional_failures else "pass"
    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "adapter": (manifest.get("policy") or {}).get("default_adapter", "regex_frontmatter"),
        "summary": {
            "fixtures": len(results),
            "passed": sum(1 for r in results if r["passed"]),
            "required_failures": len(required_failures),
            "known_gap_failures": len(known_gap_failures),
            "optional_failures": len(optional_failures),
            "false_positive_failures": len(false_positive_failures),
            "positive_failures": len(positive_failures),
        },
        "results": results,
        "findings": [
            {
                "severity": "block" if r["required"] else "warn",
                "code": "router-benchmark-mismatch",
                "fixture_id": r["id"],
                "message": "Skill router benchmark fixture did not match expected route.",
                "expected": r["expected"],
                "actual": r["actual"],
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
        print(f"skill-router-benchmark: {report['status']} {report['summary']}")
        for result in report["results"]:
            marker = "PASS" if result["passed"] else "FAIL"
            print(f"[{marker}] {result['id']}: expected={result['expected']} actual={result['actual']}")
    return 1 if report["summary"]["required_failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
