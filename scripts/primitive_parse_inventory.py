#!/usr/bin/env python3
# SCOPE: os-only
"""Parse agentic primitive files into normalized contracts.

This is a structural inventory tool. It does not classify final SCOPE; it feeds
scope calibration by exposing parsed kind, activation, metadata, structural
findings, and semantic hints.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.primitive_parser import parse_primitive_file
from lib.project_paths import relpath

SOURCE_ROOTS = ("hooks", "skills", "rules", "scripts", "templates", "packages")


def _is_text_file(path: Path) -> bool:
    if not path.is_file() or any(part in {".git", "__pycache__", ".venv", "node_modules"} for part in path.parts):
        return False
    try:
        path.read_text(encoding="utf-8", errors="ignore")[:128]
        return True
    except OSError:
        return False


def primitive_files(root: Path) -> list[Path]:
    found: dict[str, Path] = {}
    for root_name in SOURCE_ROOTS:
        base = root / root_name
        if not base.exists():
            continue
        if root_name == "skills":
            for path in base.rglob("SKILL.md"):
                if _is_text_file(path):
                    found[relpath(root, path)] = path
            continue
        if root_name == "packages":
            for path in base.glob("*/skills/*/SKILL.md"):
                if _is_text_file(path):
                    found[relpath(root, path)] = path
            continue
        for path in base.rglob("*"):
            if _is_text_file(path):
                found[relpath(root, path)] = path
    return [found[key] for key in sorted(found)]


def summarize(contracts: list[dict[str, Any]]) -> dict[str, Any]:
    by_kind: dict[str, int] = {}
    by_activation: dict[str, int] = {}
    findings: dict[str, int] = {}
    missing_scope = 0
    primitive_count = 0
    for contract in contracts:
        by_kind[contract["kind"]] = by_kind.get(contract["kind"], 0) + 1
        mode = contract["activation"]["mode"]
        by_activation[mode] = by_activation.get(mode, 0) + 1
        if contract.get("is_primitive"):
            primitive_count += 1
        if contract.get("is_primitive") and not contract.get("scope_marker"):
            missing_scope += 1
        for finding in contract.get("structural_findings", []):
            findings[finding] = findings.get(finding, 0) + 1
    return {
        "total": len(contracts),
        "primitive_total": primitive_count,
        "by_kind": dict(sorted(by_kind.items())),
        "by_activation": dict(sorted(by_activation.items())),
        "missing_scope_marker": missing_scope,
        "structural_findings": dict(sorted(findings.items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--paths", nargs="*", help="Optional repository-relative primitive paths to parse")
    parser.add_argument("--output", default=".cognitive-os/reports/primitive-parse-inventory.json")
    args = parser.parse_args()

    root = Path(args.project_dir).resolve()
    if args.paths:
        paths = [root / raw for raw in args.paths]
    else:
        paths = primitive_files(root)
    contracts = [asdict(parse_primitive_file(path, root)) for path in paths if path.exists()]
    payload = {"summary": summarize(contracts), "contracts": contracts}
    output = root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(json.dumps({**payload["summary"], "json": str(output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
