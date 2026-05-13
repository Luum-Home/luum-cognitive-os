# SCOPE: both
"""ADR-040 — Query-Tailored Context Injection helper.

Given a free-text task description, searches the self-knowledge base, ADR
documents, and recent debt-register entries for the top-3 semantically
relevant snippets and formats them as a concise additionalContext block
capped at ~1 000 tokens (~4 000 chars).

Search strategy (preference order):
1. EmbeddingsIndex (cosine similarity, sentence-transformers) — best recall.
2. SemanticIndex  (Jaccard over token bags, stdlib-only)     — reliable fallback.

Both indices are pre-built by ADR-029b/039 and cached under
.cognitive-os/reinvention-index.{json,embeddings.*}.

ADR lookup: scans docs/02-Decisions/adrs/*.md filenames + first-paragraph excerpts using
the Jaccard index for lightweight matching (ADRs are not in the code index).

Debt register: reads last 50 entries from .cognitive-os/debt-register.jsonl
and applies Jaccard matching.

Cache: results are memoised by SHA-256(task_text) in
.cognitive-os/context-injector-cache.json (TTL = 1 hour or until index mtime
changes).

Usage (standalone, for manual testing)::

    uv run python3 lib/context_injector.py "refactor rate limiter"

Returns block printed to stdout.

Usage (programmatic)::

    from lib.context_injector import build_context
    ctx = build_context("refactor rate limiter", project_root=".")
    # ctx is a str ready to append to additionalContext, or "" on failure.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any

# Absolute hard cap on injected chars (~4 chars/token × 1000 tokens).
MAX_CONTEXT_CHARS = 4_000
# How many top matches to include.
TOP_K = 3
# Cache TTL in seconds (1 hour).
CACHE_TTL_SECS = 3600

# Jaccard minimum score thresholds per source.
# Code index items have large token bags (many stopwords filtered), so genuine
# two-word matches like "rate limiter" produce scores in the 0.05-0.09 range.
# Tuned empirically against the luum-agent-os corpus.
_CODE_MIN_SCORE = 0.05
_ADR_MIN_SCORE = 0.04
_DEBT_MIN_SCORE = 0.04

# ─── Token helpers (mirrors reinvention_semantic._normalise_tokens) ──────────

_CAMEL_RE = re.compile(r"([a-z0-9])([A-Z])")
_NONALNUM_RE = re.compile(r"[^a-z0-9]+")
_STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "with",
    "by", "from", "as", "is", "are", "be", "this", "that", "it", "its",
    "at", "we", "you", "our", "your", "if", "else", "when", "then",
    "use", "used", "using", "usage", "see", "via", "also", "per",
    "file", "files", "path", "paths", "dir", "directory", "module",
    "class", "function", "method", "return", "arg", "param",
    "none", "true", "false", "null",
    "project", "cognitive", "os", "claude", "agent",
    "todo", "fixme", "note", "notes", "scope", "both",
})


def _tokenise(text: str) -> set[str]:
    """Split text into a normalised token set for Jaccard similarity."""
    s = _CAMEL_RE.sub(r"\1_\2", text)
    raw = _NONALNUM_RE.split(s.lower())
    tokens: set[str] = set()
    for t in raw:
        if len(t) < 2 or t in _STOPWORDS:
            continue
        tokens.add(t)
        # Also split snake_case identifiers.
        for part in t.split("_"):
            if len(part) >= 2 and part not in _STOPWORDS:
                tokens.add(part)
    return tokens


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


# ─── Cache helpers ───────────────────────────────────────────────────────────

def _cache_path(project_root: Path) -> Path:
    return project_root / ".cognitive-os" / "context-injector-cache.json"


def _load_cache(project_root: Path) -> dict[str, Any]:
    cp = _cache_path(project_root)
    if not cp.exists():
        return {}
    try:
        return json.loads(cp.read_text())
    except Exception:
        return {}


def _save_cache(project_root: Path, cache: dict[str, Any]) -> None:
    cp = _cache_path(project_root)
    cp.parent.mkdir(parents=True, exist_ok=True)
    tmp = cp.with_suffix(".json.tmp")
    try:
        tmp.write_text(json.dumps(cache, separators=(",", ":")))
        tmp.replace(cp)
    except Exception:
        pass


def _task_hash(task: str) -> str:
    return hashlib.sha256(task.encode()).hexdigest()[:16]


def _index_mtime(project_root: Path) -> float:
    """Return mtime of the code index file, or 0 if absent."""
    p = project_root / ".cognitive-os" / "reinvention-index.json"
    try:
        return p.stat().st_mtime
    except OSError:
        return 0.0


# ─── Code index search ───────────────────────────────────────────────────────

def _search_code_index(
    query_tokens: set[str],
    project_root: Path,
    top_k: int = TOP_K,
) -> list[dict]:
    """Search the Jaccard-based reinvention index for relevant code modules."""
    index_path = project_root / ".cognitive-os" / "reinvention-index.json"
    if not index_path.exists():
        return []
    try:
        payload = json.loads(index_path.read_text())
        items = payload.get("items", [])
    except Exception:
        return []

    scored = []
    for item in items:
        item_tokens = set(item.get("tokens", []))
        score = _jaccard(query_tokens, item_tokens)
        if score >= _CODE_MIN_SCORE:
            scored.append({
                "source": "code",
                "path": item.get("path", ""),
                "score": round(score, 4),
                "excerpt": item.get("docstring_excerpt", ""),
            })
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


def _search_code_embeddings(
    task: str,
    project_root: Path,
    top_k: int = TOP_K,
) -> list[dict] | None:
    """Try EmbeddingsIndex search. Returns None if unavailable or on error."""
    try:
        import sys
        sys.path.insert(0, str(project_root))
        from lib.reinvention_semantic import EmbeddingsIndex  # type: ignore[import]
        idx = EmbeddingsIndex(
            embeddings_path=project_root / ".cognitive-os" / "reinvention-index.embeddings.npy",
            meta_path=project_root / ".cognitive-os" / "reinvention-index.embeddings.json",
        )
        idx.load_index()
        results = idx.find_similar(task, top_k=top_k)
        return [
            {
                "source": "code_embed",
                "path": r["path"],
                "score": r["score"],
                "excerpt": r.get("docstring_excerpt", ""),
            }
            for r in results
        ]
    except Exception:
        return None


# ─── ADR search ──────────────────────────────────────────────────────────────

def _search_adrs(
    query_tokens: set[str],
    project_root: Path,
    top_k: int = TOP_K,
) -> list[dict]:
    """Search ADR filenames and first-paragraph content via Jaccard."""
    adrs_dir = project_root / "docs" / "02-Decisions" / "adrs"
    if not adrs_dir.is_dir():
        return []

    scored = []
    for md_file in adrs_dir.glob("ADR-*.md"):
        # Tokenise from filename stem + first 600 chars of file.
        content = ""
        try:
            content = md_file.read_text(errors="ignore")[:600]
        except OSError:
            pass
        adr_tokens = _tokenise(md_file.stem + " " + content)
        score = _jaccard(query_tokens, adr_tokens)
        if score >= _ADR_MIN_SCORE:
            # Extract first meaningful line (the title) after the heading.
            title_match = re.search(r"^# (.+)$", content, re.MULTILINE)
            title = title_match.group(1) if title_match else md_file.stem
            scored.append({
                "source": "adr",
                "path": str(md_file.relative_to(project_root)),
                "score": round(score, 4),
                "excerpt": title,
            })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


# ─── Debt register search ────────────────────────────────────────────────────

def _search_debt(
    query_tokens: set[str],
    project_root: Path,
    top_k: int = TOP_K,
) -> list[dict]:
    """Search last 50 entries in debt-register.jsonl via Jaccard."""
    debt_file = project_root / ".cognitive-os" / "debt-register.jsonl"
    if not debt_file.exists():
        return []

    entries: list[dict] = []
    try:
        lines = debt_file.read_text(errors="ignore").splitlines()
        for line in lines[-50:]:
            try:
                entries.append(json.loads(line))
            except Exception:
                pass
    except OSError:
        return []

    scored = []
    for entry in entries:
        text = " ".join(str(v) for v in entry.values() if isinstance(v, str))
        entry_tokens = _tokenise(text)
        score = _jaccard(query_tokens, entry_tokens)
        if score >= _DEBT_MIN_SCORE:
            scored.append({
                "source": "debt",
                "path": entry.get("file", "debt-register"),
                "score": round(score, 4),
                "excerpt": entry.get("description", text[:120]),
            })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


# ─── Context formatter ───────────────────────────────────────────────────────

def _format_context(matches: list[dict]) -> str:
    """Format top matches into a concise additionalContext block."""
    if not matches:
        return ""

    lines = ["## Relevant context (ADR-040 semantic match)"]
    for m in matches:
        source = m["source"].upper()
        path = m["path"]
        score = m["score"]
        excerpt = m.get("excerpt", "")
        # Truncate long excerpts.
        if len(excerpt) > 200:
            excerpt = excerpt[:197] + "..."
        if excerpt:
            lines.append(f"- [{source}] `{path}` (score={score}): {excerpt}")
        else:
            lines.append(f"- [{source}] `{path}` (score={score})")

    return "\n".join(lines)


# ─── Metrics logger ──────────────────────────────────────────────────────────

def _log_metrics(
    project_root: Path,
    task_hash: str,
    match_count: int,
    top_score: float,
    fallback_used: bool,
    cache_hit: bool,
    latency_ms: float,
) -> None:
    metrics_dir = project_root / ".cognitive-os" / "metrics"
    metrics_file = metrics_dir / "query-tailored-inject.jsonl"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    record = {
        "timestamp": ts,
        "task_hash": task_hash,
        "match_count": match_count,
        "top_score": round(top_score, 4),
        "fallback_used": fallback_used,
        "cache_hit": cache_hit,
        "latency_ms": round(latency_ms, 1),
    }
    try:
        with metrics_file.open("a") as f:
            f.write(json.dumps(record) + "\n")
    except OSError:
        pass


# ─── Public API ──────────────────────────────────────────────────────────────

def build_context(
    task: str,
    project_root: str | Path = ".",
    top_k: int = TOP_K,
    use_cache: bool = True,
) -> str:
    """Return a formatted additionalContext block for *task*, or "" on failure.

    Parameters
    ----------
    task:
        Free-text description of the agent's task (first paragraph or 500 chars).
    project_root:
        Absolute or relative path to the repository root.
    top_k:
        Maximum number of matches to surface.
    use_cache:
        Whether to read/write the on-disk cache.

    Returns
    -------
    str
        Formatted context block ready to append to additionalContext, capped at
        MAX_CONTEXT_CHARS.  Empty string on any failure or when no matches found.
    """
    t0 = time.monotonic()
    root = Path(project_root).resolve()
    task = task.strip()

    if not task:
        return ""

    # ── Cache check ──────────────────────────────────────────────────────────
    h = _task_hash(task)
    fallback_used = False
    cache_hit = False

    if use_cache:
        cache = _load_cache(root)
        entry = cache.get(h)
        if entry:
            stored_mtime = entry.get("index_mtime", 0.0)
            stored_ts = entry.get("ts", 0.0)
            current_mtime = _index_mtime(root)
            age = time.time() - stored_ts
            if age < CACHE_TTL_SECS and stored_mtime == current_mtime:
                ctx = entry.get("context", "")
                latency_ms = (time.monotonic() - t0) * 1000
                _log_metrics(root, h, 0, 0.0, False, True, latency_ms)
                return ctx
    else:
        cache = {}

    # ── Search ───────────────────────────────────────────────────────────────
    query_tokens = _tokenise(task)
    all_matches: list[dict] = []

    # 1. Try embeddings first.
    embed_results = _search_code_embeddings(task, root, top_k=top_k)
    if embed_results is not None:
        all_matches.extend(embed_results)
    else:
        # 2. Jaccard fallback for code index.
        fallback_used = True
        all_matches.extend(_search_code_index(query_tokens, root, top_k=top_k))

    # 3. ADR search (always Jaccard — ADRs not in embeddings corpus).
    all_matches.extend(_search_adrs(query_tokens, root, top_k=top_k))

    # 4. Debt register.
    all_matches.extend(_search_debt(query_tokens, root, top_k=top_k))

    # De-duplicate by path, keep highest score.
    seen: dict[str, dict] = {}
    for m in all_matches:
        key = m["path"]
        if key not in seen or m["score"] > seen[key]["score"]:
            seen[key] = m
    deduped = sorted(seen.values(), key=lambda x: x["score"], reverse=True)[:top_k]

    ctx = _format_context(deduped)

    # Enforce hard cap.
    if len(ctx) > MAX_CONTEXT_CHARS:
        ctx = ctx[: MAX_CONTEXT_CHARS - 30] + "\n[truncated by ADR-040]"

    # ── Persist cache ────────────────────────────────────────────────────────
    if use_cache:
        cache[h] = {
            "context": ctx,
            "ts": time.time(),
            "index_mtime": _index_mtime(root),
        }
        _save_cache(root, cache)

    # ── Metrics ──────────────────────────────────────────────────────────────
    top_score = deduped[0]["score"] if deduped else 0.0
    latency_ms = (time.monotonic() - t0) * 1000
    _log_metrics(root, h, len(deduped), top_score, fallback_used, cache_hit, latency_ms)

    return ctx


# ─── CLI entry point ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: uv run python3 lib/context_injector.py \"<task description>\"", file=sys.stderr)
        sys.exit(1)

    task_arg = " ".join(sys.argv[1:])
    # Auto-detect project root from this file's location.
    _script_root = Path(__file__).resolve().parent.parent
    result = build_context(task_arg, project_root=_script_root)
    if result:
        print(result)
    else:
        print("(no relevant context found)", file=sys.stderr)
        sys.exit(0)
