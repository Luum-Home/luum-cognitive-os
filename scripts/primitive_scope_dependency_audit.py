#!/usr/bin/env python3
# SCOPE: os-only
"""Audit scope asymmetries between hook primitives and rule references.

If a hook is project/both but points agents at an os-only rule, consumer installs
can expose enforcement without the policy text that explains it. This detector is
conservative: it reports literal `rules/*.md` references found in hook source.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_CLASSIFIER = ROOT / "scripts" / "primitive_scope_classifier.py"
_SPEC = importlib.util.spec_from_file_location("primitive_scope_classifier", _CLASSIFIER)
if _SPEC is None or _SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot load classifier from {_CLASSIFIER}")
primitive_scope_classifier = importlib.util.module_from_spec(_SPEC)
sys.modules["primitive_scope_classifier"] = primitive_scope_classifier
_SPEC.loader.exec_module(primitive_scope_classifier)

RULE_REF_RE = re.compile(r"rules/[A-Za-z0-9_.-]+\.md")


@dataclass(frozen=True)
class Finding:
    hook: str
    hook_scope: str
    rule: str
    rule_scope: str
    severity: str
    rationale: str


def _row_scope(row: Any) -> str:
    return str(getattr(row, "effective_scope", None) or getattr(row, "suggested_scope", "unknown"))


def build_findings(root: Path) -> list[Finding]:
    rows = {row.path: row for row in primitive_scope_classifier.build_rows(root)}
    findings: list[Finding] = []
    for rel, row in sorted(rows.items()):
        if not rel.startswith("hooks/"):
            continue
        hook_scope = _row_scope(row)
        if hook_scope not in {"project", "both"}:
            continue
        path = root / rel
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for rule in sorted(set(RULE_REF_RE.findall(text))):
            rule_row = rows.get(rule)
            if rule_row is None:
                continue
            rule_scope = _row_scope(rule_row)
            if rule_scope == "os-only":
                findings.append(
                    Finding(
                        hook=rel,
                        hook_scope=hook_scope,
                        rule=rule,
                        rule_scope=rule_scope,
                        severity="review",
                        rationale="project/both hook references an os-only rule; either project the rule, remove the dependency, or document that the reference is source-only/help text.",
                    )
                )
    return findings


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, default=Path("."))
    parser.add_argument("--json-out", type=Path, default=Path(".cognitive-os/reports/primitive-scope-dependency-audit.json"))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true", help="Exit 1 when findings exist")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.project_dir.resolve()
    findings = build_findings(root)
    payload = {
        "schema_version": "primitive-scope-dependency-audit/v1",
        "summary": {"findings": len(findings)},
        "findings": [asdict(finding) for finding in findings],
    }
    out = args.json_out if args.json_out.is_absolute() else root / args.json_out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(json.dumps({"json": str(out), **payload["summary"]}, sort_keys=True))
    return 1 if args.strict and findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
