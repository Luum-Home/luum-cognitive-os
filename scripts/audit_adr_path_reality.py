#!/usr/bin/env python3
# SCOPE: os-only
"""ADR path-reality census (ADR-342 question 1, applied to documentation).

An ADR describes reality when what it asserts can be verified against the
code, and the verification does not come from the ADR itself.

This script covers the cheapest and most conclusive of those signals:
**phantom paths** -- an ADR names a file, script, hook or module that no
longer exists in the repository.

Design constraints (rules/RULES-COMPACT.md, gates-sin-trampa):

* read-only, deterministic, no session state;
* symlink-aware -- ``hooks/`` is a symlink farm into ``packages/*/hooks/``,
  so existence is resolved with ``os.path.exists`` (which follows links),
  never with a naive index lookup;
* a finding is a hypothesis: mentions in explicitly historical prose
  ("removed", "no longer", "replaced by") are classified apart and are not
  counted against the ratchet;
* the ratchet refuses to run above reality -- a baseline higher than the
  measured count is a cushion, and is reported as an error.

Exit codes: 0 = no findings above baseline, 1 = findings, 2 = error.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

REPO = Path(__file__).resolve().parent.parent
ADR_DIR = REPO / "docs" / "02-Decisions" / "adrs"
# Both live under manifests/ because .cognitive-os/* is gitignored, and a
# ratchet that is not versioned cannot detect a regression across sessions.
BASELINE_PATH = REPO / "manifests" / "adr-path-reality-baseline.json"
SUPPRESSIONS_PATH = REPO / "manifests" / "adr-path-reality-suppressions.json"

# A token only counts as a repo path claim if its first segment is a real
# top-level entry of this repository. Everything else (URLs, dotted module
# names, other projects' paths, prose with slashes) is dropped before it can
# become a false "missing file".
PATH_EXTENSIONS = (
    ".py", ".sh", ".md", ".json", ".yaml", ".yml", ".toml", ".go",
    ".js", ".ts", ".txt", ".sql", ".cfg", ".ini", ".jsonl", ".lock",
)

# Placeholders make a token un-checkable, not missing.
PLACEHOLDER_RE = re.compile(r"[{}<>*$|%\s]|\.\.\.|\bYYYY\b|\bNNN\b|\bXXX\b")

# Inline code spans outside fenced blocks. Fenced blocks are illustrative
# (example YAML, sample output) and are deliberately not scanned.
INLINE_CODE_RE = re.compile(r"`([^`\n]{2,200})`")
FENCE_RE = re.compile(r"^\s*(```|~~~)")

HISTORICAL_MARKERS = (
    "removed", "remove ", "deleted", "delete ", "no longer", "formerly",
    "used to", "was replaced", "replaced by", "renamed", "superseded",
    "deprecated", "obsolete", "eliminated", "dropped", "retired",
    "previously", "historically", "before this adr", "instead of",
    "borrado", "eliminado", "ya no", "reemplazado", "antes ",
)

FRONTMATTER_PATH_KEYS = ("implementation_files", "verification_files", "files")

# Tokens whose basename is a stand-in in worked examples ("register hooks/x.sh,
# add tests/unit/test_foo.py"). Their absence is not documentation drift.
PLACEHOLDER_BASENAMES = {
    "x.sh", "y.sh", "foo.sh", "bar.sh", "test_foo.py", "test_bar.py",
    "foo.py", "bar.py", "example.sh", "example.py", "my-hook.sh",
    "test_hook_x.py", "new-hook.sh", "some-hook.sh",
}


@dataclass(frozen=True)
class Finding:
    adr: str
    path: str
    line: int
    origin: str  # "frontmatter" | "prose"
    verdict: str  # "missing" | "moved"
    basename_elsewhere: str
    context: str


def top_level_entries() -> set[str]:
    return {p.name for p in REPO.iterdir() if not p.name.startswith(".git")} | {
        ".claude", ".codex", ".opencode", ".cognitive-os", ".github",
    }


def looks_like_repo_path(token: str, roots: set[str]) -> bool:
    if "/" not in token:
        return False
    if PLACEHOLDER_RE.search(token):
        return False
    if token.startswith(("http:", "https:", "//", "git@")):
        return False
    if token.endswith("/"):
        return False
    first = token.split("/", 1)[0]
    if first not in roots:
        return False
    return token.endswith(PATH_EXTENSIONS)


def normalise(token: str) -> str:
    return token.strip().strip("`'\"").rstrip(".,;:)]").lstrip("([")


def basename_index() -> dict[str, list[str]]:
    """basename -> repo-relative paths, for telling 'moved' from 'gone'."""
    index: dict[str, list[str]] = {}
    skip = {".git", "node_modules", "__pycache__", ".venv", "venv", ".mypy_cache"}
    for root, dirs, files in os.walk(REPO, followlinks=False):
        dirs[:] = [d for d in dirs if d not in skip]
        for name in files:
            rel = os.path.relpath(os.path.join(root, name), REPO)
            index.setdefault(name, []).append(rel)
    return index


def gitignored(paths: list[str]) -> set[str]:
    """Paths git would ignore: runtime artifacts (metrics, state, caches).

    Their absence in a checkout is expected behaviour, not documentation
    drift, so they are classified apart instead of inflating the count.
    """
    if not paths:
        return set()
    import subprocess
    proc = subprocess.run(
        ["git", "check-ignore", "--stdin"],
        cwd=REPO, input="\n".join(paths), capture_output=True, text=True,
    )
    if proc.returncode not in (0, 1):
        raise RuntimeError(f"git check-ignore failed: {proc.stderr.strip()}")
    return {line for line in proc.stdout.splitlines() if line}


def is_historical(context: str) -> bool:
    low = context.lower()
    return any(marker in low for marker in HISTORICAL_MARKERS)


def is_mapping_source(token: str, context: str) -> bool:
    """True for the left-hand side of a `| old | new |` migration table row.

    A rename record names the path it renamed away from; that path being
    absent is the record working, not the record rotting. Only the first
    code span of such a row is the "from" side; every later column is a
    live claim about where the file is now, and is still checked.
    """
    if not context.lstrip().startswith("|"):
        return False
    spans = INLINE_CODE_RE.findall(context)
    if len(spans) < 2:
        return False
    return normalise(spans[0]) == token


def extract_candidates(text: str, roots: set[str]) -> Iterable[tuple[str, int, str, str]]:
    """Yield (path, line_number, origin, context_line)."""
    lines = text.splitlines()
    in_fence = False
    in_frontmatter = False
    fm_key: str | None = None

    for idx, line in enumerate(lines, start=1):
        if idx == 1 and line.strip() == "---":
            in_frontmatter = True
            continue
        if in_frontmatter:
            if line.strip() in ("---", "..."):
                in_frontmatter = False
                continue
            m = re.match(r"^([a-z_]+):\s*(.*)$", line)
            if m:
                fm_key = m.group(1)
                inline = m.group(2).strip()
                if fm_key in FRONTMATTER_PATH_KEYS and inline:
                    tok = normalise(inline)
                    if looks_like_repo_path(tok, roots):
                        yield tok, idx, "frontmatter", line.strip()
                continue
            m = re.match(r"^\s*-\s+(.*)$", line)
            if m and fm_key in FRONTMATTER_PATH_KEYS:
                tok = normalise(m.group(1))
                if looks_like_repo_path(tok, roots):
                    yield tok, idx, "frontmatter", line.strip()
            continue

        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        for raw in INLINE_CODE_RE.findall(line):
            tok = normalise(raw)
            if looks_like_repo_path(tok, roots):
                yield tok, idx, "prose", line.strip()


def load_suppressions() -> dict[str, str]:
    if not SUPPRESSIONS_PATH.exists():
        return {}
    data = json.loads(SUPPRESSIONS_PATH.read_text())
    out: dict[str, str] = {}
    for entry in data.get("suppressions", []):
        reason = (entry.get("reason") or "").strip()
        if not reason:
            raise ValueError(
                f"suppression without reason: {entry}. "
                "A suppression with no written motive is a cheap green."
            )
        out[f"{entry['adr']}::{entry['path']}"] = reason
    return out


def scan() -> tuple[list[Finding], list[Finding], dict[str, int]]:
    roots = top_level_entries()
    index = basename_index()
    suppressions = load_suppressions()

    candidates: list[Finding] = []
    historical: list[Finding] = []
    stats = {
        "adrs_scanned": 0,
        "adrs_with_path_claims": 0,
        "path_claims": 0,
        "distinct_path_claims": 0,
        "suppressed": 0,
        "placeholder_basenames": 0,
        "runtime_artifacts": 0,
    }
    seen: set[tuple[str, str]] = set()
    distinct: set[str] = set()

    for adr_file in sorted(ADR_DIR.glob("ADR-*.md")):
        stats["adrs_scanned"] += 1
        text = adr_file.read_text(errors="replace")
        adr = adr_file.name
        had_claim = False

        for path, line, origin, context in extract_candidates(text, roots):
            key = (adr, path)
            if key in seen:
                continue
            seen.add(key)
            had_claim = True
            stats["path_claims"] += 1
            distinct.add(path)

            if (REPO / path).exists():
                continue
            if f"{adr}::{path}" in suppressions:
                stats["suppressed"] += 1
                continue
            if os.path.basename(path) in PLACEHOLDER_BASENAMES:
                stats["placeholder_basenames"] += 1
                continue

            elsewhere = index.get(os.path.basename(path), [])
            verdict = "moved" if elsewhere else "missing"
            finding = Finding(
                adr=adr,
                path=path,
                line=line,
                origin=origin,
                verdict=verdict,
                basename_elsewhere=elsewhere[0] if elsewhere else "",
                context=context[:200],
            )
            if origin == "prose" and (is_historical(context)
                                      or is_mapping_source(path, context)):
                historical.append(finding)
            else:
                candidates.append(finding)

        if had_claim:
            stats["adrs_with_path_claims"] += 1

    stats["distinct_path_claims"] = len(distinct)

    ignored = gitignored(sorted({f.path for f in candidates}))
    findings = [f for f in candidates if f.path not in ignored]
    stats["runtime_artifacts"] = len(candidates) - len(findings)

    findings.sort(key=lambda f: (f.adr, f.path))
    historical.sort(key=lambda f: (f.adr, f.path))
    return findings, historical, stats


def load_baseline() -> int | None:
    if not BASELINE_PATH.exists():
        return None
    return int(json.loads(BASELINE_PATH.read_text())["max_findings"])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--historical", action="store_true",
                    help="also list mentions classified as historical prose")
    ap.add_argument("--write-baseline", action="store_true",
                    help="record the current count as the ratchet ceiling")
    ap.add_argument("--ignore-baseline", action="store_true",
                    help="report findings without ratchet comparison")
    args = ap.parse_args()

    if not ADR_DIR.is_dir():
        print(f"ERROR: ADR directory not found: {ADR_DIR}", file=sys.stderr)
        return 2

    try:
        findings, historical, stats = scan()
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    count = len(findings)

    if args.write_baseline:
        BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
        BASELINE_PATH.write_text(json.dumps(
            {"max_findings": count,
             "note": "Measured, not chosen. Lower it when ADRs are fixed; "
                     "raising it requires a written decision."},
            indent=2) + "\n")
        print(f"baseline written: max_findings={count}")
        return 0

    baseline = None if args.ignore_baseline else load_baseline()

    if args.json:
        print(json.dumps({
            "stats": stats,
            "findings": [asdict(f) for f in findings],
            "historical": [asdict(f) for f in historical],
            "baseline": baseline,
        }, indent=2))
    else:
        print(f"ADRs scanned................ {stats['adrs_scanned']}")
        print(f"ADRs asserting a repo path.. {stats['adrs_with_path_claims']}")
        print(f"path claims (adr,path)...... {stats['path_claims']}")
        print(f"distinct paths named........ {stats['distinct_path_claims']}")
        print(f"suppressed (with reason).... {stats['suppressed']}")
        print(f"illustrative placeholders... {stats['placeholder_basenames']}")
        print(f"runtime artifacts (ignored). {stats['runtime_artifacts']}")
        print(f"PHANTOM PATHS............... {count}")
        print(f"  of which relocated........ {sum(1 for f in findings if f.verdict == 'moved')}")
        print(f"historical mentions (info).. {len(historical)}")
        print()
        for f in findings:
            tail = f"  -> basename now at {f.basename_elsewhere}" if f.basename_elsewhere else ""
            print(f"{f.adr}:{f.line} [{f.origin}/{f.verdict}] {f.path}{tail}")
        if args.historical:
            print("\n--- historical prose (not counted) ---")
            for f in historical:
                print(f"{f.adr}:{f.line} {f.path}")

    if baseline is None:
        return 1 if count else 0
    if count > baseline:
        print(f"\nFAIL: {count} phantom paths > baseline {baseline}", file=sys.stderr)
        return 1
    if count < baseline:
        print(f"\nERROR: baseline {baseline} sits above reality {count} -- "
              f"a ratchet above the measurement is a cushion. "
              f"Re-run with --write-baseline.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
