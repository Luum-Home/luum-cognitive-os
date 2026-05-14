#!/usr/bin/env python3
# SCOPE: os-only
"""Evidence-weighted SCOPE classifier for agentic primitives.

This tool computes a suggested scope from distribution evidence instead of from
raw source-path mentions. It is intentionally conservative: when a primitive has
no export/projection evidence, the suggested scope is `os-only` with low
confidence and an explicit next action. `both` requires positive consumer/export
evidence and should be paired with portability proof.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.portability_proof_paths import paired_candidates, suggested_test_path
from lib.project_paths import relpath
from lib.primitive_readiness_common import load_lifecycle

VALID_SCOPES = {"os-only", "project", "both"}
SOURCE_ROOTS = ("hooks", "skills", "rules", "scripts", "templates")
SCOPE_RE = re.compile(r"\bSCOPE:\s*([A-Za-z0-9_-]+)")
PROJECTABLE_STATUSES = {"projectable-needs-driver", "shell-ci-candidate", "projected-consumer-surface"}
MAINTAINER_STATUSES = {"maintainer-only", "so-local-only", "lifecycle-declared-maintainer"}
CONSUMER_DISTRIBUTIONS = {"core", "team"}
MAINTAINER_DISTRIBUTIONS = {"maintainer", "lab"}


@dataclass(frozen=True)
class Evidence:
    source: str
    scope: str
    weight: int
    detail: str


@dataclass
class ScopeRow:
    path: str
    declared_scope: str | None
    suggested_scope: str
    confidence: str
    decision_source: str
    evidence: list[Evidence] = field(default_factory=list)
    paired_portability_test: str | None = None
    contradiction: str = ""
    next_action: str = ""


def _is_text_file(path: Path) -> bool:
    if not path.is_file() or any(part in {".git", "__pycache__", ".venv", "node_modules"} for part in path.parts):
        return False
    try:
        path.read_text(encoding="utf-8", errors="ignore")[:128]
        return True
    except OSError:
        return False


def _header_scope(path: Path) -> str | None:
    head = "\n".join(path.read_text(encoding="utf-8", errors="ignore").splitlines()[:8])
    match = SCOPE_RE.search(head)
    return match.group(1) if match else None


def _primitive_files(root: Path) -> list[Path]:
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
        for path in base.rglob("*"):
            if _is_text_file(path):
                found[relpath(root, path)] = path
    return [found[key] for key in sorted(found)]


def _load_scope_overrides(root: Path) -> list[dict[str, str]]:
    path = root / "manifests" / "primitive-scope-overrides.yaml"
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return [item for item in data.get("rules", []) if isinstance(item, dict) and item.get("pattern") and item.get("scope")]


def _override_for(rel: str, rules: list[dict[str, str]]) -> dict[str, str] | None:
    # Last matching rule wins, mirroring common allow/deny config semantics.
    match: dict[str, str] | None = None
    for rule in rules:
        if fnmatch.fnmatch(rel, str(rule["pattern"])):
            match = rule
    return match


def _load_consumer_availability(root: Path) -> dict[str, dict[str, Any]]:
    path = root / "manifests" / "primitive-consumer-availability.yaml"
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {str(item["path"]): item for item in data.get("items", []) if isinstance(item, dict) and item.get("path")}


def _load_protected_install_surfaces(root: Path) -> dict[str, dict[str, Any]]:
    path = root / "manifests" / "primitive-readiness-protected-install-surfaces.yaml"
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {str(item["path"]): item for item in data.get("scripts", []) if isinstance(item, dict) and item.get("path")}


def _paired_test(root: Path, rel: str) -> str | None:
    for candidate in paired_candidates(rel):
        if (root / candidate).exists():
            return candidate
    return None


def _evidence_for(root: Path, rel: str, override_rules: list[dict[str, str]], availability: dict[str, dict[str, Any]], protected: dict[str, dict[str, Any]], lifecycle: dict[str, dict[str, Any]]) -> list[Evidence]:
    evidence: list[Evidence] = []
    override = _override_for(rel, override_rules)
    if override and override.get("scope") in VALID_SCOPES:
        evidence.append(Evidence("scope-override", str(override["scope"]), 100, str(override.get("rationale") or override.get("pattern"))))

    if rel in protected:
        evidence.append(Evidence("protected-install-surface", "both", 90, str(protected[rel].get("surface") or "install/profile surface")))

    item = availability.get(rel)
    if item:
        status = str(item.get("status") or "")
        if status in MAINTAINER_STATUSES:
            evidence.append(Evidence("consumer-availability", "os-only", 80, status))
        elif status in PROJECTABLE_STATUSES:
            evidence.append(Evidence("consumer-availability", "both", 70, status))

    row = lifecycle.get(rel)
    if row:
        distribution = str(row.get("distribution") or "")
        state = str(row.get("lifecycle_state") or "")
        if distribution in MAINTAINER_DISTRIBUTIONS or state in {"sandbox", "archived", "deleted"}:
            evidence.append(Evidence("lifecycle", "os-only", 65, f"distribution={distribution}; state={state}"))
        elif distribution in CONSUMER_DISTRIBUTIONS:
            evidence.append(Evidence("lifecycle", "both", 65, f"distribution={distribution}; state={state}"))

    paired = _paired_test(root, rel)
    if paired:
        evidence.append(Evidence("portability-proof", "both", 45, paired))
    return evidence


def _decide(rel: str, declared: str | None, evidence: list[Evidence], paired: str | None) -> tuple[str, str, str, str, str]:
    if declared not in VALID_SCOPES and declared is not None:
        return "os-only", "low", "invalid-declared-scope", "invalid declared scope marker", "replace marker with one of os-only, project, both"

    if evidence:
        totals: dict[str, int] = {}
        for item in evidence:
            totals[item.scope] = totals.get(item.scope, 0) + item.weight
        suggested = max(totals, key=lambda key: (totals[key], key))
        winning = totals[suggested]
        second = max([score for scope, score in totals.items() if scope != suggested], default=0)
        confidence = "high" if winning >= 90 and winning - second >= 30 else "medium" if winning >= 65 and winning > second else "low"
        source = "+".join(item.source for item in evidence if item.scope == suggested)
    else:
        suggested = "os-only"
        confidence = "low"
        source = "safe-default"

    contradiction = ""
    if declared and declared != suggested and confidence in {"high", "medium"}:
        contradiction = f"declared {declared} conflicts with evidence-derived {suggested}"
    if declared == "both" and not paired:
        contradiction = contradiction or "declared both without paired portability proof"

    if suggested == "both" and not paired:
        next_action = f"add paired portability/falsification test, e.g. {suggested_test_path(rel)}"
    elif confidence == "low":
        next_action = "add lifecycle/projection/consumer-availability metadata before relying on this classification"
    elif contradiction:
        next_action = "change SCOPE marker or update distribution evidence so they agree"
    else:
        next_action = "classification evidence is coherent"
    return suggested, confidence, source, contradiction, next_action


def _changed_paths(root: Path) -> set[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain"],
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
    except Exception:
        return set()
    if result.returncode != 0:
        return set()
    changed: set[str] = set()
    for raw in result.stdout.splitlines():
        if not raw:
            continue
        path = raw[3:] if len(raw) > 3 else raw
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        changed.add(path.strip())
    return changed


def build_rows(root: Path, changed_only: bool = False, only_paths: set[str] | None = None) -> list[ScopeRow]:
    override_rules = _load_scope_overrides(root)
    availability = _load_consumer_availability(root)
    protected = _load_protected_install_surfaces(root)
    lifecycle = load_lifecycle(root)
    rows: list[ScopeRow] = []
    changed = _changed_paths(root) if changed_only else set()
    for path in _primitive_files(root):
        rel = relpath(root, path)
        if changed_only and rel not in changed:
            continue
        if only_paths is not None and rel not in only_paths:
            continue
        declared = _header_scope(path)
        paired = _paired_test(root, rel)
        evidence = _evidence_for(root, rel, override_rules, availability, protected, lifecycle)
        suggested, confidence, source, contradiction, next_action = _decide(rel, declared, evidence, paired)
        rows.append(
            ScopeRow(
                path=rel,
                declared_scope=declared,
                suggested_scope=suggested,
                confidence=confidence,
                decision_source=source,
                evidence=evidence,
                paired_portability_test=paired,
                contradiction=contradiction,
                next_action=next_action,
            )
        )
    return rows


def summarize(rows: list[ScopeRow]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "total": len(rows),
        "by_suggested_scope": {},
        "by_confidence": {},
        "contradictions": sum(1 for row in rows if row.contradiction),
        "low_confidence": sum(1 for row in rows if row.confidence == "low"),
    }
    for row in rows:
        summary["by_suggested_scope"][row.suggested_scope] = summary["by_suggested_scope"].get(row.suggested_scope, 0) + 1
        summary["by_confidence"][row.confidence] = summary["by_confidence"].get(row.confidence, 0) + 1
    summary["by_suggested_scope"] = dict(sorted(summary["by_suggested_scope"].items()))
    summary["by_confidence"] = dict(sorted(summary["by_confidence"].items()))
    return summary


def write_report(rows: list[ScopeRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "primitive-scope-classifier/v1",
        "summary": summarize(rows),
        "rows": [asdict(row) for row in rows],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Classify primitive SCOPE from distribution/projection evidence")
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--json-out", default=".cognitive-os/reports/primitive-scope-classifier.json")
    parser.add_argument("--changed-only", action="store_true", help="Only classify files changed in git status")
    parser.add_argument("--paths", nargs="*", help="Explicit repo-relative primitive paths to classify")
    parser.add_argument("--fail-contradictions", action="store_true")
    parser.add_argument("--fail-low-confidence", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.project_dir).resolve()
    only_paths = set(args.paths) if args.paths else None
    rows = build_rows(root, changed_only=args.changed_only, only_paths=only_paths)
    out = root / args.json_out
    write_report(rows, out)
    summary = summarize(rows)
    print(json.dumps({"json": str(out), **summary}, sort_keys=True))
    if args.fail_contradictions and summary["contradictions"]:
        return 1
    if args.fail_low_confidence and summary["low_confidence"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
