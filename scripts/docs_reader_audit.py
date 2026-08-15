#!/usr/bin/env python3
# SCOPE: os-only
"""Reverse index for documentation: given a doc, answer "who reads it?".

Complements ``cos_doc_path_audit.py`` (which walks references -> missing paths).
This walks the other direction: doc -> every surface that could reach it.

Surfaces checked (a doc is READ if it is reached by ANY of them):

  1. explicit-path   a tracked file mentions ``docs/a/b/c.md`` verbatim
  2. relative-link   a sibling/nearby doc links it as ``./c.md`` / ``../x/c.md``
  3. dir-consumer    code/manifest/hook reads the *directory* (or a glob of it),
                     so every file inside is consumed without being named
  4. synthesis-pair  ``cos_lib/context_injector.py`` serves ``X.synthesis.md``
                     in place of ``X.md`` for configured buckets; each half is
                     a reader of the other
  5. index-entry     an INDEX.md / MOC / entrypoint lists it
  6. basename-only   some tracked file mentions the bare filename (weak; kept
                     separate so it never silently upgrades a doc to "read")

Read-only. Deterministic. Never writes, never mutates git state.

Exit codes:
  0  no unread docs in the requested scope
  1  at least one unread doc found (findings)
  2  error

Usage:
  python3 scripts/docs_reader_audit.py --path docs/foo/bar.md   # one doc
  python3 scripts/docs_reader_audit.py                          # whole scope
  python3 scripts/docs_reader_audit.py --json
  python3 scripts/docs_reader_audit.py --unread-only
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# ADRs are out of scope by mandate: they have their own lifecycle tooling.
DEFAULT_EXCLUDE_PREFIXES = ("docs/02-Decisions/adrs/",)

SKIP_DIR_PARTS = {".git", "node_modules", ".venv", "__pycache__", "vendor", "dist", "build"}

# Files whose *content* we scan for references.
READER_SUFFIXES = {
    ".md", ".py", ".sh", ".bash", ".zsh", ".yaml", ".yml", ".json", ".jsonl",
    ".go", ".toml", ".txt", ".cfg", ".ini", ".ts", ".js", ".rs", ".mk", "",
}

DOC_PATH_RE = re.compile(r"docs/[A-Za-z0-9_][A-Za-z0-9_./+-]*")
MD_LINK_RE = re.compile(r"\]\(\s*(<)?([^)\s>]+\.md)[)>#\s]")
BARE_MD_RE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.+-]*\.md")

# Buckets where context_injector.py prefers the *.synthesis.md sibling.
SYNTHESIS_MARKER = ".synthesis.md"


def sh(args: list[str]) -> str:
    return subprocess.run(
        args, cwd=ROOT, capture_output=True, text=True, check=False
    ).stdout


def tracked_files() -> list[str]:
    out = sh(["git", "ls-files", "-z"])
    return [p for p in out.split("\0") if p]


def is_scannable(rel: str) -> bool:
    parts = Path(rel).parts
    if any(p in SKIP_DIR_PARTS for p in parts):
        return False
    return Path(rel).suffix.lower() in READER_SUFFIXES


def load_corpus(paths: list[str]) -> dict[str, str]:
    corpus: dict[str, str] = {}
    for rel in paths:
        if not is_scannable(rel):
            continue
        fp = ROOT / rel
        try:
            if fp.is_symlink():
                fp = fp.resolve()
            if not fp.is_file() or fp.stat().st_size > 4_000_000:
                continue
            corpus[rel] = fp.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
    return corpus


def build_indexes(corpus: dict[str, str]) -> tuple[dict, dict, dict, dict]:
    """explicit[docpath] -> {readers}; dirs[dirpath] -> {readers};
    rellinks[(readerdir, target)] -> {readers}; basenames[name] -> {readers}"""
    explicit: dict[str, set[str]] = defaultdict(set)
    dirs: dict[str, set[str]] = defaultdict(set)
    rellinks: dict[str, set[str]] = defaultdict(set)
    basenames: dict[str, set[str]] = defaultdict(set)

    for rel, text in corpus.items():
        reader_dir = str(Path(rel).parent)
        for m in DOC_PATH_RE.finditer(text):
            token = m.group(0).rstrip(".,;:)\"'`")
            if token.endswith(".md"):
                explicit[token].add(rel)
            else:
                # directory-ish or glob reference -> whole subtree consumed
                base = token.split("*")[0].rstrip("/")
                if base:
                    dirs[base].add(rel)
        for m in MD_LINK_RE.finditer(text):
            target = m.group(2)
            if target.startswith(("http://", "https://", "docs/")):
                continue
            resolved = os.path.normpath(os.path.join(reader_dir, target))
            rellinks[resolved].add(rel)
        for m in BARE_MD_RE.finditer(text):
            basenames[m.group(0)].add(rel)
    return explicit, dirs, rellinks, basenames


def surface_of(reader: str) -> str:
    if reader.startswith("docs/00-MOCs/entrypoints/"):
        return "entrypoint"
    if reader.startswith("docs/00-MOCs/"):
        return "moc"
    if Path(reader).name == "INDEX.md":
        return "index"
    if reader.startswith("manifests/"):
        return "manifest"
    if reader.startswith("skills/"):
        return "skill"
    if reader.startswith("rules/"):
        return "rule"
    if reader.startswith(("scripts/", "lib/", "cos_lib/", "hooks/", "cmd/", "packages/")):
        return "code"
    if reader.startswith("tests/"):
        return "test"
    if reader.startswith("docs/02-Decisions/adrs/"):
        return "adr"
    if reader.startswith("docs/"):
        return "doc"
    if reader in ("CLAUDE.md", "README.md", "AGENTS.md"):
        return "root-entrypoint"
    return "other"


def readers_for(doc: str, idx, corpus) -> dict[str, list[str]]:
    explicit, dirs, rellinks, basenames = idx
    found: dict[str, set[str]] = defaultdict(set)

    for r in explicit.get(doc, ()):
        if r != doc:
            found["explicit-path"].add(r)
    for r in rellinks.get(doc, ()):
        if r != doc:
            found["relative-link"].add(r)

    p = Path(doc)
    # Only the IMMEDIATE parent counts as a glob consumer, and only when the
    # reader is machinery (code/hook/manifest/test). Walking every ancestor
    # resurrects a whole subtree from one prose mention of "docs/06-Daily" --
    # that is the cheap green of this audit, not evidence.
    parent = str(p.parent)
    for r in dirs.get(parent, ()):
        if r == doc or r.startswith(parent + "/"):
            continue
        if surface_of(r) in ("code", "manifest", "test", "skill", "rule"):
            found["dir-consumer"].add(r)
        else:
            found["dir-mention"].add(r)

    # synthesis pairing is MUTUAL, so it can never be independent evidence:
    # an orphan X.md/X.synthesis.md island would vouch for itself. Recorded
    # as a link, resolved transitively in classify_all().
    if doc.endswith(SYNTHESIS_MARKER):
        twin = doc[: -len(SYNTHESIS_MARKER)] + ".md"
    else:
        twin = doc[:-3] + SYNTHESIS_MARKER
    if twin in corpus:
        found["synthesis-pair"].add(twin)

    for r in basenames.get(p.name, ()):
        if r != doc and r not in found.get("explicit-path", ()) and r not in found.get("relative-link", ()):
            found["basename-only"].add(r)

    return {k: sorted(v) for k, v in sorted(found.items())}


STRONG = ("explicit-path", "relative-link", "dir-consumer")


def classify(readers: dict[str, list[str]]) -> str:
    """Verdict BEFORE transitive synthesis resolution."""
    if any(k in readers for k in STRONG):
        return "read"
    if "dir-mention" in readers or "basename-only" in readers:
        return "weak"
    return "unread"


def resolve_synthesis(verdicts: dict[str, str], readers_map: dict[str, dict]) -> None:
    """A *.synthesis.md page is reachable iff its twin is reachable (and vice
    versa) -- context_injector.py serves one in place of the other. Propagate
    the STRONGER verdict across each pair, once, in place."""
    rank = {"unread": 0, "weak": 1, "read": 2}
    for doc, readers in readers_map.items():
        for twin in readers.get("synthesis-pair", ()):
            if twin in verdicts and rank[verdicts[twin]] > rank[verdicts[doc]]:
                verdicts[doc] = verdicts[twin]


def main() -> int:
    ap = argparse.ArgumentParser(description="Who reads this doc?")
    ap.add_argument("--path", action="append", default=[], help="specific doc(s), repo-relative")
    ap.add_argument("--scope", default="docs/", help="prefix to audit (default docs/)")
    ap.add_argument("--include-adrs", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--unread-only", action="store_true")
    ap.add_argument("--verbose", action="store_true", help="list reader files, not just counts")
    args = ap.parse_args()

    try:
        all_tracked = tracked_files()
    except Exception as exc:  # pragma: no cover
        print(f"error: git ls-files failed: {exc}", file=sys.stderr)
        return 2
    if not all_tracked:
        print("error: no tracked files (not a git repo?)", file=sys.stderr)
        return 2

    corpus = load_corpus(all_tracked)
    idx = build_indexes(corpus)

    if args.path:
        targets = args.path
    else:
        targets = [
            f for f in all_tracked
            if f.startswith(args.scope) and f.endswith(".md")
            and (args.include_adrs or not f.startswith(DEFAULT_EXCLUDE_PREFIXES))
        ]

    readers_map = {doc: readers_for(doc, idx, corpus) for doc in sorted(targets)}
    verdicts = {doc: classify(r) for doc, r in readers_map.items()}
    resolve_synthesis(verdicts, readers_map)

    results = []
    for doc in sorted(targets):
        readers = readers_map[doc]
        verdict = verdicts[doc]
        if args.unread_only and verdict == "read":
            continue
        entry = {
            "doc": doc,
            "verdict": verdict,
            "exists": (ROOT / doc).exists(),
            "reader_counts": {k: len(v) for k, v in readers.items()},
            "surfaces": sorted({surface_of(r) for rs in readers.values() for r in rs}),
        }
        if args.verbose or args.path:
            entry["readers"] = readers
        results.append(entry)

    unread = [r for r in results if r["verdict"] == "unread"]
    weak = [r for r in results if r["verdict"] == "weak"]

    if args.json:
        print(json.dumps({
            "schema": "docs-reader-audit/v1",
            "scope": args.scope,
            "total_audited": len(targets),
            "unread": len(unread),
            "weak": len(weak),
            "read": len(targets) - len(unread) - len(weak),
            "results": results,
        }, indent=2))
    else:
        for r in results:
            print(f"{r['verdict']:7} {r['doc']}")
            if r.get("readers"):
                for kind, rs in r["readers"].items():
                    shown = rs[:8]
                    more = f" (+{len(rs)-8})" if len(rs) > 8 else ""
                    print(f"        {kind}: {', '.join(shown)}{more}")
        print(f"\naudited={len(targets)} read={len(targets)-len(unread)-len(weak)} "
              f"weak={len(weak)} unread={len(unread)}", file=sys.stderr)

    return 1 if unread else 0


if __name__ == "__main__":
    sys.exit(main())
