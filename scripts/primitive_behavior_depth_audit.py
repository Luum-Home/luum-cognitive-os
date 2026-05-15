#!/usr/bin/env python3
# SCOPE: os-only
"""Audit behavioral proof depth for agentic primitives.

This is intentionally orthogonal to SCOPE classification. A primitive can have a
valid scope proof while still having shallow behavior evidence. This audit makes
that depth explicit and ratchetable without pretending family proofs are deep
functional tests.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_HEALTH_PATH = ROOT / "scripts" / "primitive_scope_health.py"
_SPEC = importlib.util.spec_from_file_location("primitive_scope_health", _HEALTH_PATH)
if _SPEC is None or _SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot load scope health from {_HEALTH_PATH}")
primitive_scope_health = importlib.util.module_from_spec(_SPEC)
sys.modules["primitive_scope_health"] = primitive_scope_health
_SPEC.loader.exec_module(primitive_scope_health)

DEPTH_ORDER = {
    "none": 0,
    "structural": 1,
    "projection": 2,
    "smoke": 3,
    "functional": 4,
    "adversarial": 5,
}
ORDERED_DEPTHS = tuple(DEPTH_ORDER)

STRUCTURAL_RE = re.compile(
    r"(scope[_-]family|primitive[_-]scope|scope[_-]health|registry|manifest|frontmatter|parser|readiness|ledger|wiring|structure|contract$)",
    re.I,
)
PROJECTION_RE = re.compile(r"(projection|project[_-]scope|consumer[_-]project|install|installer|scaffold|template|settings|portability)", re.I)
SMOKE_RE = re.compile(r"(smoke|e2e|executes|execute|run|bash|shell|syntax)", re.I)
ADVERSARIAL_RE = re.compile(r"(chaos|falsification|negative|block|guard|secret|injection|leak|destructive|security|abuse)", re.I)


@dataclass(frozen=True)
class DepthRow:
    path: str
    kind: str
    scope: str
    plane: str
    proof_level: str
    behavior_depth: str
    depth_source: str
    tests: list[str]


@dataclass(frozen=True)
class Finding:
    path: str
    kind: str
    scope: str
    plane: str
    severity: str
    code: str
    rationale: str


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _load_behavior_evidence(root: Path) -> dict[str, dict[str, Any]]:
    data = _load_yaml(root / "manifests" / "primitive-behavior-evidence.yaml")
    return {str(item["primitive"]): item for item in data.get("evidence", []) if isinstance(item, dict) and item.get("primitive")}


def _load_policy(root: Path) -> dict[str, Any]:
    data = _load_yaml(root / "manifests" / "primitive-scope-classification.yaml")
    return data.get("behavior_depth_policy") or {}


def _test_depth(test: str) -> str:
    name = Path(test).name
    lowered = test.lower()
    # Scope/family and manifest audits are explicit surface/structure proofs even
    # when they live under red_team/portability.
    if STRUCTURAL_RE.search(name) or STRUCTURAL_RE.search(lowered):
        return "structural"
    if ADVERSARIAL_RE.search(lowered):
        return "adversarial"
    if PROJECTION_RE.search(lowered):
        return "projection"
    if SMOKE_RE.search(lowered):
        return "smoke"
    if any(part in lowered for part in ("/behavior/", "/integration/", "/unit/", "/contracts/", "/hooks/")):
        return "functional"
    return "structural"


def _max_depth(tests: list[str]) -> tuple[str, str]:
    if not tests:
        return "none", "no behavior evidence tests"
    depths = [(DEPTH_ORDER[_test_depth(test)], _test_depth(test), test) for test in tests]
    _, depth, test = max(depths, key=lambda item: item[0])
    return depth, test


def build_rows(root: Path) -> list[DepthRow]:
    evidence = _load_behavior_evidence(root)
    health_rows = primitive_scope_health.build_rows(root)
    rows: list[DepthRow] = []
    for row in health_rows:
        item = evidence.get(row.path) or {}
        tests = [str(test) for test in item.get("tests", []) if isinstance(test, str)]
        if row.paired_portability_test and row.paired_portability_test not in tests:
            tests.append(row.paired_portability_test)
        depth, source = _max_depth(tests)
        rows.append(
            DepthRow(
                path=row.path,
                kind=row.kind,
                scope=row.scope,
                plane=row.plane,
                proof_level=row.proof_level,
                behavior_depth=depth,
                depth_source=source,
                tests=tests,
            )
        )
    return rows


def _minimum_depth_findings(root: Path, rows: list[DepthRow]) -> list[Finding]:
    policy = _load_policy(root)
    minimum_by_scope = policy.get("minimum_by_scope") or {}
    minimum_by_kind = policy.get("minimum_by_kind") or {}
    findings: list[Finding] = []
    for row in rows:
        required = str(minimum_by_scope.get(row.scope) or minimum_by_kind.get(row.kind) or "none")
        if required not in DEPTH_ORDER:
            findings.append(Finding(row.path, row.kind, row.scope, row.plane, "block", "invalid-behavior-depth-policy", f"unknown required depth {required!r}"))
            continue
        if DEPTH_ORDER[row.behavior_depth] < DEPTH_ORDER[required]:
            findings.append(
                Finding(
                    row.path,
                    row.kind,
                    row.scope,
                    row.plane,
                    "review",
                    "behavior-depth-below-minimum",
                    f"depth {row.behavior_depth} below required {required}",
                )
            )
    return findings


def _budget_findings(root: Path, rows: list[DepthRow]) -> list[Finding]:
    policy = _load_policy(root)
    budgets = policy.get("max_by_depth") or {}
    counts = Counter(row.behavior_depth for row in rows)
    findings: list[Finding] = []
    for depth, max_allowed in sorted(budgets.items()):
        if depth not in DEPTH_ORDER:
            findings.append(Finding("manifests/primitive-scope-classification.yaml", "manifest", "mixed", "control-plane", "block", "invalid-behavior-depth-budget", f"unknown depth {depth!r}"))
            continue
        count = counts.get(depth, 0)
        if count > int(max_allowed):
            findings.append(
                Finding(
                    f"behavior_depth:{depth}",
                    "mixed",
                    "mixed",
                    "control-plane",
                    "review",
                    "behavior-depth-budget-exceeded",
                    f"{depth} has {count} primitives, above budget {max_allowed}",
                )
            )
    return findings


def summarize(rows: list[DepthRow], findings: list[Finding]) -> dict[str, Any]:
    return {
        "total": len(rows),
        "by_behavior_depth": dict(sorted(Counter(row.behavior_depth for row in rows).items(), key=lambda item: DEPTH_ORDER[item[0]])),
        "by_scope": dict(sorted(Counter(row.scope for row in rows).items())),
        "by_kind": dict(sorted(Counter(row.kind for row in rows).items())),
        "by_proof_level": dict(sorted(Counter(row.proof_level for row in rows).items())),
        "findings": len(findings),
        "findings_by_code": dict(sorted(Counter(finding.code for finding in findings).items())),
    }


def build_payload(root: Path) -> dict[str, Any]:
    rows = build_rows(root)
    findings = _minimum_depth_findings(root, rows)
    findings.extend(_budget_findings(root, rows))
    return {
        "schema_version": "primitive-behavior-depth-audit/v1",
        "summary": summarize(rows, findings),
        "rows": [asdict(row) for row in rows],
        "findings": [asdict(finding) for finding in findings],
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, default=Path("."))
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.project_dir.resolve()
    payload = build_payload(root)
    out = args.json_out or root / ".cognitive-os" / "reports" / "primitive-behavior-depth-audit.json"
    if not out.is_absolute():
        out = root / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(json.dumps({"json": str(out), **payload["summary"]}, sort_keys=True))
    return 1 if args.strict and payload["findings"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
