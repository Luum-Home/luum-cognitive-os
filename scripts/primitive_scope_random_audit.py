#!/usr/bin/env python3
# SCOPE: os-only
"""Create a deterministic manual-review sample from primitive scope classifier rows.

The tool does not change SCOPE markers. It selects review rows reproducibly so
maintainers can audit arbitrary primitives, record decisions, and feed repeated
patterns back into classifier evidence instead of relying on ad-hoc judgement.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import random
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_CLASSIFIER_PATH = ROOT / "scripts" / "primitive_scope_classifier.py"
_SPEC = importlib.util.spec_from_file_location("primitive_scope_classifier", _CLASSIFIER_PATH)
if _SPEC is None or _SPEC.loader is None:  # pragma: no cover - import guard
    raise RuntimeError(f"cannot load classifier from {_CLASSIFIER_PATH}")
primitive_scope_classifier = importlib.util.module_from_spec(_SPEC)
sys.modules["primitive_scope_classifier"] = primitive_scope_classifier
_SPEC.loader.exec_module(primitive_scope_classifier)


@dataclass(frozen=True)
class AuditCandidate:
    path: str
    declared_scope: str | None
    suggested_scope: str
    effective_scope: str
    confidence: str
    decision_source: str
    paired_portability_test: str | None
    contradiction: str
    evidence_sources: list[str]
    evidence_details: list[str]
    review_prompt: str


def _row_get(row: Any, name: str, default: Any = None) -> Any:
    if isinstance(row, dict):
        return row.get(name, default)
    return getattr(row, name, default)


def _row_to_candidate(row: Any) -> AuditCandidate:
    evidence = list(_row_get(row, "evidence", []) or [])
    sources = [str(_row_get(item, "source", "")) for item in evidence if _row_get(item, "source", "")]
    details = [str(_row_get(item, "detail", "")) for item in evidence if _row_get(item, "detail", "")]
    confidence = str(_row_get(row, "confidence", ""))
    suggested = str(_row_get(row, "suggested_scope", ""))
    prompt = (
        "Verify that the declared/effective scope matches real runtime surface, "
        "consumer projection, and content semantics. If wrong, update metadata/tests/classifier before marker changes."
    )
    if confidence != "high":
        prompt = "MEDIUM/LOW confidence: " + prompt
    return AuditCandidate(
        path=str(_row_get(row, "path", "")),
        declared_scope=_row_get(row, "declared_scope"),
        suggested_scope=suggested,
        effective_scope=str(_row_get(row, "effective_scope", suggested)),
        confidence=confidence,
        decision_source=str(_row_get(row, "decision_source", "")),
        paired_portability_test=_row_get(row, "paired_portability_test"),
        contradiction=str(_row_get(row, "contradiction", "") or ""),
        evidence_sources=sources,
        evidence_details=details[:8],
        review_prompt=prompt,
    )


def _stable_sort(rows: Iterable[Any]) -> list[Any]:
    return sorted(rows, key=lambda row: str(_row_get(row, "path", "")))


def select_sample(
    rows: list[Any],
    *,
    seed: int,
    per_scope: int = 0,
    total: int = 0,
    scopes: set[str] | None = None,
    confidences: set[str] | None = None,
) -> list[AuditCandidate]:
    """Select a deterministic random sample, optionally stratified by scope."""

    filtered = [
        row
        for row in rows
        if (not scopes or str(_row_get(row, "effective_scope", _row_get(row, "suggested_scope", ""))) in scopes)
        and (not confidences or str(_row_get(row, "confidence", "")) in confidences)
    ]
    rng = random.Random(seed)
    selected: list[Any] = []
    seen: set[str] = set()

    if per_scope > 0:
        groups: dict[str, list[Any]] = defaultdict(list)
        for row in filtered:
            scope = str(_row_get(row, "effective_scope", _row_get(row, "suggested_scope", "")))
            groups[scope].append(row)
        for scope in sorted(groups):
            group = _stable_sort(groups[scope])
            rng.shuffle(group)
            for row in group[:per_scope]:
                path = str(_row_get(row, "path", ""))
                selected.append(row)
                seen.add(path)

    remaining = [row for row in _stable_sort(filtered) if str(_row_get(row, "path", "")) not in seen]
    rng.shuffle(remaining)
    if total > 0:
        selected.extend(remaining[: max(0, total - len(selected))])
    elif per_scope <= 0:
        selected.extend(remaining[:30])

    return [_row_to_candidate(row) for row in selected]


def build_audit(root: Path, *, seed: int, per_scope: int, total: int, scopes: set[str] | None, confidences: set[str] | None) -> dict[str, Any]:
    rows = primitive_scope_classifier.build_rows(root)
    sample = select_sample(rows, seed=seed, per_scope=per_scope, total=total, scopes=scopes, confidences=confidences)
    summary = primitive_scope_classifier.summarize(rows)
    sampled_counts = Counter(candidate.effective_scope for candidate in sample)
    confidence_counts = Counter(candidate.confidence for candidate in sample)
    return {
        "schema_version": "primitive-scope-random-audit/v1",
        "seed": seed,
        "selection": {
            "per_scope": per_scope,
            "total": total,
            "scopes": sorted(scopes or []),
            "confidences": sorted(confidences or []),
        },
        "classifier_summary": summary,
        "sample_summary": {
            "total": len(sample),
            "by_effective_scope": dict(sorted(sampled_counts.items())),
            "by_confidence": dict(sorted(confidence_counts.items())),
        },
        "rows": [asdict(candidate) for candidate in sample],
    }


def write_markdown(audit: dict[str, Any], output: Path) -> None:
    lines = [
        "# Primitive Scope Random Audit",
        "",
        "Deterministic manual-review sample generated from `scripts/primitive_scope_classifier.py`. This report is a review queue, not an automatic reclassification result.",
        "",
        "## Run metadata",
        "",
        f"- Seed: `{audit['seed']}`",
        f"- Sampled rows: `{audit['sample_summary']['total']}`",
        "",
        "## Classifier summary",
        "",
        "```json",
        json.dumps(audit["classifier_summary"], indent=2, sort_keys=True),
        "```",
        "",
        "## Sample summary",
        "",
        "```json",
        json.dumps(audit["sample_summary"], indent=2, sort_keys=True),
        "```",
        "",
        "## Manual review checklist",
        "",
        "For each row, check: (1) real projection/runtime surface, (2) content semantics, (3) required metadata/proofs, (4) whether classifier rules should be strengthened before changing markers.",
        "",
        "| Path | Declared | Effective | Confidence | Source | Paired proof | Evidence | Review prompt |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in audit["rows"]:
        evidence = ", ".join(row["evidence_sources"][:4]) or "none"
        paired = row["paired_portability_test"] or ""
        lines.append(
            "| "
            f"`{row['path']}` | `{row['declared_scope'] or ''}` | `{row['effective_scope']}` | "
            f"`{row['confidence']}` | `{row['decision_source']}` | `{paired}` | {evidence} | {row['review_prompt']} |"
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _parse_csv(values: list[str] | None) -> set[str] | None:
    if not values:
        return None
    parsed = {item.strip() for raw in values for item in raw.split(",") if item.strip()}
    return parsed or None


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a deterministic random manual-audit sample for primitive scopes")
    parser.add_argument("--project-dir", type=Path, default=Path("."))
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--per-scope", type=int, default=0, help="Rows to sample per effective scope")
    parser.add_argument("--total", type=int, default=30, help="Total rows to sample after any per-scope selection")
    parser.add_argument("--scope", action="append", help="Limit to effective scope(s); repeat or comma-separate")
    parser.add_argument("--confidence", action="append", help="Limit to confidence value(s); repeat or comma-separate")
    parser.add_argument("--json-out", type=Path, default=Path(".cognitive-os/reports/primitive-scope-random-audit.json"))
    parser.add_argument("--md-out", type=Path, default=None)
    parser.add_argument("--json", action="store_true", help="Print JSON payload to stdout")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.project_dir.resolve()
    audit = build_audit(
        root,
        seed=args.seed,
        per_scope=args.per_scope,
        total=args.total,
        scopes=_parse_csv(args.scope),
        confidences=_parse_csv(args.confidence),
    )
    json_path = args.json_out if args.json_out.is_absolute() else root / args.json_out
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.md_out:
        md_path = args.md_out if args.md_out.is_absolute() else root / args.md_out
        write_markdown(audit, md_path)
    if args.json:
        json.dump(audit, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        print(json.dumps({"json": str(json_path), "sample_summary": audit["sample_summary"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
