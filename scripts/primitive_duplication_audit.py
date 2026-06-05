#!/usr/bin/env python3
# SCOPE: os-only
"""Detect duplicated primitive/config/code patterns and suggest common homes.

This audit is intentionally local and dependency-free. External clone detectors
(jscpd, PMD CPD, pylint R0801) can still be used for deeper scans, but this
script emits Cognitive OS-specific recommendations: whether repeated material
should move to lib/, scripts/_lib/, hooks/_lib/, manifests/, templates/, rules/,
or skills/ and whether the duplicated surface is consumer-project relevant.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.script_io import read_text as read_text
from lib.duplicate_scanner import (
    collect_text_files,
    lexical_pairs,
    normalized_tokens,
    python_ast_function_repeats,
    shell_function_repeats,
    stable_id,
)
from lib.script_helpers import shingles
from lib.script_io import write_json as write_json
from lib.similarity import jaccard, pair_key
from lib.project_paths import relpath as rel
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - PyYAML is a repo dependency.
    yaml = None  # type: ignore[assignment]

WORD_RE = re.compile(r"[A-Za-z0-9_./:-]+")
SHELL_FUNCTION_RE = re.compile(
    r"(?m)^\s*(?:function\s+([A-Za-z_][A-Za-z0-9_-]*)\s*(?:\(\))?|([A-Za-z_][A-Za-z0-9_-]*)\s*\(\))\s*\{\s*$"
)
DEFAULT_INCLUDE = ["scripts", "hooks", "manifests", "rules", "skills", "cognitive-os.yaml"]
EXCLUDE_PARTS = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache"}
TEXT_SUFFIXES = {".py", ".sh", ".bash", ".zsh", ".yaml", ".yml", ".json", ".md"}
DEFAULT_ALLOWLIST = "manifests/primitive-duplication-allowlist.yaml"


@dataclass(frozen=True)
class Finding:
    finding_id: str
    kind: str
    severity: str
    confidence: float
    left: str
    right: str
    similarity: float
    recommendation: str
    common_home: str
    consumer_relevance: str
    rationale: str
    classification: str = "candidate"

    pair_key = property(lambda self: pair_key(self.left, self.right))
def collect_files(root: Path, include: list[str]) -> list[Path]:
    return collect_text_files(
        root,
        include,
        text_suffixes=TEXT_SUFFIXES,
        exclude_parts=EXCLUDE_PARTS,
        special_names={"cognitive-os.yaml", "AGENTS.md", "README.md"},
        tracked_only=False,
    )


def common_home_for_path(path: str, kind: str) -> str:
    if kind == "python-function-repeat":
        return "lib/"
    if kind == "bash-function-repeat":
        return "hooks/_lib/" if path.startswith("hooks/") else "scripts/_lib/"
    if kind in {"yaml-structural-repeat", "config-pattern-repeat"}:
        return "manifests/"
    if kind == "primitive-overlap":
        return "skills/ or rules/"
    return "templates/ or lib/"


def consumer_relevance(left: str, right: str) -> str:
    paths = (left, right)
    if any(path.startswith(("skills/", "rules/", "hooks/")) for path in paths):
        return "consumer-project-relevant"
    if any(path.startswith("manifests/") for path in paths):
        return "projection-contract-relevant"
    return "so-local-first"


def exact_and_near_findings(root: Path, files: list[Path], min_tokens: int, shingle_size: int, threshold: float) -> list[Finding]:
    findings: list[Finding] = []
    for pair in lexical_pairs(
        root,
        files,
        min_tokens=min_tokens,
        shingle_size=shingle_size,
        threshold=threshold,
        skip_fenced_blocks=True,
        ignore_markdown_primitives=True,
    ):
        kind = "exact-copy" if pair.exact else "near-copy"
        home = common_home_for_path(pair.left, kind)
        findings.append(
            Finding(
                stable_id(kind, pair.left, pair.right),
                kind,
                "high" if pair.exact else "medium",
                0.9 if pair.exact else 0.72,
                pair.left,
                pair.right,
                pair.similarity,
                "extract-common" if pair.exact else "review-abstraction",
                home,
                consumer_relevance(pair.left, pair.right),
                "normalized file content is duplicated" if pair.exact else "token shingles are highly similar",
            )
        )
    return findings




def python_function_fingerprints(root: Path, files: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for repeat in python_ast_function_repeats(root, files, min_dump_chars=180, skip_trivial_main=True):
        left_path = repeat.left.split("::", 1)[0]
        right_path = repeat.right.split("::", 1)[0]
        findings.append(
            Finding(
                stable_id("python-function-repeat", repeat.left, repeat.right, repeat.digest),
                "python-function-repeat",
                "medium",
                0.86,
                repeat.left,
                repeat.right,
                repeat.similarity,
                "extract-common-python-helper",
                "lib/",
                consumer_relevance(left_path, right_path),
                "Python functions have identical normalized AST bodies",
            )
        )
    return findings


def shell_function_findings(root: Path, files: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for repeat in shell_function_repeats(root, files, min_tokens=20):
        left_path = repeat.left.split("::", 1)[0]
        right_path = repeat.right.split("::", 1)[0]
        home = common_home_for_path(right_path, "bash-function-repeat")
        findings.append(
            Finding(
                stable_id("bash-function-repeat", repeat.left, repeat.right, repeat.digest),
                "bash-function-repeat",
                "medium",
                0.84,
                repeat.left,
                repeat.right,
                repeat.similarity,
                "extract-common-shell-helper",
                home,
                consumer_relevance(left_path, right_path),
                "Shell functions have identical normalized bodies",
            )
        )
    return findings




def yaml_signature(value: Any) -> str:
    if isinstance(value, dict):
        return "dict:" + ",".join(f"{key}:{yaml_signature(value[key])}" for key in sorted(value))
    if isinstance(value, list):
        if not value:
            return "list:empty"
        return "list:" + yaml_signature(value[0])
    return type(value).__name__


def yaml_structural_findings(root: Path, files: list[Path]) -> list[Finding]:
    if yaml is None:
        return []
    seen: dict[str, str] = {}
    findings: list[Finding] = []
    for path in files:
        if path.suffix not in {".yaml", ".yml"} and path.name != "cognitive-os.yaml":
            continue
        try:
            data = yaml.safe_load(read_text(path))
        except Exception:
            continue
        if not isinstance(data, dict) or len(data) < 2:
            continue
        signature = yaml_signature(data)
        if len(signature) < 80:
            continue
        digest = hashlib.sha1(signature.encode("utf-8")).hexdigest()
        current = rel(root, path)
        if digest in seen and seen[digest] != current:
            left = seen[digest]
            findings.append(
                Finding(
                    stable_id("yaml-structural-repeat", left, current, digest),
                    "yaml-structural-repeat",
                    "medium",
                    0.78,
                    left,
                    current,
                    1.0,
                    "extract-manifest-base-or-profile",
                    "manifests/",
                    consumer_relevance(left, current),
                    "YAML files share the same structural schema shape",
                )
            )
        else:
            seen[digest] = current
    return findings


def primitive_overlap_findings(root: Path, files: list[Path], threshold: float) -> list[Finding]:
    primitive_files = [path for path in files if path.as_posix().endswith("SKILL.md") or rel(root, path).startswith("rules/")]
    records = [(rel(root, path), shingles(normalized_tokens(read_text(path), skip_fenced_blocks=True), 6)) for path in primitive_files]
    findings: list[Finding] = []
    for index, (left, left_shingles) in enumerate(records):
        for right, right_shingles in records[index + 1 :]:
            similarity = round(jaccard(left_shingles, right_shingles), 4)
            if similarity >= threshold:
                findings.append(
                    Finding(
                        stable_id("primitive-overlap", left, right),
                        "primitive-overlap",
                        "medium",
                        0.7,
                        left,
                        right,
                        similarity,
                        "merge-deprecate-or-document-boundary",
                        "skills/ or rules/",
                        "consumer-project-relevant",
                        "Agentic primitive prose/procedure is highly similar",
                    )
                )
    return findings


def dedupe_findings(findings: list[Finding]) -> list[Finding]:
    by_id: dict[str, Finding] = {}
    for finding in findings:
        by_id.setdefault(finding.finding_id, finding)
    return sorted(by_id.values(), key=lambda item: (-item.similarity, item.kind, item.left, item.right))


def load_allowlist(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    if yaml is None:
        return []
    loaded = yaml.safe_load(read_text(path)) or {}
    if isinstance(loaded, dict):
        entries = loaded.get("entries", [])
    elif isinstance(loaded, list):
        entries = loaded
    else:
        entries = []
    return [entry for entry in entries if isinstance(entry, dict)]


def allowlist_entry_matches(finding: Finding, entry: dict[str, Any]) -> bool:
    if entry.get("finding_id") == finding.finding_id:
        return True
    left = entry.get("left")
    right = entry.get("right")
    if left and right and {left, right} == {finding.left, finding.right}:
        return entry.get("kind") in {None, finding.kind}
    pattern = entry.get("pair_key")
    if pattern and pattern == finding.pair_key:
        return entry.get("kind") in {None, finding.kind}
    return False


def apply_allowlist(findings: list[Finding], entries: list[dict[str, Any]]) -> list[Finding]:
    if not entries:
        return findings
    filtered: list[Finding] = []
    for finding in findings:
        match = next((entry for entry in entries if allowlist_entry_matches(finding, entry)), None)
        if not match:
            filtered.append(finding)
            continue
        action = str(match.get("action", "classify"))
        if action == "suppress":
            continue
        classification = str(match.get("classification", finding.classification))
        recommendation = str(match.get("recommendation", finding.recommendation))
        rationale = str(match.get("reason", finding.rationale))
        filtered.append(
            Finding(
                finding.finding_id,
                finding.kind,
                finding.severity,
                finding.confidence,
                finding.left,
                finding.right,
                finding.similarity,
                recommendation,
                finding.common_home,
                finding.consumer_relevance,
                rationale,
                classification,
            )
        )
    return filtered


def summarize(findings: list[Finding], files_scanned: int) -> dict[str, Any]:
    by_kind: dict[str, int] = {}
    by_home: dict[str, int] = {}
    by_relevance: dict[str, int] = {}
    for finding in findings:
        by_kind[finding.kind] = by_kind.get(finding.kind, 0) + 1
        by_home[finding.common_home] = by_home.get(finding.common_home, 0) + 1
        by_relevance[finding.consumer_relevance] = by_relevance.get(finding.consumer_relevance, 0) + 1
    return {
        "files_scanned": files_scanned,
        "findings": len(findings),
        "by_kind": dict(sorted(by_kind.items())),
        "by_common_home": dict(sorted(by_home.items())),
        "by_consumer_relevance": dict(sorted(by_relevance.items())),
    }


def audit(
    root: Path,
    include: list[str],
    min_tokens: int,
    shingle_size: int,
    threshold: float,
    primitive_threshold: float,
    allowlist_path: Path | None = None,
) -> dict[str, Any]:
    files = collect_files(root, include)
    findings = dedupe_findings(
        [
            *exact_and_near_findings(root, files, min_tokens, shingle_size, threshold),
            *python_function_fingerprints(root, files),
            *shell_function_findings(root, files),
            *yaml_structural_findings(root, files),
            *primitive_overlap_findings(root, files, primitive_threshold),
        ]
    )
    allowlist_entries = load_allowlist(allowlist_path)
    findings = apply_allowlist(findings, allowlist_entries)
    return {
        "schema_version": "primitive-duplication-audit.v1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "project": {"root": "<repo-root>"},
        "parameters": {
            "include": include,
            "min_tokens": min_tokens,
            "shingle_size": shingle_size,
            "threshold": threshold,
            "primitive_threshold": primitive_threshold,
            "allowlist": rel(root, allowlist_path) if allowlist_path and allowlist_path.is_relative_to(root) else str(allowlist_path) if allowlist_path else None,
        },
        "summary": summarize(findings, len(files)),
        "findings": [asdict(finding) | {"pair_key": finding.pair_key} for finding in findings],
    }



def finding_identity(finding: dict[str, Any]) -> str:
    """Return a stable identity for ratcheting across report regenerations."""
    finding_id = finding.get("finding_id")
    if isinstance(finding_id, str) and finding_id:
        return f"id:{finding_id}"
    pair = finding.get("pair_key")
    kind = finding.get("kind")
    if isinstance(pair, str) and isinstance(kind, str):
        return f"pair:{kind}:{pair}"
    left = finding.get("left")
    right = finding.get("right")
    if isinstance(left, str) and isinstance(right, str) and isinstance(kind, str):
        return f"lr:{kind}:{pair_key(left, right)}"
    return json.dumps(finding, sort_keys=True)


def baseline_entries(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Serialize current findings into a compact ratchet baseline."""
    entries: list[dict[str, Any]] = []
    for finding in data.get("findings", []):
        if not isinstance(finding, dict):
            continue
        entries.append(
            {
                "finding_id": finding.get("finding_id"),
                "kind": finding.get("kind"),
                "left": finding.get("left"),
                "right": finding.get("right"),
                "pair_key": finding.get("pair_key"),
            }
        )
    return entries


def write_baseline(path: Path, data: dict[str, Any]) -> None:
    """Persist the current duplicate set as an explicit no-growth baseline."""
    payload = {
        "schema_version": "primitive-duplication-baseline.v1",
        "timestamp": data.get("timestamp"),
        "parameters": data.get("parameters", {}),
        "summary": data.get("summary", {}),
        "entries": baseline_entries(data),
    }
    write_json(path, payload)


def load_baseline(path: Path | None) -> dict[str, Any] | None:
    """Load a duplication baseline, returning None when absent."""
    if path is None or not path.exists():
        return None
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"{path} must contain a JSON object baseline")
    return loaded


def apply_baseline_ratchet(data: dict[str, Any], baseline_path: Path | None) -> dict[str, Any]:
    """Annotate audit data with new findings relative to the baseline."""
    baseline = load_baseline(baseline_path)
    findings = [item for item in data.get("findings", []) if isinstance(item, dict)]
    if baseline is None:
        data["ratchet"] = {
            "baseline": str(baseline_path) if baseline_path else None,
            "status": "missing-baseline",
            "baseline_findings": 0,
            "current_findings": len(findings),
            "new_findings": len(findings),
            "new_finding_ids": [finding.get("finding_id") for finding in findings],
        }
        return data

    baseline_items = [item for item in baseline.get("entries", []) if isinstance(item, dict)]
    baseline_identities = {finding_identity(item) for item in baseline_items}
    new_findings = [finding for finding in findings if finding_identity(finding) not in baseline_identities]
    data["ratchet"] = {
        "baseline": str(baseline_path) if baseline_path else None,
        "status": "pass" if not new_findings else "fail",
        "baseline_findings": len(baseline_items),
        "current_findings": len(findings),
        "new_findings": len(new_findings),
        "new_finding_ids": [finding.get("finding_id") for finding in new_findings],
    }
    return data

def render_markdown(data: dict[str, Any]) -> str:
    summary = data["summary"]
    ratchet = data.get("ratchet") if isinstance(data.get("ratchet"), dict) else None
    lines = [
        "# Primitive Duplication Audit — Latest",
        "",
        f"Generated: `{data['timestamp']}`",
        "",
        "## Summary",
        "",
        f"- Files scanned: {summary['files_scanned']}",
        f"- Findings: {summary['findings']}",
        f"- By kind: `{json.dumps(summary['by_kind'], sort_keys=True)}`",
        f"- By common home: `{json.dumps(summary['by_common_home'], sort_keys=True)}`",
        f"- By consumer relevance: `{json.dumps(summary['by_consumer_relevance'], sort_keys=True)}`",
    ]
    if ratchet:
        lines += [
            f"- Ratchet status: `{ratchet.get('status')}`",
            f"- Baseline findings: {ratchet.get('baseline_findings')}",
            f"- New findings: {ratchet.get('new_findings')}",
        ]
    lines += [
        "",
        "## Top Candidates",
        "",
        "| Kind | Classification | Similarity | Left | Right | Recommendation | Common home | Consumer relevance |",
        "|---|---|---:|---|---|---|---|---|",
    ]
    for finding in data.get("findings", [])[:100]:
        lines.append(
            f"| {finding['kind']} | {finding.get('classification', 'candidate')} | {finding['similarity']} | `{finding['left']}` | `{finding['right']}` | {finding['recommendation']} | `{finding['common_home']}` | {finding['consumer_relevance']} |"
        )
    if not data.get("findings"):
        lines.append("| none | none | 0 |  |  |  |  |  |")
    lines += [
        "",
        "## Interpretation",
        "",
        "- Treat findings as refactor candidates, not automatic rewrite instructions.",
        "- Keep intentional duplication only when isolation, portability, or harness-specific behavior is documented.",
        "- Promote repeated projected primitive behavior into shared rules/skills/hooks only after ACC projection proof exists.",
    ]
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Detect duplicated primitive/code/config patterns and recommend common homes")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--include", action="append", default=None, help="File or directory to scan; repeatable")
    parser.add_argument("--min-tokens", type=int, default=80)
    parser.add_argument("--shingle-size", type=int, default=8)
    parser.add_argument("--threshold", type=float, default=0.82)
    parser.add_argument("--primitive-threshold", type=float, default=0.68)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--json-out", default="docs/06-Daily/reports/primitive-duplication-latest.json")
    parser.add_argument("--markdown", default="docs/06-Daily/reports/primitive-duplication-latest.md")
    parser.add_argument("--allowlist", default=DEFAULT_ALLOWLIST)
    parser.add_argument("--baseline", default=None, help="JSON baseline used by --fail-on-new")
    parser.add_argument("--write-baseline", action="store_true", help="Write current findings to --baseline")
    parser.add_argument("--fail-on-new", action="store_true", help="Fail only when findings are not present in --baseline")
    parser.add_argument("--fail-on-findings", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.project_root).resolve()
    include = args.include or DEFAULT_INCLUDE
    allowlist_path = root / args.allowlist if args.allowlist else None
    baseline_path = root / args.baseline if args.baseline else None
    data = audit(root, include, args.min_tokens, args.shingle_size, args.threshold, args.primitive_threshold, allowlist_path)
    if baseline_path:
        data = apply_baseline_ratchet(data, baseline_path)
        if isinstance(data.get("ratchet"), dict):
            data["ratchet"]["baseline"] = args.baseline
        if args.write_baseline:
            write_baseline(baseline_path, data)

    json_path = root / args.json_out
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    md_path = root / args.markdown
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_markdown(data), encoding="utf-8")

    if args.json or True:
        print(json.dumps({"json": str(json_path), "markdown": str(md_path), "summary": data["summary"]}, sort_keys=True))

    if args.fail_on_findings and data["summary"]["findings"]:
        return 1
    if args.fail_on_new and data.get("ratchet", {}).get("new_findings", 0):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
