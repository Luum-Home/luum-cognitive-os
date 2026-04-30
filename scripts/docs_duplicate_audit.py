#!/usr/bin/env python3
"""Detect near-duplicate Markdown documentation.

This audit is designed for prevention: keep today's baseline visible, then fail
when new doc pairs cross the duplicate threshold.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

WORD_RE = re.compile(r"[a-zA-Z0-9_/-]+")
DEFAULT_EXCLUDE_PARTS = {"node_modules", ".git", ".venv", "__pycache__"}


@dataclass(frozen=True)
class DocRecord:
    path: str
    title: str
    token_count: int
    shingles: set[str]


@dataclass(frozen=True)
class DuplicateFinding:
    left: str
    right: str
    similarity: float
    left_title: str
    right_title: str
    reason: str

    @property
    def pair_key(self) -> str:
        return " :: ".join(sorted([self.left, self.right]))


def read_text(path: Path) -> str:
    try:
        return path.read_text(errors="ignore")
    except OSError:
        return ""


def normalize_text(text: str) -> str:
    lines = []
    in_frontmatter = False
    for i, line in enumerate(text.splitlines()):
        stripped = line.strip()
        if i == 0 and stripped == "---":
            in_frontmatter = True
            continue
        if in_frontmatter:
            if stripped == "---":
                in_frontmatter = False
            continue
        if stripped.startswith("```"):
            continue
        if stripped.startswith("<!--") and stripped.endswith("-->"):
            continue
        lines.append(line)
    return "\n".join(lines).lower()


def title_for(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def shingles(tokens: list[str], n: int) -> set[str]:
    if len(tokens) < n:
        return set(tokens)
    return {" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def collect_docs(root: Path, include: list[str], min_tokens: int, shingle_size: int) -> list[DocRecord]:
    records: list[DocRecord] = []
    for item in include:
        base = root / item
        candidates = [base] if base.is_file() else sorted(base.rglob("*.md")) if base.exists() else []
        for path in candidates:
            if any(part in DEFAULT_EXCLUDE_PARTS for part in path.parts):
                continue
            text = read_text(path)
            normalized = normalize_text(text)
            tokens = WORD_RE.findall(normalized)
            if len(tokens) < min_tokens:
                continue
            records.append(
                DocRecord(
                    path=path.relative_to(root).as_posix(),
                    title=title_for(text, path.stem),
                    token_count=len(tokens),
                    shingles=shingles(tokens, shingle_size),
                )
            )
    return records


def jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def same_normalized_title(left: str, right: str) -> bool:
    norm_left = " ".join(WORD_RE.findall(left.lower()))
    norm_right = " ".join(WORD_RE.findall(right.lower()))
    return bool(norm_left and norm_left == norm_right)


def find_duplicates(records: list[DocRecord], threshold: float) -> list[DuplicateFinding]:
    findings: list[DuplicateFinding] = []
    for index, left in enumerate(records):
        for right in records[index + 1 :]:
            similarity = jaccard(left.shingles, right.shingles)
            title_match = same_normalized_title(left.title, right.title)
            if similarity >= threshold or (title_match and similarity >= 0.35):
                reason = "content_similarity" if similarity >= threshold else "same_title_similarity"
                findings.append(
                    DuplicateFinding(
                        left=left.path,
                        right=right.path,
                        similarity=round(similarity, 4),
                        left_title=left.title,
                        right_title=right.title,
                        reason=reason,
                    )
                )
    return sorted(findings, key=lambda item: (-item.similarity, item.left, item.right))


def load_baseline(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        data = json.loads(read_text(path))
    except json.JSONDecodeError:
        return set()
    pairs = data.get("pair_keys", [])
    return {str(pair) for pair in pairs if isinstance(pair, str)}


def render_markdown(data: dict[str, object]) -> str:
    findings = data.get("findings", [])
    new_findings = data.get("new_findings", [])
    rows = [
        "| Similarity | Reason | Left | Right |",
        "|---:|---|---|---|",
    ]
    if isinstance(findings, list):
        for finding in findings[:100]:
            if not isinstance(finding, dict):
                continue
            rows.append(
                f"| {finding.get('similarity')} | {finding.get('reason')} | `{finding.get('left')}` | `{finding.get('right')}` |"
            )
    new_rows = [f"- `{item}`" for item in new_findings] if isinstance(new_findings, list) else []
    if not new_rows:
        new_rows = ["- No new duplicate doc pairs versus baseline."]
    return "\n".join(
        [
            "# Documentation Duplicate Audit",
            "",
            f"Generated: `{data.get('timestamp')}`",
            "",
            f"Docs scanned: **{data.get('docs_scanned')}**",
            f"Duplicate pairs: **{data.get('duplicate_pairs')}**",
            f"New duplicate pairs: **{data.get('new_duplicate_pairs')}**",
            "",
            "## New Duplicate Pairs",
            "",
            *new_rows,
            "",
            "## Top Duplicate Candidates",
            "",
            *rows,
            "",
        ]
    )


def audit(root: Path, include: list[str], min_tokens: int, shingle_size: int, threshold: float, baseline_path: Path | None) -> dict[str, object]:
    records = collect_docs(root, include, min_tokens, shingle_size)
    findings = find_duplicates(records, threshold)
    baseline = load_baseline(baseline_path) if baseline_path else set()
    new_findings = [finding.pair_key for finding in findings if finding.pair_key not in baseline]
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "docs_scanned": len(records),
        "duplicate_pairs": len(findings),
        "new_duplicate_pairs": len(new_findings),
        "threshold": threshold,
        "min_tokens": min_tokens,
        "shingle_size": shingle_size,
        "pair_keys": [finding.pair_key for finding in findings],
        "new_findings": new_findings,
        "findings": [asdict(finding) | {"pair_key": finding.pair_key} for finding in findings],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Detect near-duplicate Markdown docs")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--include", action="append", default=["docs", "README.md"], help="File or directory to scan; repeatable")
    parser.add_argument("--min-tokens", type=int, default=120)
    parser.add_argument("--shingle-size", type=int, default=7)
    parser.add_argument("--threshold", type=float, default=0.72)
    parser.add_argument("--baseline", help="Existing baseline JSON path used to detect new pairs")
    parser.add_argument("--write-baseline", help="Write current duplicate pair baseline JSON to this path")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--markdown", help="Write Markdown report")
    parser.add_argument("--fail-new", action="store_true", help="Exit 1 when new duplicate pairs are found versus baseline")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.project_root).resolve()
    baseline_path = root / args.baseline if args.baseline else None
    data = audit(root, args.include, args.min_tokens, args.shingle_size, args.threshold, baseline_path)

    if args.write_baseline:
        output = root / args.write_baseline
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    if args.markdown:
        output = root / args.markdown
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_markdown(data), encoding="utf-8")

    if args.json or not args.markdown:
        print(json.dumps(data, indent=2, sort_keys=True))

    return 1 if args.fail_new and int(data["new_duplicate_pairs"]) > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
