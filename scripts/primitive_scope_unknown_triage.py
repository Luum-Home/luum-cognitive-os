#!/usr/bin/env python3
# SCOPE: os-only
"""Triage unknown primitive scope rows into reviewable evidence-gap buckets.

This is intentionally deterministic. It does not decide final SCOPE markers; it
summarizes why `scripts/primitive_scope_classifier.py` could not classify rows
and adds semantic hints to make manual/AI review cheaper.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from lib.primitive_parser import PrimitiveContract, parse_primitive_file
from lib.project_paths import relpath

OS_INTERNAL_PATTERNS = [
    r"\.cognitive-os/",
    r"manifests/",
    r"docs/02-Decisions/",
    r"docs/06-Daily/",
    r"cognitive-os\.yaml",
    r"scripts/cos[-_]",
    r"primitive-lifecycle",
    r"primitive-readiness",
    r"ADR-\d+",
]

GENERIC_REPO_PATTERNS = [
    r"\bcode review\b",
    r"\btest(?:ing|s)?\b",
    r"\blint\b",
    r"\bcoverage\b",
    r"\bdocumentation\b",
    r"\bsecurity\b",
    r"\barchitecture\b",
    r"\bbuild\b",
    r"\bCI\b",
]

PROJECT_ONLY_PATTERNS = [
    r"--project-dir",
    r"target project",
    r"consumer project",
    r"downstream project",
    r"scaffold",
    r"templates?/",
]


def _read_text(path: Path, limit: int = 120_000) -> str:
    try:
        return path.read_text(errors="ignore")[:limit]
    except OSError:
        return ""


def _first_line_summary(text: str) -> str:
    for raw in text.splitlines()[:80]:
        line = raw.strip().strip('"')
        if not line or line.startswith(("#!", "---", "<!--", "# SCOPE:")):
            continue
        if line.startswith(("#", "//")):
            line = line.lstrip("#/ ").strip()
        if line:
            return line[:180]
    return ""


def _count_patterns(text: str, patterns: list[str]) -> int:
    return sum(1 for pattern in patterns if re.search(pattern, text, re.IGNORECASE))


def _semantic_hints(root: Path, primitive_path: str) -> dict[str, Any]:
    text = _read_text(root / primitive_path)
    contract = parse_primitive_file(root / primitive_path, root)
    return {
        "summary": _first_line_summary(text),
        "os_internal_hits": _count_patterns(text, OS_INTERNAL_PATTERNS),
        "generic_repo_hits": _count_patterns(text, GENERIC_REPO_PATTERNS),
        "project_only_hits": _count_patterns(text, PROJECT_ONLY_PATTERNS),
        "parser_semantic_hints": list(contract.semantic_hints),
        "activation_mode": contract.activation.mode,
        "kind": contract.kind,
    }


def _gap_tags(row: dict[str, Any], contract: PrimitiveContract) -> list[str]:
    evidence = row.get("evidence") or []
    sources = {item.get("source") for item in evidence}
    tags: list[str] = []
    if not row.get("declared_scope"):
        tags.append("missing-scope-marker")
    tags.extend(contract.structural_findings)
    if not evidence:
        tags.append("no-distribution-evidence")
    if "lifecycle" not in sources:
        tags.append("missing-lifecycle-row")
    if "consumer-availability" not in sources:
        tags.append("missing-consumer-availability-row")
    if row.get("declared_scope") == "both" and row.get("paired_proof") is None:
        tags.append("declared-both-missing-paired-proof")
    if row.get("decision_source") == "conflicting-distribution-evidence":
        tags.append("conflicting-distribution-evidence")
    return tags


def _bucket(row: dict[str, Any], hints: dict[str, Any], tags: list[str]) -> str:
    if "conflicting-distribution-evidence" in tags:
        return "conflicting-metadata"
    if row.get("declared_scope") == "both" and "declared-both-missing-paired-proof" in tags:
        if hints["os_internal_hits"] > hints["generic_repo_hits"] and hints["os_internal_hits"] >= 2:
            return "declared-both-os-internal-heavy"
        return "declared-both-needs-proof-and-metadata"
    if not row.get("declared_scope"):
        return "missing-scope-marker"
    if hints["project_only_hits"] >= 2:
        return "project-only-semantic-candidate"
    if hints["generic_repo_hits"] >= 2 and hints["os_internal_hits"] == 0:
        return "both-semantic-candidate"
    if hints["os_internal_hits"] >= 2 and hints["generic_repo_hits"] == 0:
        return "os-only-semantic-candidate"
    return "insufficient-metadata"


@dataclass
class TriageRow:
    path: str
    declared_scope: str | None
    bucket: str
    gap_tags: list[str]
    structural_findings: list[str]
    semantic_hints: dict[str, Any]
    evidence: list[dict[str, Any]] = field(default_factory=list)
    next_action: str = ""


def _load_classifier_report(root: Path) -> dict[str, Any]:
    report = root / ".cognitive-os" / "reports" / "primitive-scope-classifier.json"
    if not report.exists():
        subprocess.run([sys.executable, str(root / "scripts" / "primitive_scope_classifier.py"), "--project-dir", str(root)], check=True)
    return json.loads(report.read_text())


def build_triage(root: Path) -> dict[str, Any]:
    report = _load_classifier_report(root)
    unknown_rows = [row for row in report["rows"] if row.get("suggested_scope") == "unknown"]
    rows: list[TriageRow] = []
    for row in unknown_rows:
        contract = parse_primitive_file(root / row["path"], root)
        hints = _semantic_hints(root, row["path"])
        tags = _gap_tags(row, contract)
        rows.append(
            TriageRow(
                path=row["path"],
                declared_scope=row.get("declared_scope"),
                bucket=_bucket(row, hints, tags),
                gap_tags=tags,
                structural_findings=list(contract.structural_findings),
                semantic_hints=hints,
                evidence=row.get("evidence") or [],
                next_action=row.get("next_action") or "",
            )
        )

    bucket_counts = Counter(row.bucket for row in rows)
    gap_counts = Counter(tag for row in rows for tag in row.gap_tags)
    prefix_counts = Counter(row.path.split("/")[0] for row in rows)
    declared_counts = Counter(row.declared_scope or "none" for row in rows)

    return {
        "schema_version": "primitive-scope-unknown-triage/v1",
        "summary": {
            "total_unknown": len(rows),
            "by_bucket": dict(sorted(bucket_counts.items())),
            "by_gap": dict(sorted(gap_counts.items())),
            "by_prefix": dict(sorted(prefix_counts.items())),
            "by_declared_scope": dict(sorted(declared_counts.items())),
        },
        "rows": [asdict(row) for row in rows],
    }


def write_markdown(root: Path, triage: dict[str, Any], output: Path) -> None:
    rows = triage["rows"]
    by_bucket: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_bucket[row["bucket"]].append(row)

    lines = [
        "# Primitive Scope Unknown Triage",
        "",
        "This report groups `suggested_scope=unknown` rows by missing evidence and deterministic semantic hints. It is not a final classifier and must not drive marker rewrites by itself.",
        "",
        "## Summary",
        "",
        "```json",
        json.dumps(triage["summary"], indent=2, sort_keys=True),
        "```",
        "",
        "## Bucket meanings",
        "",
        "| Bucket | Meaning | Default action |",
        "|---|---|---|",
        "| `conflicting-metadata` | Durable metadata disagrees. | Reconcile lifecycle/consumer metadata before marker changes. |",
        "| `declared-both-needs-proof-and-metadata` | Marker says `both`, but distribution/proof evidence is absent or incomplete. | Add paired proof and lifecycle/consumer evidence, or demote after semantic review. |",
        "| `declared-both-os-internal-heavy` | Marker says `both`, but content is dominated by SO-internal concepts. | Prioritize manual review for likely stale marker. |",
        "| `missing-scope-marker` | Parser/classifier found no explicit marker and not enough evidence. | Add marker only after semantic review. |",
        "| `project-only-semantic-candidate` | Text suggests downstream-project-only behavior. | Add project-only metadata/proof if confirmed. |",
        "| `both-semantic-candidate` | Text looks repo-agnostic and generic. | Add portability proof and distribution metadata if confirmed. |",
        "| `os-only-semantic-candidate` | Text looks SO-internal. | Add os-only lifecycle/consumer metadata if confirmed. |",
        "| `insufficient-metadata` | No clear deterministic semantic direction. | Needs manual or AI-assisted adjudication. |",
        "",
    ]

    for bucket, bucket_rows in sorted(by_bucket.items(), key=lambda item: (-len(item[1]), item[0])):
        lines.extend([f"## {bucket} ({len(bucket_rows)})", ""])
        lines.append("| Path | Declared | Hints | Gaps | Structure | Summary |")
        lines.append("|---|---|---|---|---|---|")
        for row in bucket_rows[:50]:
            hints = row["semantic_hints"]
            hint_text = f"os={hints['os_internal_hits']}; generic={hints['generic_repo_hits']}; project={hints['project_only_hits']}"
            gaps = ", ".join(row["gap_tags"][:4])
            structure = ", ".join(row.get("structural_findings", [])[:3])
            summary = (hints.get("summary") or "").replace("|", "\\|")
            lines.append(f"| `{row['path']}` | {row.get('declared_scope') or ''} | {hint_text} | {gaps} | {structure} | {summary} |")
        if len(bucket_rows) > 50:
            lines.append(f"| … | … | … | … | … | {len(bucket_rows) - 50} more rows in JSON report. |")
        lines.append("")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Triage unknown primitive scope classifier rows.")
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--json", default=".cognitive-os/reports/primitive-scope-unknown-triage.json")
    parser.add_argument("--markdown", default="docs/06-Daily/reports/primitive-scope-unknown-triage-latest.md")
    args = parser.parse_args()

    root = Path(args.project_dir).resolve()
    triage = build_triage(root)
    json_path = root / args.json
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(triage, indent=2, sort_keys=True) + "\n")
    write_markdown(root, triage, root / args.markdown)
    print(json.dumps({**triage["summary"], "json": relpath(root, json_path), "markdown": args.markdown}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
