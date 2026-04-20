# SCOPE: both
"""Reinvention-gate Phase B-α — Jaccard similarity over module token bags.

See: docs/adrs/ADR-029b-reinvention-phase-b-semantic.md

The module builds a JSON index of existing modules (lib/, hooks/, scripts/) and
scores agent prompts against it using Jaccard set overlap on extracted tokens
(docstrings, function/class names, shell header comments).

Stdlib only — no ML dependencies. p95 query time < 50 ms on this repo.

Usage:
    from lib.reinvention_semantic import SemanticIndex

    idx = SemanticIndex()
    idx.build_index(".")                     # scan + persist to .cognitive-os/reinvention-index.json
    matches = idx.find_similar("throttle agent tool calls per minute", top_k=3)
    for m in matches:
        print(m["path"], m["score"])
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Iterable

INDEX_SCHEMA_VERSION = 1
DEFAULT_INDEX_RELPATH = ".cognitive-os/reinvention-index.json"

# Minimal stopword list — generic CS / project words that dominate docstrings
# and carry little discriminative signal.
_STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "with",
    "by", "from", "as", "is", "are", "be", "this", "that", "it", "its",
    "at", "we", "you", "our", "your", "if", "else", "when", "then",
    "use", "used", "using", "usage", "see", "via", "also", "per",
    "file", "files", "path", "paths", "dir", "directory", "module", "modules",
    "class", "classes", "function", "functions", "method", "methods",
    "return", "returns", "arg", "args", "kwarg", "kwargs", "param", "params",
    "none", "true", "false", "null",
    "project", "cognitive", "os", "claude", "agent",  # project-specific noise
    "todo", "fixme", "note", "notes",
    "scope", "both", "both\n",
})

# Scanned subtrees (relative to project root). Ordered; duplicates are fine.
_SCAN_DIRS = ("lib", "hooks", "scripts")

# File suffixes → language key. Anything else is skipped.
_SUFFIX_TO_KIND = {
    ".py": "python",
    ".sh": "shell",
    ".bash": "shell",
}

# Directories to skip even under scanned roots.
_SKIP_DIRNAMES = frozenset({"__pycache__", "node_modules", ".git", "tests", "_archive"})

# Regex for CamelCase → camel case splitting.
_CAMEL_RE = re.compile(r"([a-z0-9])([A-Z])")
# Regex for non-alphanumeric tokenisation.
_NONALNUM_RE = re.compile(r"[^a-z0-9]+")


def _split_identifier(name: str) -> list[str]:
    """Split snake_case and CamelCase identifiers into lowercase tokens."""
    s = _CAMEL_RE.sub(r"\1_\2", name)
    return [t for t in _NONALNUM_RE.split(s.lower()) if t]


def _normalise_tokens(raw: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for tok in raw:
        tok = tok.strip().lower()
        if not tok or len(tok) < 3:
            continue
        if tok in _STOPWORDS:
            continue
        if tok.isdigit():
            continue
        if tok in seen:
            continue
        seen.add(tok)
        out.append(tok)
    return out


def _extract_python_tokens(text: str) -> tuple[list[str], str]:
    """Extract tokens from a Python source file.

    Returns (tokens, docstring_excerpt).
    """
    tokens: list[str] = []
    doc_excerpt = ""

    # Module docstring — triple-quoted string near the top of the file.
    mdoc = re.search(r'^\s*(?:#[^\n]*\n)*\s*(?:"""|\'\'\')(.*?)(?:"""|\'\'\')',
                     text, flags=re.DOTALL | re.MULTILINE)
    if mdoc:
        doc_text = mdoc.group(1)
        doc_excerpt = doc_text.strip().splitlines()[0][:200] if doc_text.strip() else ""
        for w in _NONALNUM_RE.split(doc_text.lower()):
            tokens.append(w)

    # Top-level def / class names.
    for m in re.finditer(r"^(?:async\s+)?(?:def|class)\s+([A-Za-z_][A-Za-z0-9_]*)",
                         text, flags=re.MULTILINE):
        tokens.extend(_split_identifier(m.group(1)))

    # First line of each function docstring.
    for m in re.finditer(
        r'(?:def|class)\s+[A-Za-z_][A-Za-z0-9_]*[^\n:]*:\s*\n\s*(?:"""|\'\'\')([^\n"\']+)',
        text,
    ):
        for w in _NONALNUM_RE.split(m.group(1).lower()):
            tokens.append(w)

    return _normalise_tokens(tokens), doc_excerpt


def _extract_shell_tokens(text: str) -> tuple[list[str], str]:
    """Extract tokens from a shell script: header comment block + function names."""
    tokens: list[str] = []
    doc_excerpt = ""

    # Header comments — leading `#` lines after the shebang.
    header_lines: list[str] = []
    for line in text.splitlines()[:40]:
        s = line.strip()
        if s.startswith("#!"):
            continue
        if s.startswith("#"):
            header_lines.append(s.lstrip("#").strip())
        elif s == "":
            continue
        else:
            break
    header = " ".join(header_lines)
    if header:
        doc_excerpt = header[:200]
        for w in _NONALNUM_RE.split(header.lower()):
            tokens.append(w)

    # Shell function names: `foo() {` or `function foo {`.
    for m in re.finditer(r"^\s*(?:function\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*\(\)\s*\{",
                         text, flags=re.MULTILINE):
        tokens.extend(_split_identifier(m.group(1)))

    return _normalise_tokens(tokens), doc_excerpt


def _extract_tokens(path: Path) -> tuple[list[str], str, str] | None:
    """Return (tokens, docstring_excerpt, kind) or None if the file is not scannable."""
    kind = _SUFFIX_TO_KIND.get(path.suffix)
    if not kind:
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    if not text.strip():
        return None

    # Basename tokens: the filename itself carries signal.
    basename_tokens = _split_identifier(path.stem)

    if kind == "python":
        toks, doc = _extract_python_tokens(text)
    else:
        toks, doc = _extract_shell_tokens(text)

    # Merge basename tokens (de-duped later).
    merged = _normalise_tokens(list(toks) + basename_tokens)
    return merged, doc, kind


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


class SemanticIndex:
    """In-memory + on-disk index of module token bags."""

    def __init__(self, index_path: str | Path | None = None):
        self.index_path = Path(index_path) if index_path else None
        self.items: list[dict] = []
        self.built_at: str | None = None
        self.project_root: str | None = None

    # ---------- build ----------

    def build_index(self, project_root: str | Path) -> None:
        """Scan project_root, populate self.items, and persist to disk if index_path set."""
        root = Path(project_root).resolve()
        items: list[dict] = []

        for subdir in _SCAN_DIRS:
            base = root / subdir
            if not base.is_dir():
                continue
            for path in base.rglob("*"):
                if not path.is_file():
                    continue
                if any(part in _SKIP_DIRNAMES for part in path.parts):
                    continue
                res = _extract_tokens(path)
                if res is None:
                    continue
                tokens, doc, kind = res
                if len(tokens) < 2:
                    # Too thin to be meaningful signal — skip.
                    continue
                items.append({
                    "path": str(path.relative_to(root)),
                    "kind": kind,
                    "tokens": tokens,
                    "docstring_excerpt": doc,
                })

        self.items = items
        self.project_root = str(root)
        self.built_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        if self.index_path is None:
            self.index_path = root / DEFAULT_INDEX_RELPATH
        self._persist()

    def _persist(self) -> None:
        assert self.index_path is not None
        payload = {
            "version": INDEX_SCHEMA_VERSION,
            "built_at": self.built_at,
            "project_root": self.project_root,
            "items": self.items,
        }
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.index_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, separators=(",", ":")))
        tmp.replace(self.index_path)

    # ---------- load ----------

    def load(self, index_path: str | Path | None = None) -> bool:
        """Load index from disk. Returns True on success, False if missing/invalid."""
        path = Path(index_path) if index_path else self.index_path
        if not path or not path.is_file():
            return False
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            return False
        if data.get("version") != INDEX_SCHEMA_VERSION:
            return False
        self.items = data.get("items", [])
        self.built_at = data.get("built_at")
        self.project_root = data.get("project_root")
        self.index_path = path
        return True

    # ---------- query ----------

    def find_similar(
        self,
        description: str,
        top_k: int = 3,
        min_score: float = 0.3,
    ) -> list[dict]:
        """Return up to top_k items scored ≥ min_score, sorted by score desc.

        Each result: {"path", "score", "kind", "docstring_excerpt", "matched_tokens"}.
        """
        if not description or not self.items:
            return []

        query_tokens = set(_normalise_tokens(_NONALNUM_RE.split(description.lower())))
        # Also split identifiers — "rate_limiter" in the query should split.
        extra: list[str] = []
        for tok in list(query_tokens):
            extra.extend(_split_identifier(tok))
        query_tokens.update(_normalise_tokens(extra))

        if not query_tokens:
            return []

        scored: list[dict] = []
        for item in self.items:
            item_tokens = set(item["tokens"])
            score = _jaccard(query_tokens, item_tokens)
            if score >= min_score:
                scored.append({
                    "path": item["path"],
                    "score": round(score, 4),
                    "kind": item["kind"],
                    "docstring_excerpt": item.get("docstring_excerpt", ""),
                    "matched_tokens": sorted(query_tokens & item_tokens),
                })

        scored.sort(key=lambda r: r["score"], reverse=True)
        return scored[:top_k]


# ---------- CLI entry point ----------

def _cli() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Reinvention semantic index (Phase B-α).")
    sub = parser.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="Build the index.")
    b.add_argument("--root", default=".")

    q = sub.add_parser("query", help="Query the index.")
    q.add_argument("description")
    q.add_argument("--top-k", type=int, default=3)
    q.add_argument("--min-score", type=float, default=0.3)
    q.add_argument("--root", default=".")

    args = parser.parse_args()
    idx = SemanticIndex(Path(args.root) / DEFAULT_INDEX_RELPATH)
    if args.cmd == "build":
        idx.build_index(args.root)
        print(f"indexed {len(idx.items)} items → {idx.index_path}")
        return 0
    if args.cmd == "query":
        if not idx.load():
            idx.build_index(args.root)
        matches = idx.find_similar(args.description, top_k=args.top_k, min_score=args.min_score)
        if not matches:
            print("no matches")
            return 0
        for m in matches:
            print(f"{m['score']:.3f}  {m['path']}  ({m['kind']})")
            if m["docstring_excerpt"]:
                print(f"        {m['docstring_excerpt']}")
        return 0
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_cli())
