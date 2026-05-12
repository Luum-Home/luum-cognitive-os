#!/usr/bin/env python3
# SCOPE: both
"""Audit volatile documentation claims against generated truth sources.

This is stricter than a Markdown linter: claims are declared in
manifests/documentation-truth-claims.yaml, facts are derived from generated
reports/manifests, and docs are checked for stale forbidden prose, required
phrases, source report availability, and generated fact blocks.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "documentation-truth-audit.v1"
DEFAULT_MANIFEST = Path("manifests/documentation-truth-claims.yaml")
DEFAULT_JSON = Path("docs/reports/documentation-truth-latest.json")
DEFAULT_MD = Path("docs/reports/documentation-truth-latest.md")
BLOCK_START = "<!-- GENERATED:documentation-truth:{marker}:start -->"
BLOCK_END = "<!-- GENERATED:documentation-truth:{marker}:end -->"


@dataclass(frozen=True)
class TruthRow:
    claim_id: str
    check: str
    status: str
    severity: str
    doc: str | None
    message: str
    evidence: list[str]
    next_action: str


def read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def rel(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def implemented_harnesses(root: Path) -> list[str]:
    data = read_yaml(root / "manifests" / "harness-projection.yaml")
    harnesses = []
    for item in data.get("harnesses", []):
        if item.get("status") == "implemented" and item.get("id"):
            harnesses.append(str(item["id"]))
    return sorted(harnesses)


def json_summary(root: Path, report: str) -> dict[str, Any]:
    data = read_json(root / report)
    summary = data.get("summary", {}) if isinstance(data, dict) else {}
    status = data.get("status") or data.get("gate", {}).get("status")
    return {"status": status, "summary": summary}


def block_payload(root: Path, claim_id: str) -> list[str]:
    if claim_id == "consumer_projection_harnesses":
        harnesses = implemented_harnesses(root)
        projection = json_summary(root, "docs/reports/primitive-projection-fidelity-latest.json")
        projection_summary = projection.get("summary", {})
        return [
            "Generated documentation truth: consumer projection harnesses.",
            f"Implemented harnesses ({len(harnesses)}): {', '.join(harnesses)}.",
            f"Projection fidelity summary: {json.dumps(projection_summary, sort_keys=True)}.",
            "Structural projection is not runtime enforcement; native lifecycle enforcement remains harness-specific.",
            "Sources: manifests/harness-projection.yaml; docs/reports/primitive-projection-fidelity-latest.json.",
        ]
    if claim_id == "primitive_authority_write_effects":
        authority = json_summary(root, "docs/reports/primitive-authority-latest.json")
        summary = authority.get("summary", {})
        return [
            "Generated documentation truth: primitive authority/write-effects.",
            f"Authority audit status: {authority.get('status') or 'unknown'}.",
            f"Scripts audited: {summary.get('total_scripts', 0)}; blockers: {summary.get('block_count', 0)}; dynamic smokes: {summary.get('dynamic_smokes', 0)}; dynamic blocks: {summary.get('dynamic_blocks', 0)}.",
            "Contract surfaces: manifests/primitive-authority.yaml; scripts/primitive_authority_audit.py; ACC adapter authority_write_effects.",
            "Sources: docs/reports/primitive-authority-latest.json; docs/adrs/ADR-276-primitive-authority-write-effects.md.",
        ]
    if claim_id == "documentation_truth_control":
        manifest = read_yaml(root / DEFAULT_MANIFEST)
        claims = sorted((manifest.get("claims") or {}).keys())
        return [
            "Generated documentation truth: documentation truth control.",
            f"Declared truth claims ({len(claims)}): {', '.join(claims)}.",
            "Contract surfaces: manifests/documentation-truth-claims.yaml; scripts/documentation_truth_audit.py; ACC adapter documentation_truth.",
            "Report surfaces: docs/reports/documentation-truth-latest.json; docs/reports/documentation-truth-latest.md.",
        ]
    return [f"Generated documentation truth: {claim_id}."]


def render_block(root: Path, claim_id: str, marker: str) -> str:
    lines = [BLOCK_START.format(marker=marker)]
    lines.extend(block_payload(root, claim_id))
    lines.append(BLOCK_END.format(marker=marker))
    return "\n".join(lines)


def find_block(text: str, marker: str) -> tuple[int, int, str] | None:
    start = BLOCK_START.format(marker=marker)
    end = BLOCK_END.format(marker=marker)
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    match = pattern.search(text)
    if not match:
        return None
    return match.start(), match.end(), match.group(0)


def update_block(root: Path, doc: str, claim_id: str, marker: str) -> bool:
    path = root / doc
    expected = render_block(root, claim_id, marker)
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    found = find_block(text, marker)
    if found:
        start, end, current = found
        if current == expected:
            return False
        path.write_text(text[:start] + expected + text[end:], encoding="utf-8")
        return True
    insertion = "\n\n" + expected + "\n"
    path.write_text(text.rstrip() + insertion, encoding="utf-8")
    return True


def audit(root: Path, manifest_path: Path) -> list[TruthRow]:
    manifest = read_yaml(manifest_path)
    rows: list[TruthRow] = []
    for claim_id, claim in sorted((manifest.get("claims") or {}).items()):
        severity = str(claim.get("severity") or "medium")
        source_reports = [str(p) for p in claim.get("source_reports", [])]
        required_docs = [str(p) for p in claim.get("required_docs", [])]
        existing_doc_text: dict[str, str] = {}
        for report in source_reports:
            path = root / report
            if report == DEFAULT_JSON.as_posix():
                rows.append(TruthRow(claim_id, "source_report_self", "pass", severity, report, "Self-generated documentation truth report is produced by this audit", [report], "keep audit in refresh lane"))
                continue
            if not path.exists():
                rows.append(TruthRow(claim_id, "source_report_exists", "block", severity, report, "Required source report is missing", [report], "generate the source report or demote the claim"))
                continue
            data = read_json(path) if path.suffix == ".json" else {}
            status = data.get("status") if isinstance(data, dict) else None
            if status == "block":
                rows.append(TruthRow(claim_id, "source_report_status", "block", severity, report, "Source report is currently blocking", [f"status:{status}"], "fix source report blockers before claiming docs are current"))
            else:
                rows.append(TruthRow(claim_id, "source_report_exists", "pass", severity, report, "Required source report exists", [report], "keep report generated"))
        for doc in required_docs:
            path = root / doc
            if not path.exists():
                rows.append(TruthRow(claim_id, "required_doc_exists", "block", severity, doc, "Required documentation surface is missing", [doc], "create or relink the canonical doc"))
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            existing_doc_text[doc] = text
            rows.append(TruthRow(claim_id, "required_doc_exists", "pass", severity, doc, "Required documentation surface exists", [doc], "keep doc linked"))
            lowered = text.lower()
            for phrase in claim.get("forbidden_phrases", []) or []:
                phrase = str(phrase)
                status = "block" if phrase.lower() in lowered else "pass"
                rows.append(TruthRow(claim_id, "forbidden_phrase", status, severity, doc, f"Forbidden stale phrase {'present' if status == 'block' else 'absent'}: {phrase}", [phrase], "remove stale or contradictory prose"))
        joined_docs = "\n".join(existing_doc_text.values())
        for phrase in claim.get("required_phrases", []) or []:
            phrase = str(phrase)
            status = "pass" if phrase in joined_docs else "block"
            rows.append(TruthRow(claim_id, "required_phrase", status, severity, None, f"Required phrase {'present' if status == 'pass' else 'missing'}: {phrase}", [phrase], "add or regenerate current-truth prose"))
        block = claim.get("generated_block") or {}
        if block.get("required"):
            doc = str(block.get("doc") or "")
            marker = str(block.get("marker") or claim_id)
            path = root / doc
            expected = render_block(root, claim_id, marker)
            if not path.exists():
                rows.append(TruthRow(claim_id, "generated_block", "block", severity, doc, "Generated block doc is missing", [doc], "create doc and generated block"))
            else:
                found = find_block(path.read_text(encoding="utf-8", errors="replace"), marker)
                if not found:
                    rows.append(TruthRow(claim_id, "generated_block", "block", severity, doc, "Generated truth block is missing", [marker], "run documentation_truth_audit.py --update-generated"))
                elif found[2] != expected:
                    rows.append(TruthRow(claim_id, "generated_block", "block", severity, doc, "Generated truth block is stale", [marker], "run documentation_truth_audit.py --update-generated"))
                else:
                    rows.append(TruthRow(claim_id, "generated_block", "pass", severity, doc, "Generated truth block matches current facts", [marker], "keep block generated"))
    return rows


def summarize(rows: list[TruthRow]) -> dict[str, Any]:
    by_status: dict[str, int] = {}
    by_claim: dict[str, dict[str, int]] = {}
    for row in rows:
        by_status[row.status] = by_status.get(row.status, 0) + 1
        by_claim.setdefault(row.claim_id, {})
        by_claim[row.claim_id][row.status] = by_claim[row.claim_id].get(row.status, 0) + 1
    return {"rows": len(rows), "by_status": dict(sorted(by_status.items())), "by_claim": by_claim, "block_count": by_status.get("block", 0)}


def render_markdown(report: dict[str, Any]) -> str:
    PIPE = '\\|'
    lines = ["# Documentation Truth Audit — Latest", "", f"Generated: {report['generated_at']}", f"Status: `{report['status']}`", "", "## Summary", ""]
    for key, value in report["summary"].items():
        lines.append(f"- {key}: `{value}`")
    lines += ["", "## Blocking rows", "", "| Claim | Check | Doc | Message | Next action |", "|---|---|---|---|---|"]
    blockers = [row for row in report["rows"] if row["status"] == "block"]
    if not blockers:
        lines.append("| none | - | - | - | - |")
    for row in blockers[:120]:
        lines.append(f"| `{row['claim_id']}` | `{row['check']}` | `{row.get('doc') or ''}` | {row['message'].replace('|', PIPE)} | {row['next_action'].replace('|', PIPE)} |")
    return "\n".join(lines) + "\n"


def build_report(root: Path, manifest_path: Path) -> dict[str, Any]:
    rows = audit(root, manifest_path)
    summary = summarize(rows)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": "block" if summary["block_count"] else "pass",
        "manifest": rel(root, manifest_path),
        "summary": summary,
        "rows": [asdict(row) for row in rows],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", default=str(ROOT))
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--update-generated", action="store_true")
    parser.add_argument("--fail-on-block", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.project_dir).resolve()
    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = root / manifest_path
    manifest = read_yaml(manifest_path)
    if args.update_generated:
        for claim_id, claim in sorted((manifest.get("claims") or {}).items()):
            block = claim.get("generated_block") or {}
            if block.get("required"):
                update_block(root, str(block.get("doc") or ""), claim_id, str(block.get("marker") or claim_id))
    report = build_report(root, manifest_path)
    if not args.no_write:
        json_path = root / DEFAULT_JSON
        md_path = root / DEFAULT_MD
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        md_path.write_text(render_markdown(report), encoding="utf-8")
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(json.dumps({"status": report["status"], "summary": report["summary"]}, sort_keys=True))
    if args.fail_on_block and report["status"] == "block":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
