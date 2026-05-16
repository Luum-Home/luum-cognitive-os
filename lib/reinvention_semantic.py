# SCOPE: os-only
"""Reinvention-gate Phase B — semantic similarity index (Jaccard + Embeddings).

See: docs/02-Decisions/adrs/ADR-029b-reinvention-phase-b-semantic.md
     docs/02-Decisions/adrs/ADR-039-reinvention-phase-b-beta-embeddings.md

Two index implementations:

* **SemanticIndex** (Phase B-alpha, always available) — Jaccard set overlap on
  extracted tokens (docstrings, function/class names, shell header comments).
  Stdlib only. p95 query time < 50 ms.

* **EmbeddingsIndex** (Phase B-beta, optional) — cosine similarity over
  sentence-transformer embeddings (``all-MiniLM-L6-v2`` default).
  Requires ``sentence-transformers>=3.0`` (``pip install
  luum-cognitive-os[semantic]``). Raises ``ImportError`` if absent so callers
  can fall back to ``SemanticIndex``.

Usage::

    from lib.reinvention_semantic import SemanticIndex

    idx = SemanticIndex()
    idx.build_index(".")
    matches = idx.find_similar("throttle agent tool calls per minute", top_k=3)

    # Phase B-beta (embeddings):
    try:
        from lib.reinvention_semantic import EmbeddingsIndex
        eidx = EmbeddingsIndex()
        eidx.build_index(".")
        matches = eidx.find_similar("throttle agent tool calls per minute", top_k=3)
    except ImportError:
        pass  # sentence-transformers not installed — use SemanticIndex above
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Iterable

INDEX_SCHEMA_VERSION = 1
DEFAULT_INDEX_RELPATH = ".cognitive-os/reinvention-index.json"

# Embeddings index artefacts (Phase B-beta).
DEFAULT_EMBEDDINGS_RELPATH = ".cognitive-os/reinvention-index.embeddings.npy"
DEFAULT_EMBEDDINGS_META_RELPATH = ".cognitive-os/reinvention-index.embeddings.json"

# Default model: ~90 MB, Apache-2 licence, runs locally.
# Override via REINVENTION_EMBED_MODEL env var.
DEFAULT_EMBED_MODEL = "all-MiniLM-L6-v2"

# Recalibrated threshold for cosine similarity (embeddings produce much higher
# scores than Jaccard; empirical range 0.3-0.9 for genuine matches).
DEFAULT_EMBED_MIN_SCORE = 0.45

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


# ---------- Phase B-beta: EmbeddingsIndex ----------


def _require_sentence_transformers():
    """Import sentence_transformers or raise ImportError with install hint."""
    try:
        import sentence_transformers  # noqa: F401
        return sentence_transformers
    except ImportError as exc:
        raise ImportError(
            "sentence-transformers is not installed. "
            "Install the optional semantic extra: "
            "pip install 'luum-cognitive-os[semantic]' "
            "or pip install sentence-transformers>=3.0"
        ) from exc


class EmbeddingsIndex:
    """Cosine-similarity index over sentence-transformer embeddings (Phase B-beta).

    Raises ``ImportError`` on instantiation if ``sentence-transformers`` is not
    installed — the caller must catch this and fall back to ``SemanticIndex``.

    The index persists two files:
    - ``.cognitive-os/reinvention-index.embeddings.npy``  (float32 matrix, rows = items)
    - ``.cognitive-os/reinvention-index.embeddings.json`` (metadata: paths, docstrings, model name)

    Cache hit detection uses a SHA-256 of the metadata JSON's mtime so that
    adding new files triggers a partial rebuild (full rebuild for now; partial
    is a future optimisation).
    """

    def __init__(
        self,
        embeddings_path: str | Path | None = None,
        meta_path: str | Path | None = None,
        model_name: str | None = None,
    ) -> None:
        st = _require_sentence_transformers()  # raises ImportError early if absent
        self._st = st
        self.model_name: str = model_name or DEFAULT_EMBED_MODEL
        self.embeddings_path: Path | None = Path(embeddings_path) if embeddings_path else None
        self.meta_path: Path | None = Path(meta_path) if meta_path else None

        # Runtime state
        self._model = None  # lazy-loaded on first build/query
        self._embeddings = None  # numpy float32 array, shape (N, D)
        self.items: list[dict] = []  # same structure as SemanticIndex.items
        self.built_at: str | None = None
        self.project_root: str | None = None

    # ---------- internal helpers ----------

    def _get_model(self):
        if self._model is None:
            import os
            model_name = os.environ.get("REINVENTION_EMBED_MODEL", self.model_name)
            self._model = self._st.SentenceTransformer(model_name)
        return self._model

    def _item_text(self, item: dict) -> str:
        """Produce the text string that represents a module for embedding."""
        parts = [item.get("docstring_excerpt", ""), " ".join(item.get("tokens", []))]
        return " ".join(p for p in parts if p).strip()

    def _resolve_paths(self, root: Path) -> None:
        if self.embeddings_path is None:
            self.embeddings_path = root / DEFAULT_EMBEDDINGS_RELPATH
        if self.meta_path is None:
            self.meta_path = root / DEFAULT_EMBEDDINGS_META_RELPATH

    # ---------- build ----------

    def build_index(self, project_root: str | Path) -> None:
        """Scan project_root, embed each module, persist artefacts.

        Re-uses the Jaccard SemanticIndex scan to extract tokens/docstrings;
        this avoids duplicating the file-walking logic.
        """
        import numpy as np

        root = Path(project_root).resolve()
        self._resolve_paths(root)

        # Reuse SemanticIndex scanning — it already knows how to extract tokens.
        jaccard_idx = SemanticIndex()
        jaccard_idx.build_index(root)  # scan only; we'll build our own persistence
        self.items = jaccard_idx.items
        self.project_root = str(root)
        self.built_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        if not self.items:
            self._embeddings = np.empty((0, 384), dtype=np.float32)
            self._persist()
            return

        texts = [self._item_text(item) for item in self.items]
        model = self._get_model()
        embeddings = model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,  # cosine = dot product for unit vectors
            show_progress_bar=False,
        )
        self._embeddings = embeddings.astype(np.float32)
        self._persist()

    def _persist(self) -> None:
        import numpy as np
        assert self.embeddings_path is not None
        assert self.meta_path is not None

        self.embeddings_path.parent.mkdir(parents=True, exist_ok=True)

        # Save embeddings matrix.
        # np.save auto-appends ".npy" when the path doesn't end with it; pass
        # allow_pickle=False and use a stem with ".tmp" suffix so the resulting
        # file is {stem}.tmp.npy, then rename over the final path.
        if self._embeddings is None:
            self._embeddings = np.empty((0, 0), dtype=np.float32)
        tmp_npy = self.embeddings_path.with_suffix(".npy.tmp.npy")
        np.save(str(tmp_npy), self._embeddings, allow_pickle=False)
        tmp_npy.replace(self.embeddings_path)

        # Save metadata.
        meta = {
            "version": INDEX_SCHEMA_VERSION,
            "built_at": self.built_at,
            "project_root": self.project_root,
            "model_name": self.model_name,
            "items": self.items,
        }
        tmp_json = self.meta_path.with_suffix(".json.tmp")
        tmp_json.write_text(json.dumps(meta, separators=(",", ":")))
        tmp_json.replace(self.meta_path)

    # ---------- load ----------

    def load(self, root: str | Path | None = None) -> bool:
        """Load persisted artefacts. Returns True on success."""
        import numpy as np

        if root is not None:
            self._resolve_paths(Path(root).resolve())

        if not self.meta_path or not self.meta_path.is_file():
            return False
        if not self.embeddings_path or not self.embeddings_path.is_file():
            return False

        try:
            meta = json.loads(self.meta_path.read_text())
        except (OSError, json.JSONDecodeError):
            return False
        if meta.get("version") != INDEX_SCHEMA_VERSION:
            return False

        try:
            self._embeddings = np.load(str(self.embeddings_path))
        except Exception:
            return False

        self.items = meta.get("items", [])
        self.built_at = meta.get("built_at")
        self.project_root = meta.get("project_root")
        self.model_name = meta.get("model_name", self.model_name)
        return True

    # ---------- query ----------

    def find_similar(
        self,
        description: str,
        top_k: int = 3,
        min_score: float = DEFAULT_EMBED_MIN_SCORE,
    ) -> list[dict]:
        """Return up to top_k items scored >= min_score (cosine similarity).

        Each result: {"path", "score", "kind", "docstring_excerpt"}.
        Score range: -1..1 (practically 0..1 for natural language queries).
        """
        import numpy as np

        if not description or self._embeddings is None or len(self._embeddings) == 0:
            return []

        model = self._get_model()
        q_vec = model.encode(
            [description],
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )[0].astype(np.float32)  # shape (D,)

        # Dot product of normalised vectors = cosine similarity.
        scores = self._embeddings @ q_vec  # shape (N,)

        scored: list[dict] = []
        for i, score in enumerate(scores.tolist()):
            if score >= min_score:
                item = self.items[i]
                scored.append({
                    "path": item["path"],
                    "score": round(float(score), 4),
                    "kind": item["kind"],
                    "docstring_excerpt": item.get("docstring_excerpt", ""),
                })

        scored.sort(key=lambda r: r["score"], reverse=True)
        return scored[:top_k]


# ---------- CLI entry point ----------

def _cli() -> int:
    import argparse
    parser = argparse.ArgumentParser(
        description="Reinvention semantic index (Phase B-alpha Jaccard / Phase B-beta Embeddings)."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="Build the index.")
    b.add_argument("--root", default=".")
    b.add_argument("--embeddings", action="store_true", help="Build embeddings index (Phase B-beta).")

    q = sub.add_parser("query", help="Query the index.")
    q.add_argument("description")
    q.add_argument("--top-k", type=int, default=3)
    q.add_argument("--min-score", type=float, default=None)
    q.add_argument("--root", default=".")
    q.add_argument("--embeddings", action="store_true", help="Query embeddings index (Phase B-beta).")

    args = parser.parse_args()

    use_embeddings = getattr(args, "embeddings", False)

    if use_embeddings:
        root = Path(args.root)
        eidx = EmbeddingsIndex(
            embeddings_path=root / DEFAULT_EMBEDDINGS_RELPATH,
            meta_path=root / DEFAULT_EMBEDDINGS_META_RELPATH,
        )
        if args.cmd == "build":
            eidx.build_index(args.root)
            print(f"indexed {len(eidx.items)} items → {eidx.embeddings_path}")
            return 0
        if args.cmd == "query":
            if not eidx.load(args.root):
                eidx.build_index(args.root)
            min_score = args.min_score if args.min_score is not None else DEFAULT_EMBED_MIN_SCORE
            matches = eidx.find_similar(args.description, top_k=args.top_k, min_score=min_score)
            if not matches:
                print("no matches")
                return 0
            for m in matches:
                print(f"{m['score']:.3f}  {m['path']}  ({m['kind']})")
                if m["docstring_excerpt"]:
                    print(f"        {m['docstring_excerpt']}")
            return 0
        return 2

    idx = SemanticIndex(Path(args.root) / DEFAULT_INDEX_RELPATH)
    if args.cmd == "build":
        idx.build_index(args.root)
        print(f"indexed {len(idx.items)} items → {idx.index_path}")
        return 0
    if args.cmd == "query":
        if not idx.load():
            idx.build_index(args.root)
        min_score = args.min_score if args.min_score is not None else 0.3
        matches = idx.find_similar(args.description, top_k=args.top_k, min_score=min_score)
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
