#!/usr/bin/env python3
"""Detect duplicated primitive/config/code patterns and suggest common homes.

This audit is intentionally local and dependency-free. External clone detectors
(jscpd, PMD CPD, pylint R0801) can still be used for deeper scans, but this
script emits Cognitive OS-specific recommendations: whether repeated material
should move to lib/, scripts/_lib/, hooks/_lib/, manifests/, templates/, rules/,
or skills/ and whether the duplicated surface is consumer-project relevant.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - PyYAML is a repo dependency.
    yaml = None  # type: ignore[assignment]

WORD_RE = re.compile(r"[A-Za-z0-9_./:-]+")
SHELL_FUNCTION_RE = re.compile(r"(?m)^\s*(?:function\s+)?([A-Za-z_][A-Za-z0-9_-]*)\s*(?:\(\))?\s*\{\s*$")
DEFAULT_INCLUDE = ["scripts", "hooks", "manifests", "rules", "skills", "cognitive-os.yaml"]
EXCLUDE_PARTS = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache"}
TEXT_SUFFIXES = {".py", ".sh", ".bash", ".zsh", ".yaml", ".yml", ".json", ".md"}


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

    @property
    def pair_key(self) -> str:
        return " :: ".join(sorted([self.left, self.right]))


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def stable_id(kind: str, left: str, right: str, extra: str = "") -> str:
    digest = hashlib.sha1(f"{kind}\0{left}\0{right}\0{extra}".encode("utf-8")).hexdigest()[:12]
    return f"{kind}:{digest}"


def collect_files(root: Path, include: list[str]) -> list[Path]:
    files: list[Path] = []
    for item in include:
        base = root / item
        candidates = [base] if base.is_file() else sorted(base.rglob("*")) if base.exists() else []
        for path in candidates:
            if not path.is_file():
                continue
            if any(part in EXCLUDE_PARTS for part in path.parts):
                continue
            if path.suffix in TEXT_SUFFIXES or path.name in {"cognitive-os.yaml", "AGENTS.md", "README.md"}:
                files.append(path)
    return sorted(set(files))


def normalize_text(text: str) -> str:
    lines: list[str] = []
    in_fence = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or not stripped or stripped.startswith("#"):
            continue
        lines.append(re.sub(r"\s+", " ", stripped.lower()))
    return "\n".join(lines)


def shingles(text: str, size: int) -> set[str]:
    tokens = WORD_RE.findall(normalize_text(text))
    if len(tokens) < size:
        return set(tokens)
    return {" ".join(tokens[index : index + size]) for index in range(len(tokens) - size + 1)}


def jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


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
    records: list[tuple[str, str, int, set[str]]] = []
    for path in files:
        relative = rel(root, path)
        if path.suffix == ".md" and relative.startswith(("skills/", "rules/")):
            # Rule/skill prose is handled by primitive_overlap_findings. Keeping
            # it out of generic near-copy comparisons avoids quadratic scans
            # over large instructional documents.
            continue
        text = read_text(path)
        tokens = WORD_RE.findall(normalize_text(text))
        if len(tokens) < min_tokens:
            continue
        records.append((relative, text, len(tokens), shingles(text, shingle_size)))
    findings: list[Finding] = []
    for index, (left_path, left_text, left_count, left_shingles) in enumerate(records):
        for right_path, right_text, right_count, right_shingles in records[index + 1 :]:
            if min(left_count, right_count) / max(left_count, right_count) < 0.55:
                continue
            similarity = round(jaccard(left_shingles, right_shingles), 4)
            exact = normalize_text(left_text) == normalize_text(right_text)
            if exact or similarity >= threshold:
                kind = "exact-copy" if exact else "near-copy"
                home = common_home_for_path(left_path, kind)
                findings.append(
                    Finding(
                        stable_id(kind, left_path, right_path),
                        kind,
                        "high" if exact else "medium",
                        0.9 if exact else 0.72,
                        left_path,
                        right_path,
                        1.0 if exact else similarity,
                        "extract-common" if exact else "review-abstraction",
                        home,
                        consumer_relevance(left_path, right_path),
                        "normalized file content is duplicated" if exact else "token shingles are highly similar",
                    )
                )
    return findings


def python_function_fingerprints(root: Path, files: list[Path]) -> list[Finding]:
    seen: dict[str, tuple[str, str]] = {}
    findings: list[Finding] = []
    for path in files:
        if path.suffix != ".py":
            continue
        text = read_text(path)
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            body_dump = ast.dump(ast.Module(body=node.body, type_ignores=[]), include_attributes=False)
            if len(body_dump) < 180:
                continue
            digest = hashlib.sha1(body_dump.encode("utf-8")).hexdigest()
            current = (rel(root, path), node.name)
            if digest in seen and seen[digest][0] != current[0]:
                left_path, left_name = seen[digest]
                right = f"{current[0]}::{current[1]}"
                left = f"{left_path}::{left_name}"
                findings.append(
                    Finding(
                        stable_id("python-function-repeat", left, right, digest),
                        "python-function-repeat",
                        "medium",
                        0.86,
                        left,
                        right,
                        1.0,
                        "extract-common-python-helper",
                        "lib/",
                        consumer_relevance(left_path, current[0]),
                        "Python functions have identical normalized AST bodies",
                    )
                )
            else:
                seen[digest] = current
    return findings


def shell_function_blocks(text: str) -> list[tuple[str, str]]:
    lines = text.splitlines()
    blocks: list[tuple[str, str]] = []
    index = 0
    while index < len(lines):
        match = SHELL_FUNCTION_RE.match(lines[index])
        if not match:
            index += 1
            continue
        name = match.group(1)
        start = index
        depth = lines[index].count("{") - lines[index].count("}")
        index += 1
        while index < len(lines) and depth > 0:
            depth += lines[index].count("{") - lines[index].count("}")
            index += 1
        # Normalize the body without the declaration line so equivalent helpers
        # with different names are still detected as extraction candidates.
        block = "\n".join(lines[start + 1 : index])
        if len(WORD_RE.findall(block)) >= 20:
            blocks.append((name, normalize_text(block)))
    return blocks


def shell_function_findings(root: Path, files: list[Path]) -> list[Finding]:
    seen: dict[str, tuple[str, str]] = {}
    findings: list[Finding] = []
    for path in files:
        if path.suffix not in {".sh", ".bash", ".zsh"} and not path.name.endswith(".sh"):
            continue
        for name, block in shell_function_blocks(read_text(path)):
            digest = hashlib.sha1(block.encode("utf-8")).hexdigest()
            current = (rel(root, path), name)
            if digest in seen and seen[digest][0] != current[0]:
                left_path, left_name = seen[digest]
                left = f"{left_path}::{left_name}"
                right = f"{current[0]}::{current[1]}"
                home = common_home_for_path(current[0], "bash-function-repeat")
                findings.append(
                    Finding(
                        stable_id("bash-function-repeat", left, right, digest),
                        "bash-function-repeat",
                        "medium",
                        0.84,
                        left,
                        right,
                        1.0,
                        "extract-common-shell-helper",
                        home,
                        consumer_relevance(left_path, current[0]),
                        "Shell functions have identical normalized bodies",
                    )
                )
            else:
                seen[digest] = current
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
    records = [(rel(root, path), shingles(read_text(path), 6)) for path in primitive_files]
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


def audit(root: Path, include: list[str], min_tokens: int, shingle_size: int, threshold: float, primitive_threshold: float) -> dict[str, Any]:
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
        },
        "summary": summarize(findings, len(files)),
        "findings": [asdict(finding) | {"pair_key": finding.pair_key} for finding in findings],
    }


def render_markdown(data: dict[str, Any]) -> str:
    summary = data["summary"]
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
        "",
        "## Top Candidates",
        "",
        "| Kind | Similarity | Left | Right | Recommendation | Common home | Consumer relevance |",
        "|---|---:|---|---|---|---|---|",
    ]
    for finding in data.get("findings", [])[:100]:
        lines.append(
            f"| {finding['kind']} | {finding['similarity']} | `{finding['left']}` | `{finding['right']}` | {finding['recommendation']} | `{finding['common_home']}` | {finding['consumer_relevance']} |"
        )
    if not data.get("findings"):
        lines.append("| none | 0 |  |  |  |  |  |")
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
    parser.add_argument("--json-out", default="docs/reports/primitive-duplication-latest.json")
    parser.add_argument("--markdown", default="docs/reports/primitive-duplication-latest.md")
    parser.add_argument("--fail-on-findings", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.project_root).resolve()
    include = args.include or DEFAULT_INCLUDE
    data = audit(root, include, args.min_tokens, args.shingle_size, args.threshold, args.primitive_threshold)

    json_path = root / args.json_out
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    md_path = root / args.markdown
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_markdown(data), encoding="utf-8")

    if args.json or True:
        print(json.dumps({"json": str(json_path), "markdown": str(md_path), "summary": data["summary"]}, sort_keys=True))

    return 1 if args.fail_on_findings and data["summary"]["findings"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
