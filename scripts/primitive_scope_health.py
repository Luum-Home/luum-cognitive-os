#!/usr/bin/env python3
# SCOPE: os-only
"""Primitive scope health, plane, balance, and risk audits.

This is the ADR-321 audit surface. It does not reclassify primitives; it derives
orthogonal metadata from classifier/lifecycle evidence and emits review queues for
balance, over-internalization, and false-`both` risks.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_CLASSIFIER_PATH = ROOT / "scripts" / "primitive_scope_classifier.py"
_SPEC = importlib.util.spec_from_file_location("primitive_scope_classifier", _CLASSIFIER_PATH)
if _SPEC is None or _SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot load classifier from {_CLASSIFIER_PATH}")
primitive_scope_classifier = importlib.util.module_from_spec(_SPEC)
sys.modules["primitive_scope_classifier"] = primitive_scope_classifier
_SPEC.loader.exec_module(primitive_scope_classifier)

VALID_PLANES = {"control-plane", "user-plane", "factory-plane", "runtime-plane"}
GENERIC_NAME_RE = re.compile(r"(review|test|security|secret|docs?|architecture|health|license|audit|status|browser|quality|verify|validation|coverage|lint)", re.I)
INTERNAL_RE = re.compile(r"(docs/02-Decisions|docs/06-Daily|manifests/|primitive-lifecycle|primitive-readiness|ADR-\d+|\.cognitive-os/(reports|strategy|sessions)|source Cognitive OS|COS maintainer)", re.I)
SOURCE_PATH_RE = re.compile("(" + "/" + "Users" + "/|matias" + r"\.nahuel)")
BATCH_PROOF_RE = re.compile(r"test_low_confidence_scope_batch\.py|batch", re.I)


@dataclass(frozen=True)
class HealthRow:
    path: str
    kind: str
    scope: str
    declared_scope: str | None
    confidence: str
    plane: str
    consumer_surface: str
    proof_level: str
    decision_source: str
    paired_portability_test: str | None


@dataclass(frozen=True)
class Finding:
    path: str
    kind: str
    scope: str
    plane: str
    severity: str
    code: str
    rationale: str


def _kind(path: str) -> str:
    if path.startswith("hooks/"):
        return "hooks"
    if path.startswith("skills/") or "/skills/" in path:
        return "skills"
    if path.startswith("rules/"):
        return "rules"
    if path.startswith("scripts/"):
        return "scripts"
    if path.startswith("templates/"):
        return "templates"
    if path.startswith("packages/"):
        return "packages"
    return path.split("/", 1)[0]


def _load_lifecycle(root: Path) -> dict[str, dict[str, Any]]:
    path = root / "manifests" / "primitive-lifecycle.yaml"
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {str(row.get("id")): row for row in data.get("primitives", []) if isinstance(row, dict) and row.get("id")}


def _load_scope_policy(root: Path) -> dict[str, Any]:
    path = root / "manifests" / "primitive-scope-classification.yaml"
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _review_exemption_entries(root: Path) -> list[dict[str, str]]:
    policy = _load_scope_policy(root)
    parsed: list[dict[str, str]] = []
    for code, raw_entries in (policy.get("review_exemptions") or {}).items():
        if not isinstance(raw_entries, list):
            continue
        for entry in raw_entries:
            if not isinstance(entry, dict):
                continue
            path = str(entry.get("path") or "")
            rationale = str(entry.get("rationale") or "")
            if path or rationale:
                parsed.append({"code": str(code), "path": path, "rationale": rationale})
    return parsed


def _review_exemptions(root: Path) -> dict[tuple[str, str], str]:
    exemptions: dict[tuple[str, str], str] = {}
    for entry in _review_exemption_entries(root):
        path = entry["path"]
        rationale = entry["rationale"]
        if path and rationale:
            exemptions[(entry["code"], path)] = rationale
    return exemptions


def _apply_review_exemptions(root: Path, findings: list[Finding]) -> tuple[list[Finding], list[dict[str, str]]]:
    exemptions = _review_exemptions(root)
    active: list[Finding] = []
    suppressed: list[dict[str, str]] = []
    for finding in findings:
        rationale = exemptions.get((finding.code, finding.path))
        if rationale:
            suppressed.append(
                {
                    "path": finding.path,
                    "code": finding.code,
                    "rationale": rationale,
                }
            )
            continue
        active.append(finding)
    return active, suppressed


def review_exemption_hygiene_findings(root: Path, raw_findings: list[Finding]) -> list[Finding]:
    policy = _load_scope_policy(root)
    cfg = policy.get("review_exemption_policy") or {}
    max_active_by_code = cfg.get("max_active_by_code") or {}
    min_rationale_chars = int(cfg.get("min_rationale_chars") or 40)
    entries = _review_exemption_entries(root)
    findings: list[Finding] = []
    raw_keys = {(finding.code, finding.path) for finding in raw_findings}
    seen: set[tuple[str, str]] = set()
    counts = Counter(entry["code"] for entry in entries)
    for code, count in sorted(counts.items()):
        max_allowed = max_active_by_code.get(code)
        if max_allowed is not None and count > int(max_allowed):
            findings.append(
                Finding(
                    "manifests/primitive-scope-classification.yaml",
                    "manifest",
                    "mixed",
                    "control-plane",
                    "review",
                    "review-exemptions-over-budget",
                    f"{code} has {count} review exemptions, above budget {max_allowed}",
                )
            )
    for entry in entries:
        code = entry["code"]
        path = entry["path"]
        rationale = entry["rationale"]
        key = (code, path)
        if key in seen:
            findings.append(Finding(path or "<missing>", "manifest", "mixed", "control-plane", "review", "duplicate-review-exemption", f"duplicate exemption for {code}"))
        seen.add(key)
        if not path or not rationale:
            findings.append(Finding(path or "<missing>", "manifest", "mixed", "control-plane", "review", "malformed-review-exemption", "review exemption requires path and rationale"))
            continue
        if len(rationale.strip()) < min_rationale_chars:
            findings.append(Finding(path, _kind(path), "mixed", "control-plane", "review", "thin-review-exemption-rationale", f"rationale shorter than {min_rationale_chars} characters"))
        if not (root / path).exists():
            findings.append(Finding(path, _kind(path), "mixed", "control-plane", "review", "missing-review-exemption-path", "review exemption path does not exist"))
        if key not in raw_keys:
            findings.append(Finding(path, _kind(path), "mixed", "control-plane", "review", "stale-review-exemption", "exemption no longer suppresses an active review finding"))
    return findings


def _text(root: Path, rel: str, limit: int = 30000) -> str:
    try:
        return (root / rel).read_text(encoding="utf-8", errors="ignore")[:limit]
    except OSError:
        return ""


def infer_plane(root: Path, rel: str, scope: str, lifecycle: dict[str, Any]) -> str:
    explicit = str((lifecycle.get(rel) or {}).get("plane") or "")
    if explicit in VALID_PLANES:
        return explicit
    lower = rel.lower()
    text = _text(root, rel, 6000).lower()
    if rel.startswith("hooks/_lib/") or rel.startswith("hooks/"):
        return "runtime-plane"
    if any(token in lower for token in ("harvest", "scaffold", "synthesize", "repair", "creator", "add-", "generate")):
        return "factory-plane"
    if any(token in lower for token in ("manifest", "readiness", "ledger", "classifier", "audit", "adr", "release", "status", "doctor", "migration", "governance")):
        return "control-plane"
    if any(token in text for token in ("create a new", "promote", "scaffold", "generate project", "primitive authoring")):
        return "factory-plane"
    if rel.startswith("templates/project-templates/") or scope == "project":
        return "user-plane"
    if scope == "both" and any(token in lower for token in ("secret", "review", "test", "quality", "security", "license", "verify", "docs")):
        return "user-plane"
    if scope == "os-only":
        return "control-plane"
    return "user-plane"


def consumer_surface(scope: str, lifecycle: dict[str, Any]) -> str:
    access = str(lifecycle.get("consumer_accessibility") or "")
    if access == "lifecycle-declared-shared-surface" or scope == "both":
        return "shared"
    if access == "lifecycle-declared-consumer-candidate":
        return "project-generated"
    if scope == "project":
        return "projected"
    return "maintainer-only"


def proof_level(row: Any) -> str:
    paired = getattr(row, "paired_portability_test", None)
    if not paired:
        return "none"
    name = Path(paired).name
    if BATCH_PROOF_RE.search(name):
        return "batch"
    if any(token in name for token in ("shared_", "package_skills", "family", "surfaces", "scripts")):
        return "family"
    return "primitive-specific"


def build_rows(root: Path) -> list[HealthRow]:
    lifecycle = _load_lifecycle(root)
    rows = []
    for row in primitive_scope_classifier.build_rows(root):
        rel = row.path
        scope = row.effective_scope
        life = lifecycle.get(rel) or {}
        rows.append(
            HealthRow(
                path=rel,
                kind=_kind(rel),
                scope=scope,
                declared_scope=row.declared_scope,
                confidence=row.confidence,
                plane=infer_plane(root, rel, scope, lifecycle),
                consumer_surface=consumer_surface(scope, life),
                proof_level=proof_level(row),
                decision_source=row.decision_source,
                paired_portability_test=row.paired_portability_test,
            )
        )
    return rows


def balance_findings(root: Path, rows: list[HealthRow]) -> list[Finding]:
    policy = _load_scope_policy(root).get("expected_scope_distribution", {})
    findings: list[Finding] = []
    by_kind: dict[str, list[HealthRow]] = defaultdict(list)
    for row in rows:
        by_kind[row.kind].append(row)
    for kind, kind_rows in sorted(by_kind.items()):
        if kind not in policy or not kind_rows:
            continue
        total = len(kind_rows)
        counts = Counter(row.scope for row in kind_rows)
        cfg = policy[kind]
        os_pct = counts.get("os-only", 0) * 100 / total
        both_pct = counts.get("both", 0) * 100 / total
        project_pct = counts.get("project", 0) * 100 / total
        if "os-only_max_warning" in cfg and os_pct > float(cfg["os-only_max_warning"]):
            findings.append(Finding(kind, kind, "mixed", "control-plane", "warning", "scope-ratio-os-only-high", f"{kind} os-only ratio {os_pct:.1f}% exceeds warning threshold {cfg['os-only_max_warning']}%"))
        if "both_min_warning" in cfg and both_pct < float(cfg["both_min_warning"]):
            findings.append(Finding(kind, kind, "mixed", "user-plane", "warning", "scope-ratio-both-low", f"{kind} both ratio {both_pct:.1f}% below warning threshold {cfg['both_min_warning']}%"))
        if "project_min_warning" in cfg and project_pct < float(cfg["project_min_warning"]):
            findings.append(Finding(kind, kind, "mixed", "user-plane", "warning", "scope-ratio-project-low", f"{kind} project ratio {project_pct:.1f}% below warning threshold {cfg['project_min_warning']}%"))
    return findings


def generic_os_only_findings(root: Path, rows: list[HealthRow]) -> list[Finding]:
    findings: list[Finding] = []
    for row in rows:
        if row.scope != "os-only":
            continue
        text = _text(root, row.path)
        name = f"{Path(row.path).stem} {row.path}"
        has_generic_name = bool(GENERIC_NAME_RE.search(name))
        has_invocation = any(token in text.lower() for token in ("user-invocable: true", "triggers:", "routing_patterns", "## usage", "## trigger"))
        has_internal = bool(INTERNAL_RE.search(text))
        if has_generic_name and has_invocation and not has_internal:
            findings.append(Finding(row.path, row.kind, row.scope, row.plane, "review", "os-only-generic-candidate", "os-only primitive has generic repo-facing name/triggers and lacks strong COS-internal markers"))
    return findings


def false_both_findings(root: Path, rows: list[HealthRow]) -> list[Finding]:
    findings: list[Finding] = []
    for row in rows:
        if row.scope != "both":
            continue
        text = _text(root, row.path)
        reasons = []
        if SOURCE_PATH_RE.search(text):
            reasons.append("source checkout path")
        if row.proof_level in {"none", "batch"}:
            reasons.append(f"weak proof level {row.proof_level}")
            if INTERNAL_RE.search(text):
                reasons.append("COS-internal references")
        # COS-internal words are common in legitimate shared hooks because they run
        # inside a COS projection. Treat them as a false-both signal only when proof
        # is weak, or when a real source-checkout path is present.
        if reasons:
            findings.append(Finding(row.path, row.kind, row.scope, row.plane, "review", "both-needs-specific-proof", "; ".join(reasons)))
    return findings


def proof_budget_findings(root: Path, rows: list[HealthRow]) -> list[Finding]:
    budgets = (_load_scope_policy(root).get("proof_level_budgets") or {}).get("none_by_scope") or {}
    findings: list[Finding] = []
    counts = Counter(row.scope for row in rows if row.proof_level == "none")
    for scope, count in sorted(counts.items()):
        max_allowed = budgets.get(scope)
        if max_allowed is not None and count > int(max_allowed):
            findings.append(
                Finding(
                    f"proof_level:none/{scope}",
                    "mixed",
                    scope,
                    "user-plane" if scope in {"both", "project"} else "control-plane",
                    "review",
                    "proof-none-budget-exceeded",
                    f"{scope} has {count} proof_level:none primitives, above budget {max_allowed}",
                )
            )
    for scope, max_allowed in sorted(budgets.items()):
        if int(max_allowed) == 0 and counts.get(scope, 0) > 0:
            findings.append(
                Finding(
                    f"proof_level:none/{scope}",
                    "mixed",
                    scope,
                    "user-plane",
                    "block",
                    "proof-none-zero-budget-violated",
                    f"{scope} must have zero proof_level:none primitives",
                )
            )
    return findings


def summarize(rows: list[HealthRow], findings: list[Finding]) -> dict[str, Any]:
    return {
        "total": len(rows),
        "by_scope": dict(sorted(Counter(row.scope for row in rows).items())),
        "by_plane": dict(sorted(Counter(row.plane for row in rows).items())),
        "by_kind": dict(sorted(Counter(row.kind for row in rows).items())),
        "by_proof_level": dict(sorted(Counter(row.proof_level for row in rows).items())),
        "findings": len(findings),
        "findings_by_code": dict(sorted(Counter(f.code for f in findings).items())),
    }


def build_payload(root: Path, mode: str) -> dict[str, Any]:
    rows = build_rows(root)
    findings: list[Finding] = []
    raw_review_findings: list[Finding] = []
    if mode in {"balance", "health"}:
        findings.extend(balance_findings(root, rows))
    if mode in {"generic-os-only", "health"}:
        raw_review_findings.extend(generic_os_only_findings(root, rows))
    if mode in {"false-both", "health"}:
        raw_review_findings.extend(false_both_findings(root, rows))
    findings.extend(raw_review_findings)
    if mode in {"proof", "health"}:
        findings.extend(proof_budget_findings(root, rows))
    if mode in {"generic-os-only", "health"}:
        findings.extend(review_exemption_hygiene_findings(root, raw_review_findings))
    if mode == "plane":
        findings.extend(
            Finding(row.path, row.kind, row.scope, row.plane, "block", "invalid-plane", "plane could not be derived")
            for row in rows
            if row.plane not in VALID_PLANES
        )
    findings, suppressed = _apply_review_exemptions(root, findings)
    return {
        "schema_version": f"primitive-scope-{mode}-audit/v1",
        "mode": mode,
        "summary": summarize(rows, findings),
        "rows": [asdict(row) for row in rows],
        "findings": [asdict(finding) for finding in findings],
        "suppressed_findings": suppressed,
    }


def mode_from_argv(argv0: str) -> str:
    name = Path(argv0).name
    if "balance" in name:
        return "balance"
    if "plane" in name:
        return "plane"
    if "generic-os-only" in name:
        return "generic-os-only"
    if "false-both" in name:
        return "false-both"
    if "proof" in name:
        return "proof"
    return "health"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, default=Path("."))
    parser.add_argument("--mode", choices=["balance", "plane", "generic-os-only", "false-both", "proof", "health"], default=None)
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero for block findings, and for all findings in non-health modes")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.project_dir.resolve()
    mode = args.mode or mode_from_argv(sys.argv[0])
    payload = build_payload(root, mode)
    out = args.json_out or root / ".cognitive-os" / "reports" / f"primitive-scope-{mode}-audit.json"
    if not out.is_absolute():
        out = root / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(json.dumps({"json": str(out), **payload["summary"]}, sort_keys=True))
    findings = payload["findings"]
    if args.strict:
        if mode == "health":
            return 1 if any(f["severity"] == "block" for f in findings) else 0
        return 1 if findings else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
