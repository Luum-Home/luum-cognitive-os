#!/usr/bin/env python3
# SCOPE: os-only
"""Map product-facing claims to available proof signals.

The goal is not semantic truth. It creates a durable queue of strong claims that
need code/test/metric/workflow evidence or wording demotion.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.script_io import read_text as read_text

CLAIM_PATTERNS = re.compile(
    r"(automatic|automated|auto-|self-|always|never|guarantee|enforce|block|prevent|"
    r"\b\d+%|\b\d+x|\b\d+\s+(?:hooks|skills|rules|layers|tests)|production|universal)",
    re.IGNORECASE,
)
STOPWORDS = {"the", "and", "for", "with", "that", "this", "from", "into", "your", "cos", "cognitive", "agent", "agents"}


@dataclass(frozen=True)
class ClaimRow:
    path: str
    line: int
    claim: str
    status: str
    evidence: str
    next_action: str


def candidate_docs(root: Path) -> list[Path]:
    paths = [root / "README.md", root / "docs" / "README.md"]
    paths.extend(sorted((root / "docs" / "business").glob("*.md")) if (root / "docs" / "business").exists() else [])
    paths.extend(sorted((root / "docs" / "02-Decisions" / "adrs").glob("ADR-*.md")) if (root / "docs" / "02-Decisions" / "adrs").exists() else [])
    return [path for path in paths if path.exists()]


def proof_corpus(root: Path) -> str:
    chunks: list[str] = []
    for pattern in ("hooks/**/*.sh", "scripts/**/*.py", "lib/**/*.py", "tests/**/*.py", ".github/workflows/*.yml", ".claude/settings.json"):
        for path in root.glob(pattern):
            if path.is_file():
                chunks.append(path.as_posix())
                chunks.append(read_text(path))
    return "\n".join(chunks).lower()


def terms(text: str) -> set[str]:
    return {term.lower() for term in re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}", text) if term.lower() not in STOPWORDS}


def audit(root: Path) -> list[ClaimRow]:
    corpus = proof_corpus(root)
    rows: list[ClaimRow] = []
    for path in candidate_docs(root):
        rel = path.relative_to(root).as_posix()
        in_fence = False
        for idx, line in enumerate(read_text(path).splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            if (
                not stripped
                or stripped.startswith("#")
                or stripped.startswith("|")
                or stripped.startswith("- No ")
                or (rel.startswith("docs/02-Decisions/adrs/") and len(stripped) < 120)
                or "does not " in stripped.lower()
                or "not called automatically" in stripped.lower()
                or "blocked-by:" in stripped.lower()
                or re.search(r"\bBLOCKS\b", stripped)
                or (stripped.endswith(":") and len(stripped) < 100)
                or (stripped.count("`") >= 2 and len(stripped) < 140)
                or (" = " in stripped and re.search(r"\d+.*\d+", stripped))
                or re.fullmatch(r"- [A-Za-z][A-Za-z0-9_ -]{1,40}", stripped)
                or not CLAIM_PATTERNS.search(stripped)
            ):
                continue
            claim_terms = terms(stripped)
            hits = sorted(term for term in claim_terms if term in corpus)[:8]
            if len(hits) >= 3:
                status = "mapped"
                action = "keep claim but ensure proof remains current"
            elif hits:
                status = "weak-proof"
                action = "add explicit proof link/test/metric or demote wording"
            else:
                status = "unmapped"
                action = "demote aspirational claim or add implementation proof"
            rows.append(
                ClaimRow(
                    path=rel,
                    line=idx,
                    claim=stripped[:220],
                    status=status,
                    evidence=", ".join(hits) if hits else "none found",
                    next_action=action,
                )
            )
    return rows


def write_markdown(rows: list[ClaimRow], path: Path) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.status] = counts.get(row.status, 0) + 1
    lines = ["# Claim-to-Proof Audit — Latest", "", "## Summary", ""]
    for status in ("mapped", "weak-proof", "unmapped"):
        lines.append(f"- {status}: {counts.get(status, 0)}")
    lines.extend(["", "## Claims Needing Work", "", "| File | Line | Status | Claim | Evidence | Next action |", "|---|---:|---|---|---|---|"])
    for row in rows:
        if row.status != "mapped":
            claim = row.claim.replace("|", "\\|")
            lines.append(f"| {row.path} | {row.line} | {row.status} | {claim} | {row.evidence} | {row.next_action} |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit product claims against proof corpus")
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--json-out", default="docs/06-Daily/reports/claim-proof-latest.json")
    parser.add_argument("--md-out", default="docs/06-Daily/reports/claim-proof-latest.md")
    parser.add_argument("--fail-unmapped", action="store_true", help="Exit non-zero when any strong claim has no proof signal")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.project_dir).resolve()
    rows = audit(root)
    payload = {"rows": [asdict(row) for row in rows]}
    json_path = root / args.json_out
    md_path = root / args.md_out
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(rows, md_path)
    print(json.dumps({"claims": len(rows), "json": str(json_path), "markdown": str(md_path)}, sort_keys=True))
    if args.fail_unmapped and any(row.status == "unmapped" for row in rows):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
