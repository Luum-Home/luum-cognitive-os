#!/usr/bin/env python3
# SCOPE: os-only
"""Audit behavioral proof depth for agentic primitives.

This is intentionally orthogonal to SCOPE classification. A primitive can have a
valid scope proof while still having shallow behavior evidence. This audit makes
that depth explicit and ratchetable without pretending family proofs are deep
functional tests.
"""

from __future__ import annotations
import os as _cos_os
import sys as _cos_sys
_cos_sys.path.insert(0, _cos_os.path.dirname(_cos_os.path.dirname(__file__)))
from cos_lib.script_helpers import read_yaml_dict as _load_yaml

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


def _load_behavior_evidence(root: Path) -> dict[str, dict[str, Any]]:
    data = _load_yaml(root / "manifests" / "primitive-behavior-evidence.yaml")
    return {str(item["primitive"]): item for item in data.get("evidence", []) if isinstance(item, dict) and item.get("primitive")}


def _load_policy(root: Path) -> dict[str, Any]:
    data = _load_yaml(root / "manifests" / "primitive-scope-classification.yaml")
    return data.get("behavior_depth_policy") or {}


def _normalize(text: str) -> str:
    """Collapse case and separators so ``cos-registry-lock`` == ``cos_registry_lock``."""
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _artifact_stem(artifact: str) -> str:
    """Normalized identity of the artifact a paired test is named after.

    ``skills/<name>/SKILL.md`` is identified by ``<name>``: every skill file is
    literally called ``SKILL.md``, so its stem carries no identity at all.
    """
    path = Path(artifact)
    return _normalize(path.parent.name if path.stem.lower() == "skill" else path.stem)


def _match_depth(haystack: str) -> str | None:
    if not haystack:
        return None
    if STRUCTURAL_RE.search(haystack):
        return "structural"
    if ADVERSARIAL_RE.search(haystack):
        return "adversarial"
    if PROJECTION_RE.search(haystack):
        return "projection"
    if SMOKE_RE.search(haystack):
        return "smoke"
    return None


def _test_depth(test: str, artifact: str = "") -> str:
    """Depth of the proof a single test provides for ``artifact``.

    CRITERION: depth is what the test EXERCISES -- never what the artifact under
    test is called. Paired proofs are named ``test_<artifact-stem>.py``, so every
    keyword inside the artifact-derived half of that name describes the ARTIFACT.
    Matching it is a name leak, not evidence: it filed
    ``test_check_codebase_memory_readiness.py`` (a cwd-invariance probe) as
    ``structural`` on the token ``readiness``, and it filed
    ``test_secret-detector.py`` (also a cwd-invariance probe) as ``adversarial``
    on ``secret`` -- one under-claim and one over-claim from the same bug.

    So: when the artifact stem is provably present in the test stem, subtract it
    and judge what is left -- the test's own subject first, then its lane (the
    directory, which no artifact name can contaminate). When it is NOT present
    there is nothing to subtract and no leak to prove, so the historical
    whole-path match stands unchanged; guessing there would move rows on the
    strength of a filename, which is the same mistake in a new place.

    Deliberately NOT done here: reading the test body. Two tests in the corpus
    are named for something they do not do (``test_os_only_missing_proof_smoke.py``
    asserts header markers and executes nothing, yet reads as ``smoke``). Only
    content inspection can catch that class; it is out of scope for a name-based
    classifier and is recorded as measured debt in
    ``docs/06-Daily/reports/clasificador-profundidad-2026-08-18.md``.
    """
    lowered = test.lower()
    path = Path(test)
    stem = _normalize(path.stem)
    if stem.startswith("test_"):
        stem = stem[len("test_") :]
    artifact_stem = _artifact_stem(artifact) if artifact else ""
    if artifact_stem and artifact_stem in stem:
        residual = re.sub(r"_+", "_", stem.replace(artifact_stem, "_")).strip("_")
        depth = _match_depth(residual) or _match_depth(_normalize(str(path.parent)))
    else:
        # No provable leak: keep the historical name-or-path match verbatim.
        # Scope/family and manifest audits are explicit surface/structure proofs
        # even when they live under red_team/portability.
        depth = "structural" if STRUCTURAL_RE.search(path.name) else None
        depth = depth or _match_depth(lowered)
    if depth:
        return depth
    if any(part in lowered for part in ("/behavior/", "/integration/", "/unit/", "/contracts/", "/hooks/")):
        return "functional"
    return "structural"


def _max_depth(tests: list[str], artifact: str = "") -> tuple[str, str]:
    if not tests:
        return "none", "no behavior evidence tests"
    depths = [(DEPTH_ORDER[_test_depth(test, artifact)], _test_depth(test, artifact), test) for test in tests]
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
        depth, source = _max_depth(tests, row.path)
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


def build_movement(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Rows that changed depth category between two payloads of this audit.

    A classifier change is a change of MEASUREMENT over a whole population, not a
    one-line fix, so the honest unit of review is this table -- not the handful of
    cases someone happened to notice. See ``--compare-to`` for how to rebuild the
    "before" payload from an older revision of this file.
    """
    old_rows = {str(row["path"]): row for row in before.get("rows", [])}
    new_rows = {str(row["path"]): row for row in after.get("rows", [])}
    moved = [
        {
            "path": path,
            "from": old_rows[path]["behavior_depth"],
            "to": new_rows[path]["behavior_depth"],
            "direction": "up"
            if DEPTH_ORDER[new_rows[path]["behavior_depth"]] > DEPTH_ORDER[old_rows[path]["behavior_depth"]]
            else "down",
            "source_before": old_rows[path]["depth_source"],
            "source_after": new_rows[path]["depth_source"],
        }
        for path in sorted(old_rows.keys() & new_rows.keys())
        if old_rows[path]["behavior_depth"] != new_rows[path]["behavior_depth"]
    ]
    return {
        "totals_before": before.get("summary", {}).get("by_behavior_depth", {}),
        "totals_after": after.get("summary", {}).get("by_behavior_depth", {}),
        "rows_before": len(old_rows),
        "rows_after": len(new_rows),
        "only_in_before": sorted(old_rows.keys() - new_rows.keys()),
        "only_in_after": sorted(new_rows.keys() - old_rows.keys()),
        "moved": moved,
        "moved_by_transition": dict(sorted(Counter(f"{item['from']} -> {item['to']}" for item in moved).items())),
    }


def render_movement(movement: dict[str, Any]) -> str:
    lines = [
        f"rows: {movement['rows_before']} before / {movement['rows_after']} after"
        f"  (+{len(movement['only_in_after'])} new, -{len(movement['only_in_before'])} gone)",
        "",
        f"{'depth':<12}{'before':>8}{'after':>8}{'delta':>8}",
    ]
    for depth in sorted(set(movement["totals_before"]) | set(movement["totals_after"]), key=lambda item: DEPTH_ORDER[item]):
        was = movement["totals_before"].get(depth, 0)
        now = movement["totals_after"].get(depth, 0)
        lines.append(f"{depth:<12}{was:>8}{now:>8}{now - was:>+8}")
    lines += ["", f"moved: {len(movement['moved'])} rows"]
    for transition, count in movement["moved_by_transition"].items():
        lines.append(f"  {count:>4}  {transition}")
    if movement["moved"]:
        lines += ["", f"{'dir':<6}{'transition':<28}path"]
        for item in sorted(movement["moved"], key=lambda entry: (entry["from"], entry["to"], entry["path"])):
            lines.append(f"{item['direction']:<6}{item['from'] + ' -> ' + item['to']:<28}{item['path']}")
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, default=Path("."))
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument(
        "--compare-to",
        type=Path,
        default=None,
        metavar="BEFORE.json",
        help=(
            "print the table of rows that changed depth category against an earlier payload of "
            "this audit. To measure a classifier change, rebuild the old audit against the CURRENT "
            "corpus: copy `git show <commit>:scripts/primitive_behavior_depth_audit.py` into a "
            "scratch dir alongside symlinks to scripts/primitive_scope_health.py and cos_lib/, run "
            "it with --project-dir pointing at this repo, and pass its --json-out here. Pinning "
            "--project-dir keeps manifests and evidence fixed so the classifier is the only variable."
        ),
    )
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
    if args.compare_to is not None:
        before = json.loads(args.compare_to.read_text(encoding="utf-8"))
        print(render_movement(build_movement(before, payload)))
    return 1 if args.strict and payload["findings"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
