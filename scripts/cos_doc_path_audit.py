#!/usr/bin/env python3
# SCOPE: os-only
"""Audit tracked references to documentation paths.

The audit treats any tracked text file containing a docs/ reference as linked to
repository documentation, classifies the reference by operational surface, and
reports exact missing paths, unmatched globs, legacy numbered-vault drift, and
historical allowlisted references.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

SCHEMA_VERSION = "doc-path-audit/v1"
ADR = "ADR-284"

DOC_BUCKET_RE = re.compile(r"^docs/[0-9]{2}-[^/]+(?:/|$)")
DOC_REF_RE = re.compile(
    r"(?<![A-Za-z0-9_.-])(?P<raw>(?:\.\.?/)*docs/(?:[^\s`\"'<>]|%20)+)"
)
TRAILING_CHARS = ".,;:!?)]}\"'"
GLOB_CHARS = set("*?[")

# ADR-054 project-documentation convention paths. These are output/template
# paths for adopting projects, not documentation directories that must exist in
# this repository checkout. Without a separate class, generated primitive
# metadata such as `.ai/primitives/.../rules-export...json` looks like a broken
# internal docs link even though it is a valid projection target.
PROJECT_TEMPLATE_DOC_PREFIXES = {
    "docs/01-context",
    "docs/02-architecture",
    "docs/03-domain-risk",
    "docs/04-security",
    "docs/05-features",
    "docs/06-backoffice",
    "docs/07-research",
    "docs/08-standards",
    "docs/09-execution-plan",
    "docs/10-summaries",
}

SURFACE_PREFIXES: list[tuple[str, str]] = [
    ("P0", "hooks/"),
    ("P0", "scripts/"),
    ("P0", "lib/"),
    ("P0", "cmd/"),
    ("P0", "crates/"),
    ("P0", "bin/"),
    ("P0", ".githooks/"),
    ("P1", "tests/"),
    ("P2", ".ai/primitives/"),
    ("P2", "manifests/"),
    ("P2", ".github/workflows/"),
    ("P2", ".cognitive-os/"),
    ("P4", "docs/99-Archive/"),
    ("P4", "archive/"),
    ("P3", "docs/"),
    ("P3", "templates/"),
    ("P3", "rules/"),
    ("P3", "skills/"),
]

ALLOW_MARKERS = (
    "doc-path-audit: allow",
    "doc-path-audit: historical",
    "legacy-doc-path: allow",
)

# Intentionally synthetic paths used inside audit tests and fixtures. Keeping this
# list in code makes each historical allowance visible in the JSON counts instead
# of hiding it by excluding files from the scan.
ALLOWLIST_EXACT: set[tuple[str, str]] = {
    ("tests/contracts/test_docs_archive_path_drift.py", "docs/active.md"),
    ("tests/contracts/test_docs_archive_path_drift.py", "docs/99-Archive/archived/legacy.md"),
}

HISTORICAL_FILE_PREFIXES = (
    ".cognitive-os/migrations/",
    ".cognitive-os/plans/",
    "docs/",
)

EXCLUDED_TRACKED_FILES = {
    "docs/06-Daily/reports/doc-path-audit-latest.md",
}

TEXT_SUFFIXES = {
    ".adoc", ".bats", ".c", ".cfg", ".conf", ".css", ".go", ".h", ".html",
    ".ini", ".js", ".json", ".jsonl", ".jsx", ".md", ".mdx", ".py", ".rs",
    ".sh", ".sql", ".toml", ".ts", ".tsx", ".txt", ".yaml", ".yml", "",
}


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    surface: str
    file: str
    line: int
    reference: str
    normalized: str
    message: str


def run_git_ls_files(root: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
    )
    return [p for p in proc.stdout.decode("utf-8", errors="ignore").split("\0") if p]


def is_probably_text(path: Path) -> bool:
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return False
    try:
        chunk = path.read_bytes()[:4096]
    except OSError:
        return False
    return b"\0" not in chunk


def surface_for(rel_file: str) -> str:
    for surface, prefix in SURFACE_PREFIXES:
        if rel_file == prefix.rstrip("/") or rel_file.startswith(prefix):
            return surface
    if rel_file in {"Makefile", "justfile"}:
        return "P0"
    return "P3"


def strip_reference(raw: str) -> str:
    ref = raw.strip().rstrip(TRAILING_CHARS)
    # Markdown links often close as docs/file.md#anchor); keep anchors separate
    # from filesystem validation.
    while ref and ref[-1] in TRAILING_CHARS:
        ref = ref[:-1]
    ref = ref.rstrip("…")
    # Human reports often cite path.md:12 or path.md:12,34. Validate the file,
    # not the prose line-number suffix.
    ref = re.sub(r"(\.(?:md|mdx|json|yaml|yml|txt|sh|py|go|rs|toml)):\d+(?:,\d+)*$", r"\1", ref)
    return ref


def normalize_reference(root: Path, rel_file: str, ref: str) -> str | None:
    path_part = ref.split("#", 1)[0]
    if not path_part or path_part == "docs":
        return None
    if path_part.startswith("docs/"):
        return os.path.normpath(path_part)
    file_parent = (root / rel_file).parent
    try:
        resolved = (file_parent / path_part).resolve(strict=False)
        return str(resolved.relative_to(root.resolve()))
    except ValueError:
        return None


def is_glob_reference(path: str) -> bool:
    if "{" in path or "}" in path:
        return False
    return any(ch in path for ch in GLOB_CHARS)


def line_allowed(rel_file: str, ref: str, line: str, previous: str, following: str) -> bool:
    if (rel_file, ref) in ALLOWLIST_EXACT:
        return True
    window = "\n".join([previous, line, following])
    return any(marker in window for marker in ALLOW_MARKERS)


def historical_file_allowed(rel_file: str) -> bool:
    return rel_file.startswith(HISTORICAL_FILE_PREFIXES)


def project_template_doc_path(path: str) -> bool:
    """Return True for ADR-054 adopting-project documentation outputs."""
    return any(
        path == prefix
        or path.startswith(prefix + "/")
        or path.startswith(prefix + "*")
        for prefix in PROJECT_TEMPLATE_DOC_PREFIXES
    )


def historical_finding(surface: str, rel_file: str, line_no: int, ref: str, normalized: str, message: str) -> Finding:
    return Finding(
        code="historical-allowed",
        severity="info",
        surface=surface,
        file=rel_file,
        line=line_no,
        reference=ref,
        normalized=normalized,
        message=message,
    )


def classify_reference(root: Path, rel_file: str, line_no: int, line: str, previous: str, following: str, raw: str) -> Finding | None:
    ref = strip_reference(raw)
    normalized = normalize_reference(root, rel_file, ref)
    surface = surface_for(rel_file)
    if normalized is None or not normalized.startswith("docs/"):
        return Finding(
            code="ambiguous",
            severity="warn",
            surface=surface,
            file=rel_file,
            line=line_no,
            reference=ref,
            normalized=normalized or "",
            message="Could not normalize documentation reference inside repository root.",
        )

    ambiguous_tokens = ("{", "}", "…", "|", "\\", "$(", ")", "(", "$", "\n")
    if any(token in normalized for token in ambiguous_tokens):
        return Finding(
            code="ambiguous",
            severity="warn",
            surface=surface,
            file=rel_file,
            line=line_no,
            reference=ref,
            normalized=normalized,
            message="Reference contains template, regex, shell, or prose syntax and needs human review.",
        )

    if line_allowed(rel_file, normalized, line, previous, following) or line_allowed(rel_file, ref, line, previous, following):
        return Finding(
            code="historical-allowed",
            severity="info",
            surface=surface,
            file=rel_file,
            line=line_no,
            reference=ref,
            normalized=normalized,
            message="Reference is explicitly allowlisted as historical or synthetic fixture context.",
        )

    first_doc_segment = normalized.split("/", 2)[1] if "/" in normalized else ""
    broad_docs_scan = any(ch in first_doc_segment for ch in "*?[") or normalized in {"docs/*", "docs/**", "docs/**/*.md", "docs/*.md"}
    legacy = (not DOC_BUCKET_RE.match(normalized)) and not broad_docs_scan
    target = root / normalized

    if project_template_doc_path(normalized):
        return Finding(
            code="project-template",
            severity="info",
            surface=surface,
            file=rel_file,
            line=line_no,
            reference=ref,
            normalized=normalized,
            message=(
                "Reference is an ADR-054 adopting-project documentation template/output path, "
                "not a repository documentation path that must exist in this checkout."
            ),
        )

    if is_glob_reference(normalized):
        try:
            matches = list(root.glob(normalized))
        except ValueError:
            return Finding(
                code="ambiguous",
                severity="warn",
                surface=surface,
                file=rel_file,
                line=line_no,
                reference=ref,
                normalized=normalized,
                message="Documentation glob syntax cannot be validated by pathlib.",
            )
        if not matches:
            if historical_file_allowed(rel_file):
                return historical_finding(surface, rel_file, line_no, ref, normalized, "Historical file contains a documentation glob that no longer matches after migration.")
            return Finding(
                code="missing-glob",
                severity="error",
                surface=surface,
                file=rel_file,
                line=line_no,
                reference=ref,
                normalized=normalized,
                message="Documentation glob reference does not match any tracked path.",
            )
        if legacy:
            return Finding(
                code="legacy-reference",
                severity="error" if surface in {"P0", "P2"} else "warn",
                surface=surface,
                file=rel_file,
                line=line_no,
                reference=ref,
                normalized=normalized,
                message="Documentation glob uses a legacy non-numbered docs bucket.",
            )
        return None

    if not target.exists():
        suffix = Path(normalized).suffix
        if not suffix or normalized.endswith("-") or "NNN" in normalized:
            return Finding(
                code="ambiguous",
                severity="warn",
                surface=surface,
                file=rel_file,
                line=line_no,
                reference=ref,
                normalized=normalized,
                message="Reference looks like a directory, prefix, or template rather than an exact file path.",
            )
        if historical_file_allowed(rel_file):
            return historical_finding(surface, rel_file, line_no, ref, normalized, "Historical file contains an exact documentation path that no longer exists after migration.")
        return Finding(
            code="missing-exact",
            severity="error",
            surface=surface,
            file=rel_file,
            line=line_no,
            reference=ref,
            normalized=normalized,
            message="Exact documentation path does not exist after bridge removal.",
        )

    if legacy:
        if historical_file_allowed(rel_file):
            return historical_finding(surface, rel_file, line_no, ref, normalized, "Historical file contains a legacy non-numbered docs path.")
        return Finding(
            code="legacy-reference",
            severity="error" if surface in {"P0", "P2"} else "warn",
            surface=surface,
            file=rel_file,
            line=line_no,
            reference=ref,
            normalized=normalized,
            message="Reference points at a legacy non-numbered docs path.",
        )

    return None


def scan_file(root: Path, rel_file: str) -> list[Finding]:
    path = root / rel_file
    if not path.exists() or not is_probably_text(path):
        return []
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return []
    findings: list[Finding] = []
    for idx, line in enumerate(lines):
        if "docs/" not in line:
            continue
        previous = lines[idx - 1] if idx > 0 else ""
        following = lines[idx + 1] if idx + 1 < len(lines) else ""
        for match in DOC_REF_RE.finditer(line):
            finding = classify_reference(
                root=root,
                rel_file=rel_file,
                line_no=idx + 1,
                line=line,
                previous=previous,
                following=following,
                raw=match.group("raw"),
            )
            if finding is not None:
                findings.append(finding)
    return findings


def audit(root: Path, tracked_files: Sequence[str] | None = None) -> dict[str, object]:
    files = list(tracked_files) if tracked_files is not None else run_git_ls_files(root)
    findings: list[Finding] = []
    scanned_text_files = 0
    doc_linked_files = 0
    for rel_file in files:
        if rel_file in EXCLUDED_TRACKED_FILES:
            continue
        path = root / rel_file
        if not is_probably_text(path):
            continue
        scanned_text_files += 1
        try:
            has_docs = "docs/" in path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if has_docs:
            doc_linked_files += 1
        findings.extend(scan_file(root, rel_file))

    counts = {
        "missing_exact": sum(1 for f in findings if f.code == "missing-exact"),
        "missing_glob": sum(1 for f in findings if f.code == "missing-glob"),
        "legacy_reference": sum(1 for f in findings if f.code == "legacy-reference"),
        "legacy_runtime": sum(1 for f in findings if f.code == "legacy-reference" and f.surface in {"P0", "P2"}),
        "historical_allowed": sum(1 for f in findings if f.code == "historical-allowed"),
        "project_template": sum(1 for f in findings if f.code == "project-template"),
        "ambiguous": sum(1 for f in findings if f.code == "ambiguous"),
    }
    status = "fail" if counts["missing_exact"] or counts["missing_glob"] or counts["legacy_runtime"] else "pass"
    return {
        "schema_version": SCHEMA_VERSION,
        "adr": ADR,
        "status": status,
        "summary": {
            "tracked_files": len(files),
            "scanned_text_files": scanned_text_files,
            "doc_linked_files": doc_linked_files,
            "findings": len(findings),
        },
        "counts": counts,
        "findings": [asdict(f) for f in findings],
    }


def _object_map(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _finding_maps(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def report_markdown(payload: dict[str, object]) -> str:
    counts = _object_map(payload.get("counts", {}))
    summary = _object_map(payload.get("summary", {}))
    findings = _finding_maps(payload.get("findings", []))
    lines = [
        "# Documentation Path Audit — Latest",
        "",
        f"Schema: `{payload.get('schema_version', '')}`",
        f"ADR: `{payload.get('adr', '')}`",
        f"Status: `{payload.get('status', '')}`",
        "",
        "## Summary",
        "",
        f"- Tracked files: {summary['tracked_files']}",
        f"- Scanned text files: {summary['scanned_text_files']}",
        f"- Files linked to docs: {summary['doc_linked_files']}",
        f"- Findings: {summary['findings']}",
        "",
        "## Counts",
        "",
    ]
    for key, value in counts.items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Findings", ""])
    if not findings:
        lines.append("No unresolved documentation path findings.")
    else:
        lines.append("| Code | Surface | File | Line | Reference | Message |")
        lines.append("|---|---|---:|---:|---|---|")
        for item in findings:
            lines.append(
                "| {code} | {surface} | {file} | {line} | `{normalized}` | {message} |".format(
                    code=item.get("code", ""),
                    surface=item.get("surface", ""),
                    file=item.get("file", ""),
                    line=item.get("line", ""),
                    normalized=item.get("normalized") or item.get("reference", ""),
                    message=str(item.get("message", "")).replace("|", "\\|"),
                )
            )
    lines.append("")
    return "\n".join(lines)


def parse_fail_on(value: str) -> set[str]:
    aliases = {
        "missing": {"missing-exact", "missing-glob"},
        "missing-exact": {"missing-exact"},
        "missing_glob": {"missing-glob"},
        "missing-glob": {"missing-glob"},
        "legacy": {"legacy-reference"},
        "legacy-runtime": {"legacy-runtime"},
        "legacy_runtime": {"legacy-runtime"},
        "ambiguous": {"ambiguous"},
    }
    result: set[str] = set()
    for raw in filter(None, (part.strip() for part in value.split(","))):
        if raw not in aliases:
            raise SystemExit(f"unknown --fail-on category: {raw}")
        result.update(aliases[raw])
    return result


def should_fail(payload: dict[str, object], categories: set[str]) -> bool:
    counts = _object_map(payload.get("counts", {}))
    if "missing-exact" in categories and counts.get("missing_exact"):
        return True
    if "missing-glob" in categories and counts.get("missing_glob"):
        return True
    if "legacy-reference" in categories and counts.get("legacy_reference"):
        return True
    if "legacy-runtime" in categories and counts.get("legacy_runtime"):
        return True
    if "ambiguous" in categories and counts.get("ambiguous"):
        return True
    return False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit tracked references to docs/ paths.")
    parser.add_argument("--project-dir", default=".", help="Repository root to scan.")
    parser.add_argument("--json", action="store_true", help="Emit JSON payload to stdout.")
    parser.add_argument("--fail-on", default="", help="Comma list: missing, missing-exact, missing-glob, legacy, legacy-runtime, ambiguous.")
    parser.add_argument("--write-report", help="Write a Markdown report to this path.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.project_dir).resolve()
    payload = audit(root)

    if args.write_report:
        report_path = (root / args.write_report).resolve() if not Path(args.write_report).is_absolute() else Path(args.write_report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report_markdown(payload), encoding="utf-8")

    if args.json or not args.write_report:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        summary = _object_map(payload.get("summary", {}))
        print(f"doc-path-audit status={payload.get('status')} findings={summary.get('findings')}")

    fail_categories = parse_fail_on(args.fail_on)
    return 2 if should_fail(payload, fail_categories) else 0


if __name__ == "__main__":
    raise SystemExit(main())
