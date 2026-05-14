#!/usr/bin/env python3
# SCOPE: os-only
"""cos_verbatim_copy_detector.py — ADR-267 Hook #2 companion detector.

Scans staged (or all) COS files for verbatim code-block matches against the
contents of .cognitive-os/external-source-cache/ to prevent accidental leakage
of research-only cloned code into committed runtime artefacts.

FINGERPRINTING APPROACH
-----------------------
Rolling SHA-256 of sliding N-line windows (default N=8).  Lines that are
comment-only, whitespace-only, or boilerplate (pure imports, pure type
annotations, single-statement one-liners) are excluded before windowing so
that common preambles do not generate spurious hits.

RISK CLASSIFICATION
-------------------
HIGH   : ≥3 consecutive matching windows  (~24+ verbatim lines)
MEDIUM : 1-2 consecutive windows, content judged non-trivial
LOW    : single window, mostly boilerplate

HONEST LIMITATIONS
------------------
Fingerprinting catches verbatim and near-verbatim copies only.  It does NOT
detect:
  • Paraphrased or lightly-reworded adaptations
  • Structural ports (same algorithm, different variable names)
  • Pseudocode descriptions or prose summaries
  • Symbol-renamed clones where every identifier is changed
  • Any conceptual or design-level reuse

Use this detector as a safety net for mechanical copy-paste, not as a complete
audit of intellectual-property provenance.

Usage
-----
  python3 scripts/cos_verbatim_copy_detector.py [options]

Options
-------
  --baseline           Write current hits to manifests/verbatim-detection-baseline.yaml
  --quick              Scan only staged files (for pre-commit speed, target <2s)
  --max-hits N         Early exit after N hits
  --format json|text   Output format (default: text)
  --allowlist PATH     Path to allowlist file (one path-prefix per line)
  --cache-dir PATH     Override external-source-cache path
  --window N           Line-window size for fingerprinting (default: 8)
  --help               Show this message and exit

Exit codes
----------
  0  No non-baseline hits found
  1  Non-baseline hits detected (or error)
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_WINDOW = 8
BASELINE_PATH = "manifests/verbatim-detection-baseline.yaml"
DEFAULT_CACHE_SUBDIR = ".cognitive-os/external-source-cache"

# Extensions considered scannable (text-based source)
SCANNABLE_EXTS = {
    ".py", ".ts", ".tsx", ".js", ".jsx",
    ".sh", ".bash",
    ".rs", ".go",
    ".toml", ".yaml", ".yml", ".json",
    ".md", ".txt",
    ".rb", ".java", ".c", ".cpp", ".h", ".hpp",
    ".swift", ".kt", ".scala",
    ".lua", ".pl", ".r", ".m",
}

# Patterns that flag a line as boilerplate / skip-worthy
_RE_BLANK = re.compile(r"^\s*$")
_RE_COMMENT = re.compile(r"^\s*(#|//|/\*|\*|<!--)")
_RE_IMPORT = re.compile(
    r"^\s*(import |from .+ import |require\(|use |include |#include )"
)
_RE_TYPE_ANNOTATION = re.compile(r"^\s*(type |interface |typedef |@[A-Za-z]+)")
_RE_SINGLE_STMT = re.compile(r"^\s*\w[\w.]*\s*[=:]\s*\S+\s*$")


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class Hit:
    cos_file: str
    cos_start: int          # 1-based
    cos_end: int            # 1-based inclusive
    cache_file: str
    cache_start: int
    cache_end: int
    fingerprint: str        # hex digest
    risk: str               # HIGH | MEDIUM | LOW
    consecutive_blocks: int


@dataclass
class BaselineEntry:
    cos_file: str
    cache_file: str
    fingerprint: str
    note: str = ""


# ---------------------------------------------------------------------------
# Fingerprinting
# ---------------------------------------------------------------------------


def _is_boilerplate(line: str) -> bool:
    """Return True if the line carries no meaningful content signal."""
    return bool(
        _RE_BLANK.match(line)
        or _RE_COMMENT.match(line)
        or _RE_IMPORT.match(line)
        or _RE_TYPE_ANNOTATION.match(line)
        or _RE_SINGLE_STMT.match(line)
    )


def _normalise(line: str) -> str:
    """Strip trailing whitespace; lower-case for hash stability."""
    return line.rstrip().lower()


def compute_fingerprints(lines: list[str], window: int) -> dict[str, tuple[int, int]]:
    """Compute rolling SHA-256 fingerprints for sliding N-line windows.

    Returns a mapping of hex_digest -> (start_line, end_line) where lines
    are 1-based.  Windows that consist entirely of boilerplate lines are
    skipped.
    """
    result: dict[str, tuple[int, int]] = {}
    n = len(lines)
    for i in range(n - window + 1):
        window_lines = lines[i : i + window]
        # Skip windows that are all boilerplate
        non_boilerplate = [ln for ln in window_lines if not _is_boilerplate(ln)]
        if not non_boilerplate:
            continue
        content = "\n".join(_normalise(ln) for ln in window_lines)
        digest = hashlib.sha256(content.encode()).hexdigest()
        # Keep first occurrence per digest
        if digest not in result:
            result[digest] = (i + 1, i + window)
    return result


def read_lines(path: Path) -> list[str] | None:
    """Read text lines from a file; return None if the file is binary/unreadable."""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            return fh.readlines()
    except OSError:
        return None


# ---------------------------------------------------------------------------
# Cache indexing
# ---------------------------------------------------------------------------


def index_cache(cache_dir: Path, window: int) -> dict[str, list[tuple[str, int, int]]]:
    """Build a fingerprint index over all scannable files in cache_dir.

    Returns: fingerprint -> [(cache_file_rel, start, end), ...]
    """
    index: dict[str, list[tuple[str, int, int]]] = {}
    if not cache_dir.is_dir():
        return index

    for root, _dirs, files in os.walk(cache_dir):
        for fname in files:
            fpath = Path(root) / fname
            if fpath.suffix.lower() not in SCANNABLE_EXTS:
                continue
            lines = read_lines(fpath)
            if lines is None:
                continue
            fps = compute_fingerprints(lines, window)
            rel = str(fpath.relative_to(cache_dir))
            for digest, (s, e) in fps.items():
                index.setdefault(digest, []).append((rel, s, e))

    return index


# ---------------------------------------------------------------------------
# Staged files
# ---------------------------------------------------------------------------


def get_staged_files(root: Path) -> list[str]:
    """Return relative paths of staged files (ACMR) from git index."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=10,
        )
        return [f for f in result.stdout.splitlines() if f]
    except (subprocess.SubprocessError, FileNotFoundError):
        return []


def get_all_cos_files(root: Path, cache_dir: Path) -> Iterator[Path]:
    """Yield all scannable COS source files (excluding the cache itself)."""
    cache_rel = cache_dir.relative_to(root) if cache_dir.is_relative_to(root) else None
    for dirpath, _dirs, files in os.walk(root):
        dp = Path(dirpath)
        # Skip cache dir itself
        if cache_rel and dp.is_relative_to(root / cache_rel):
            continue
        # Skip hidden dirs except .cognitive-os (which we already exclude via cache)
        if any(part.startswith(".") for part in dp.relative_to(root).parts):
            continue
        for fname in files:
            fpath = dp / fname
            if fpath.suffix.lower() in SCANNABLE_EXTS:
                yield fpath


# ---------------------------------------------------------------------------
# Hit detection
# ---------------------------------------------------------------------------


def _classify_risk(consecutive: int, non_boilerplate_count: int) -> str:
    if consecutive >= 3:
        return "HIGH"
    if consecutive >= 1 and non_boilerplate_count > 2:
        return "MEDIUM"
    return "LOW"


def find_hits(
    target_path: Path,
    cache_index: dict[str, list[tuple[str, int, int]]],
    window: int,
    cos_rel: str,
) -> list[Hit]:
    """Return a list of Hit objects for a single target file."""
    lines = read_lines(target_path)
    if lines is None:
        return []

    fps = compute_fingerprints(lines, window)
    if not fps:
        return []

    # Group matching windows by cache file to detect consecutive blocks
    # Structure: cache_file -> [(cos_start, cos_end, cache_start, cache_end, digest)]
    per_cache: dict[str, list[tuple[int, int, int, int, str]]] = {}
    for digest, (cos_s, cos_e) in fps.items():
        if digest in cache_index:
            for cache_file, cache_s, cache_e in cache_index[digest]:
                per_cache.setdefault(cache_file, []).append(
                    (cos_s, cos_e, cache_s, cache_e, digest)
                )

    hits: list[Hit] = []
    for cache_file, matches in per_cache.items():
        # Sort by cos_start for consecutive detection
        matches.sort(key=lambda m: m[0])
        # Walk and group consecutive windows (overlapping is fine — step is 1)
        groups: list[list[tuple[int, int, int, int, str]]] = []
        current_group: list[tuple[int, int, int, int, str]] = []
        for m in matches:
            if not current_group:
                current_group.append(m)
            else:
                prev = current_group[-1]
                # Consecutive if the next window starts within window distance
                if m[0] <= prev[1] + 1:
                    current_group.append(m)
                else:
                    groups.append(current_group)
                    current_group = [m]
        if current_group:
            groups.append(current_group)

        for group in groups:
            cos_start = group[0][0]
            cos_end = group[-1][1]
            cache_start = group[0][2]
            cache_end = group[-1][3]
            digest = group[0][4]
            consecutive = len(group)

            group_lines = lines[cos_start - 1 : cos_end]
            non_bp = sum(1 for ln in group_lines if not _is_boilerplate(ln))
            risk = _classify_risk(consecutive, non_bp)

            hits.append(
                Hit(
                    cos_file=cos_rel,
                    cos_start=cos_start,
                    cos_end=cos_end,
                    cache_file=cache_file,
                    cache_start=cache_start,
                    cache_end=cache_end,
                    fingerprint=digest,
                    risk=risk,
                    consecutive_blocks=consecutive,
                )
            )

    return hits


# ---------------------------------------------------------------------------
# Baseline I/O
# ---------------------------------------------------------------------------


def _baseline_key(h: Hit | BaselineEntry) -> str:
    if isinstance(h, Hit):
        return f"{h.cos_file}::{h.cache_file}::{h.fingerprint}"
    return f"{h.cos_file}::{h.cache_file}::{h.fingerprint}"


def load_baseline(baseline_path: Path) -> set[str]:
    """Return the set of accepted baseline keys."""
    if not baseline_path.exists():
        return set()
    keys: set[str] = set()
    try:
        with open(baseline_path, "r", encoding="utf-8") as fh:
            content = fh.read()
        # Minimal YAML parsing — look for fingerprint: lines.
        # Handles both `accepted:` (block sequence) and `accepted: []` (inline empty).
        in_accepted = False
        current: dict[str, str] = {}
        for line in content.splitlines():
            stripped = line.strip()
            if stripped in ("accepted:", "accepted: []"):
                in_accepted = True
                continue
            if in_accepted:
                if stripped.startswith("- cos_file:"):
                    if current:
                        key = f"{current.get('cos_file','')}::{current.get('cache_file','')}::{current.get('fingerprint','')}"
                        keys.add(key)
                    current = {"cos_file": stripped.split(":", 1)[1].strip()}
                elif stripped.startswith("cache_file:") and current:
                    current["cache_file"] = stripped.split(":", 1)[1].strip()
                elif stripped.startswith("fingerprint:") and current:
                    current["fingerprint"] = stripped.split(":", 1)[1].strip()
        if current:
            key = f"{current.get('cos_file','')}::{current.get('cache_file','')}::{current.get('fingerprint','')}"
            keys.add(key)
    except OSError:
        pass
    return keys


def write_baseline(baseline_path: Path, hits: list[Hit]) -> None:
    """Overwrite the baseline file with the current set of hits."""
    now = datetime.date.today().isoformat()
    lines = [
        "schema_version: verbatim-detection-baseline/v1",
        f"generated: {now}",
        "note: |",
        "  ACCEPTED hits — verbatim content from external-source-cache that has been",
        "  reviewed and is permitted (e.g. attribution comments, MIT-vendored with",
        "  proper headers). New hits NOT in this file block commits.",
        "accepted:",
    ]
    for h in hits:
        lines += [
            f"  - cos_file: {h.cos_file}",
            f"    cache_file: {h.cache_file}",
            f"    fingerprint: {h.fingerprint}",
            f"    risk: {h.risk}",
            f"    cos_lines: {h.cos_start}-{h.cos_end}",
            f"    cache_lines: {h.cache_start}-{h.cache_end}",
            f"    note: seeded by --baseline run on {now}",
        ]
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    with open(baseline_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


def format_hit_text(h: Hit) -> str:
    return (
        f"[{h.risk}] {h.cos_file}:{h.cos_start}-{h.cos_end} "
        f"matches {h.cache_file}:{h.cache_start}-{h.cache_end} "
        f"(fp={h.fingerprint[:12]}…, blocks={h.consecutive_blocks})"
    )


def format_hit_json(h: Hit) -> dict:
    return {
        "cos_file": h.cos_file,
        "cos_lines": f"{h.cos_start}-{h.cos_end}",
        "cache_file": h.cache_file,
        "cache_lines": f"{h.cache_start}-{h.cache_end}",
        "fingerprint": h.fingerprint,
        "risk": h.risk,
        "consecutive_blocks": h.consecutive_blocks,
    }


# ---------------------------------------------------------------------------
# Allowlist
# ---------------------------------------------------------------------------


def load_allowlist(allowlist_path: Path | None) -> list[str]:
    if allowlist_path is None or not allowlist_path.exists():
        return []
    with open(allowlist_path, "r", encoding="utf-8") as fh:
        return [
            ln.strip()
            for ln in fh
            if ln.strip() and not ln.strip().startswith("#")
        ]


def is_allowlisted(rel_path: str, prefixes: list[str]) -> bool:
    return any(rel_path.startswith(p) for p in prefixes)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="COS verbatim copy detector — ADR-267 Hook #2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--baseline", action="store_true", help="Seed baseline from current hits")
    p.add_argument("--quick", action="store_true", help="Scan staged files only (pre-commit mode)")
    p.add_argument("--max-hits", type=int, default=0, metavar="N", help="Early exit after N hits (0=unlimited)")
    p.add_argument("--format", choices=["text", "json"], default="text", dest="fmt")
    p.add_argument("--allowlist", type=Path, default=None)
    p.add_argument("--cache-dir", type=Path, default=None)
    p.add_argument("--window", type=int, default=DEFAULT_WINDOW)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    root = Path(
        subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True
        ).stdout.strip()
        or "."
    )

    cache_dir = args.cache_dir or (root / DEFAULT_CACHE_SUBDIR)
    baseline_path = root / BASELINE_PATH
    allowlist_prefixes = load_allowlist(args.allowlist)
    baseline_keys = load_baseline(baseline_path)

    # Build cache index
    sys.stderr.write(f"[verbatim-detector] indexing cache: {cache_dir}\n")
    cache_index = index_cache(cache_dir, args.window)
    if not cache_index:
        sys.stderr.write("[verbatim-detector] cache empty or missing — nothing to compare\n")
        return 0

    # Determine files to scan
    if args.quick:
        staged = get_staged_files(root)
        scan_paths = [root / f for f in staged if (root / f).suffix.lower() in SCANNABLE_EXTS]
        cos_rels = [f for f in staged if (root / f).suffix.lower() in SCANNABLE_EXTS]
    else:
        paths_and_rels = [
            (fp, str(fp.relative_to(root)))
            for fp in get_all_cos_files(root, cache_dir)
        ]
        scan_paths = [p for p, _ in paths_and_rels]
        cos_rels = [r for _, r in paths_and_rels]

    all_hits: list[Hit] = []
    new_hits: list[Hit] = []

    for fpath, cos_rel in zip(scan_paths, cos_rels):
        if is_allowlisted(cos_rel, allowlist_prefixes):
            continue
        if not fpath.exists():
            continue
        hits = find_hits(fpath, cache_index, args.window, cos_rel)
        for h in hits:
            all_hits.append(h)
            if _baseline_key(h) not in baseline_keys:
                new_hits.append(h)
            if args.max_hits > 0 and len(new_hits) >= args.max_hits:
                break
        if args.max_hits > 0 and len(new_hits) >= args.max_hits:
            break

    # Baseline mode: write all hits and exit 0
    if args.baseline:
        write_baseline(baseline_path, all_hits)
        print(f"[verbatim-detector] baseline written: {len(all_hits)} hits captured → {baseline_path}")
        return 0

    # Report
    if args.fmt == "json":
        output = {
            "total_hits": len(all_hits),
            "new_hits": len(new_hits),
            "hits": [format_hit_json(h) for h in new_hits],
        }
        print(json.dumps(output, indent=2))
    else:
        if new_hits:
            print(f"[verbatim-detector] {len(new_hits)} non-baseline hit(s) found:")
            for h in sorted(new_hits, key=lambda x: x.risk):
                print(f"  {format_hit_text(h)}")
        else:
            print(f"[verbatim-detector] no new hits (total={len(all_hits)}, baseline={len(baseline_keys)})")

    return 1 if new_hits else 0


if __name__ == "__main__":
    sys.exit(main())
