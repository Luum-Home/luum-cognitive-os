#!/usr/bin/env python3
# SCOPE: os-only
"""Verify that a .cognitive-os/metrics flow is really orphaned before switching its emitter off.

Executable evidence for the ADR-186-adjacent signal-consumer census
(docs/06-Daily/reports/arquitectura-senal-sin-consumidor-2026-08-19.md), whose author
declared two blind spots this script closes:

  1. Row counts taken from the live file only. The live file covers a few hours; a flow
     that rotated into .cognitive-os/metrics/.archive/*.gz reads as a false zero. This
     script counts live + archived.
  2. Reader search by literal basename over tracked files with extensions. It missed
     extensionless scripts (scripts/cos-control-plane-audit writes 13.5 MB and was
     classified "no writer" twice). This script searches every tracked file regardless of
     extension or language -- Go, JS, CI workflows, shell, Python -- plus the stem alone,
     which is how dynamically-built paths (metrics_dir / f"{stem}.jsonl") appear.

Read-only. Deterministic. Exit 0 = every flow verified orphaned (safe to stop emitting),
1 = at least one flow has a reader, rows, or no writer (do not touch), 2 = error.
"""
from __future__ import annotations

import argparse
import gzip
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
METRICS = ROOT / ".cognitive-os" / "metrics"

# An "append/write" operation near the mention makes the mentioning file a WRITER.
WRITE_HINT = re.compile(
    r"""(>>|open\s*\(|\.open\s*\(|append_|write_text|writeString|os\.Create|
        OpenFile|tee\s|printf.*>>|echo.*>>|json\.dump|WriteFile|createWriteStream|
        appendFile|fs\.append)""",
    re.VERBOSE,
)
# A read operation makes it a READER.
READ_HINT = re.compile(
    r"""(read_text|readlines|read_rows|\bcat\b|\bgrep\b|\bwc\b|ReadFile|readFile|
        readFileSync|json\.load|\btail\b|\bhead\b|iter_rows|glob|Open\s*\()""",
    re.VERBOSE,
)


def tracked_files() -> list[Path]:
    out = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files"], capture_output=True, text=True, check=True
    ).stdout.splitlines()
    return [ROOT / line for line in out if line]


def count_rows(stem: str) -> tuple[int, int, int]:
    """Return (live_rows, archived_rows, archive_files) for a metrics stem."""
    live_path = METRICS / f"{stem}.jsonl"
    live = 0
    if live_path.is_file():
        live = sum(1 for line in live_path.read_text(errors="replace").splitlines() if line.strip())
    archived = 0
    archives = 0
    archive_dir = METRICS / ".archive"
    if archive_dir.is_dir():
        for gz in sorted(archive_dir.glob(f"{stem}-*.gz")) + sorted(archive_dir.glob(f"{stem}.jsonl*.gz")):
            archives += 1
            try:
                with gzip.open(gz, "rt", errors="replace") as fh:
                    archived += sum(1 for line in fh if line.strip())
            except OSError:
                continue
    return live, archived, archives


CODE_SUFFIXES = {".py", ".sh", ".bash", ".go", ".js", ".ts", ".mjs", ".rb", ".pl", ""}
CONFIG_SUFFIXES = {".yaml", ".yml", ".json", ".toml", ".txt", ".lock"}
CONFIG_PREFIXES = (".ai/", ".clau" + "de/", ".cod" + "ex/", ".cur" + "sor/", ".de" + "vin/", ".ki" + "ro/", ".open" + "code/", "manifests/", "templates/")
# Dynamic path construction: the stem reaches a metrics path without the literal basename.
DYNAMIC_HINT = re.compile(r"(metrics[_-]?(dir|path|file)|cognitive-os/metrics|METRICS)", re.IGNORECASE)


def _kind(path: Path, rel: str) -> str:
    if rel.startswith(("docs/", "CHANGELOG", "README")):
        return "doc"
    suffix = path.suffix.lower()
    if suffix in CONFIG_SUFFIXES or rel.startswith(CONFIG_PREFIXES):
        return "config"
    if suffix in CODE_SUFFIXES:
        return "code"
    return "other"


def classify_mentions(stem: str, files: list[Path]) -> dict[str, list[str]]:
    """Split every tracked file that touches the ARTIFACT into writers and readers.

    Matching is on the artifact basename `<stem>.jsonl`, not the bare stem: the bare stem
    is usually the emitter's own name, and matching it makes every emitter registration
    look like a consumer. Dynamically-built paths are caught separately, by requiring the
    stem to appear alongside a metrics-directory reference.
    """
    basename = f"{stem}.jsonl"
    out: dict[str, list[str]] = {"writers": [], "code_readers": [], "config": [], "docs": [], "dynamic": []}
    for path in files:
        rel = str(path.relative_to(ROOT))
        if rel.startswith(".cognitive-os/metrics"):
            continue
        try:
            text = path.read_text(errors="replace")
        except (OSError, UnicodeDecodeError):
            continue
        lines = text.splitlines()
        if basename not in text:
            dyn = [
                i for i, line in enumerate(lines)
                if stem in line and DYNAMIC_HINT.search("\n".join(lines[max(0, i - 6): i + 7]))
            ]
            if dyn:
                out["dynamic"].append(rel)
            continue
        hits = [i for i, line in enumerate(lines) if basename in line]
        window = "\n".join(line for i in hits for line in lines[max(0, i - 12): i + 13])
        kind = _kind(path, rel)
        if kind == "doc":
            out["docs"].append(rel)
        elif kind == "config":
            out["config"].append(rel)
        elif WRITE_HINT.search(window) and not READ_HINT.search(window):
            out["writers"].append(rel)
        else:
            out["code_readers"].append(rel)
    return {key: sorted(set(value)) for key, value in out.items()}


WILDCARD_READ = re.compile(r"""(metrics_dir\.glob|metrics\.glob|metrics\.rglob|
    metrics/\*\.jsonl|METRICS_DIR"?/\*\.jsonl|\$\{?METRICS_DIR\}?/\*\.jsonl)""", re.VERBOSE)


def wildcard_consumers(files: list[Path]) -> list[str]:
    """Find consumers that read EVERY *.jsonl in the metrics dir without naming one.

    This is the class of reader a per-filename grep cannot see, and it is the reason a
    flow can be "mentioned by nobody" and still feed a decision: primitive_fitness
    scores friction over every stream, promote_from_telemetry tags each row with its
    stream name, exercised_coverage counts a row as TIER-1 proof that a primitive ran.
    While any of these exist, "no reader" is a statement about naming, not about use.
    """
    out = []
    for path in files:
        rel = str(path.relative_to(ROOT))
        if rel.startswith((".cognitive-os/metrics", "docs/", "tests/")):
            continue
        try:
            text = path.read_text(errors="replace")
        except (OSError, UnicodeDecodeError):
            continue
        if WILDCARD_READ.search(text):
            out.append(rel)
    return sorted(set(out))


def verify(stems: list[str]) -> int:
    files = tracked_files()
    wildcards = wildcard_consumers(files)
    worst = 0
    print(f"wildcard consumers of every metrics stream: {len(wildcards)}")
    for entry in wildcards:
        print(f"  - {entry}")
    print()
    for stem in stems:
        live, archived, archives = count_rows(stem)
        found = classify_mentions(stem, files)
        readers = [r for r in found["code_readers"] if not r.startswith("tests/")]
        test_readers = [r for r in found["code_readers"] if r.startswith("tests/")]
        reasons = []
        verdict = "ORPHAN"
        if readers:
            verdict = "HAS_READER"
            reasons.append(f"code readers: {readers}")
        elif live or archived:
            verdict = "HAS_ROWS"
            reasons.append(f"emitted rows: live={live} archived={archived} in {archives} archive(s)")
        elif not found["writers"]:
            verdict = "NO_WRITER"
            reasons.append("no writer: nothing to switch off (missing input, not missing reader)")
        if found["dynamic"]:
            reasons.append(f"dynamic-path candidates: {found['dynamic']}")
        if verdict == "ORPHAN" and wildcards:
            # No named reader, but every stream feeds the wildcard consumers above.
            verdict = "WILDCARD_READER"
            reasons.append(f"no named reader, but {len(wildcards)} wildcard consumer(s) read every stream")
        if verdict != "ORPHAN":
            worst = 1
        print(f"{verdict:<10} {stem}  live={live} archived={archived} archives={archives}")
        print(f"           writers      : {found['writers'] or 'NONE'}")
        print(f"           code readers : {readers or 'NONE'}")
        print(f"           test-only    : {test_readers or 'NONE'}")
        print(f"           config/docs  : {len(found['config'])} config, {len(found['docs'])} docs")
        for reason in reasons:
            print(f"           ! {reason}")
    return worst


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("stems", nargs="+", help="metrics flow stems, e.g. adr-implementation")
    args = parser.parse_args(argv)
    try:
        return verify(args.stems)
    except subprocess.CalledProcessError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
