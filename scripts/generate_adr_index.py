#!/usr/bin/env python3
# SCOPE: os-only
"""Generate docs/02-Decisions/adrs/INDEX.md from ADR metadata.

The generator follows docs/02-Decisions/adrs/STATUS-TAXONOMY.md: decision status, implementation
status, and index bucket are separate concepts.
"""
from __future__ import annotations

import argparse
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
ADRS_DIR = ROOT / "docs" / "02-Decisions" / "adrs"
INDEX = ADRS_DIR / "INDEX.md"
TAXONOMY = "STATUS-TAXONOMY.md"

CANONICAL_STATUSES = {
    "proposed",
    "exploration",
    "accepted",
    "implemented",
    "resolved",
    "superseded",
    "deprecated",
    "tombstone",
}
BUCKETS = ["Active", "Proposed", "Exploration", "Resolved", "Superseded", "Deprecated", "Tombstone", "Other"]
ACTIVE_IMPL_BUCKETS = [
    ("implemented", "Implemented"),
    ("partial", "Partial"),
    ("partial-blocked", "Partial / Blocked"),
    ("blocked", "Blocked"),
    ("deferred", "Deferred"),
    ("planned", "Planned"),
    ("not-applicable", "Not Applicable"),
    ("", "Unclassified"),
]
STATUS_TO_BUCKET = {
    "accepted": "Active",
    "implemented": "Active",
    "proposed": "Proposed",
    "exploration": "Exploration",
    "resolved": "Resolved",
    "superseded": "Superseded",
    "deprecated": "Deprecated",
    "tombstone": "Tombstone",
}


@dataclass(frozen=True)
class AdrRow:
    sort_key: tuple[int, str, str]
    number: str
    path: Path
    title: str
    status: str
    implementation_status: str
    date: str
    summary: str
    bucket: str


def extract_frontmatter(text: str) -> dict[str, Any]:
    if not text.startswith("---\n"):
        return {}
    parts = text.split("\n---\n", 1)
    if len(parts) != 2:
        return {}
    data = yaml.safe_load(parts[0].removeprefix("---\n")) or {}
    return data if isinstance(data, dict) else {"status": data}


def first_heading(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line.removeprefix("# ").strip()
    return fallback


def normalize_title(title: str) -> str:
    title = re.sub(r"^ADR-\d+[a-zA-Z-]*\s*[—–:-]\s*", "", title).strip()
    return title or "Untitled"


def prose_status(text: str) -> str:
    head = text[:4000]
    patterns = [
        r"(?im)^status:\s*([A-Za-z-]+)",
        r"(?im)^##\s*Status\s*\n+\s*([A-Za-z-]+)",
        r"(?im)\*\*Status\*\*:\s*([A-Za-z-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, head)
        if match:
            return canonical_status(match.group(1))
    return "accepted"


def canonical_status(raw: Any) -> str:
    if not isinstance(raw, str):
        return "other"
    value = raw.strip().lower()
    if value in CANONICAL_STATUSES:
        return value
    if "tombstone" in value:
        return "tombstone"
    if "exploration" in value:
        return "exploration"
    if "resolved" in value:
        return "resolved"
    if "superseded" in value:
        return "superseded"
    if "deprecated" in value or "retired" in value:
        return "deprecated"
    if "implemented" in value:
        return "implemented"
    if "accepted" in value or "active" in value:
        return "accepted"
    if "proposed" in value or "draft" in value:
        return "proposed"
    return "other"


def first_summary(text: str) -> str:
    body = text.split("\n---\n", 1)[-1] if text.startswith("---\n") else text
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("<!--"):
            continue
        if stripped.startswith("**Status**") or stripped.startswith("**Date**") or stripped.startswith("**Related**"):
            continue
        if stripped in {"---", "Resolved", "Tombstone", "Accepted"}:
            continue
        return re.sub(r"\s+", " ", stripped)[:160]
    return ""


def adr_number_and_suffix(path: Path) -> tuple[str, tuple[int, str, str]]:
    match = re.match(r"ADR-(\d+)([A-Za-z]*)", path.name)
    if not match:
        return "?", (999999, "", path.name)
    num = int(match.group(1))
    suffix = match.group(2).lower()
    display = f"{int(match.group(1)):03d}{suffix}"
    return display, (num, suffix, path.name)


def row_for(path: Path) -> AdrRow:
    text = path.read_text(encoding="utf-8", errors="replace")
    fm = extract_frontmatter(text)
    number, sort_key = adr_number_and_suffix(path)
    title = normalize_title(str(fm.get("title") or first_heading(text, path.stem)))
    status = canonical_status(fm.get("status")) if "status" in fm else prose_status(text)
    impl = str(fm.get("implementation_status") or "").strip()
    date = str(fm.get("date") or "")
    bucket = STATUS_TO_BUCKET.get(status, "Other")
    return AdrRow(sort_key, number, path, title, status, impl, date, first_summary(text), bucket)


def md_escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def render_table(rows: list[AdrRow]) -> list[str]:
    out = ["| ADR | Title | Decision Status | Implementation | Date | Summary |", "|---|---|---|---|---|---|"]
    for row in sorted(rows, key=lambda r: r.sort_key):
        rel = row.path.name
        out.append(
            "| "
            + " | ".join(
                [
                    f"[{row.number}]({rel})",
                    md_escape(row.title),
                    row.status,
                    md_escape(row.implementation_status),
                    md_escape(row.date),
                    md_escape(row.summary),
                ]
            )
            + " |"
        )
    return out


def adr_paths() -> list[Path]:
    """Return committed/staged ADR files so local untracked drafts do not dirty the index."""
    result = subprocess.run(
        ["git", "ls-files", "docs/02-Decisions/adrs/ADR-*.md"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode == 0 and result.stdout.strip():
        return [ROOT / line for line in result.stdout.splitlines()]
    return sorted(ADRS_DIR.glob("ADR-*.md"))


def generate() -> str:
    rows = [row_for(path) for path in sorted(adr_paths())]
    by_bucket = {bucket: [row for row in rows if row.bucket == bucket] for bucket in BUCKETS}
    lines = [
        "# ADR Index",
        "",
        "## How to Use This Index",
        "",
        f"This generated table is the status inventory for all {len(rows)} Architecture Decision Record files (ADRs).",
        f"Status semantics are defined in [{TAXONOMY}]({TAXONOMY}): decision status, implementation status, and index bucket are separate fields.",
        "Rows link to the canonical ADR file and group by index bucket for human and agent navigation.",
        "",
    ]
    for bucket in BUCKETS:
        bucket_rows = by_bucket[bucket]
        if not bucket_rows:
            continue
        if bucket in {"Superseded", "Deprecated", "Tombstone"}:
            lines.extend(["<details>", f"<summary>{bucket} ADRs ({len(bucket_rows)})</summary>", ""])
        lines.extend([f"## {bucket}", ""])
        if bucket == "Active":
            for impl_status, label in ACTIVE_IMPL_BUCKETS:
                subgroup = [row for row in bucket_rows if row.implementation_status == impl_status]
                if not subgroup:
                    continue
                lines.extend([f"### Active / {label} ({len(subgroup)})", ""])
                lines.extend(render_table(subgroup))
                lines.append("")
        else:
            lines.extend(render_table(bucket_rows))
            lines.append("")
        if bucket in {"Superseded", "Deprecated", "Tombstone"}:
            lines.extend(["</details>", ""])
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if docs/02-Decisions/adrs/INDEX.md is not current")
    args = parser.parse_args()

    rendered = generate()
    if args.check:
        current = INDEX.read_text(encoding="utf-8") if INDEX.exists() else ""
        if current != rendered:
            print(f"{INDEX.relative_to(ROOT)} is stale; run scripts/generate_adr_index.py")
            return 1
        print(f"{INDEX.relative_to(ROOT)} is current")
        return 0

    INDEX.write_text(rendered, encoding="utf-8")
    print(f"wrote {INDEX.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
