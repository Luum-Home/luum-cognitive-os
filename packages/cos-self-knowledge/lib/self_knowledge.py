# SCOPE: both
"""
self_knowledge.py — Query interface for the COS self-knowledge index.

The index lives at .cognitive-os/self-knowledge/ and is built by
scripts/cos_build_self_knowledge.py.

Public API:
    query(term)          -> List[dict]  — substring search across all artifacts
    get_module(path)     -> dict | None — fast api-surface lookup
    get_importers(module)-> List[str]   — reverse dep-graph query
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Index location resolution
# ---------------------------------------------------------------------------

def _find_project_dir() -> Path | None:
    """Walk up from this file to find the project root."""
    candidate = Path(__file__).resolve()
    for _ in range(8):
        candidate = candidate.parent
        if (candidate / "cognitive-os.yaml").exists() or (candidate / ".claude").exists():
            return candidate
    return None


def _index_dir(project_dir: Path | None = None) -> Path:
    if project_dir is None:
        project_dir = _find_project_dir()
    if project_dir is None:
        raise FileNotFoundError("Cannot find project root. Pass project_dir explicitly.")
    return project_dir / ".cognitive-os" / "self-knowledge"


# ---------------------------------------------------------------------------
# Lazy cache
# ---------------------------------------------------------------------------

_CACHE: dict[str, Any] = {}


def _load(name: str, project_dir: Path | None = None) -> Any:
    cache_key = str(project_dir) + ":" + name
    if cache_key not in _CACHE:
        idx = _index_dir(project_dir)
        path = idx / name
        if not path.exists():
            _CACHE[cache_key] = None
        elif name.endswith(".json"):
            _CACHE[cache_key] = json.loads(path.read_text(encoding="utf-8"))
        else:
            _CACHE[cache_key] = path.read_text(encoding="utf-8")
    return _CACHE[cache_key]


def _invalidate_cache() -> None:
    """Clear the in-memory cache (useful in tests)."""
    _CACHE.clear()


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def _score_text(term: str, text: str) -> int:
    """Return hit count for term in text (case-insensitive)."""
    return len(re.findall(re.escape(term), text, re.IGNORECASE))


def _normalize_term(term: str) -> str:
    """Normalise term: lowercase, replace spaces/hyphens with underscores for path matching."""
    return term.lower().replace(" ", "_").replace("-", "_")


def _score_entry(term: str, source: str, key: str, value: Any) -> int:
    """Compute a relevance score for a single index entry."""
    score = 0
    tl = term.lower()
    tl_norm = _normalize_term(term)  # for path / identifier matching

    # Path/key match is highest value — check both raw term and normalised form
    key_lower = key.lower()
    if tl in key_lower or tl_norm in key_lower:
        score += 3

    if source == "api-surface":
        # class names
        for cls in value.get("classes", []):
            cls_l = cls.lower()
            if tl in cls_l or tl_norm in cls_l:
                score += 2
        # function names and docs
        for fn in value.get("functions", []):
            fn_name_l = fn.get("name", "").lower()
            if tl in fn_name_l or tl_norm in fn_name_l:
                score += 2
            if tl in fn.get("doc_first_line", "").lower():
                score += 1
            if tl in fn.get("signature", "").lower():
                score += 1
    elif source == "dep-graph":
        for dep in value:
            dep_l = dep.lower()
            if tl in dep_l or tl_norm in dep_l:
                score += 1
    elif source in ("glossary", "codebase-summary"):
        # value is a text block; key is the section heading
        key_l = key.lower()
        if tl in key_l or tl_norm in key_l:
            score += 2
        if isinstance(value, str) and (tl in value.lower() or tl_norm in value.lower()):
            score += 1

    return score


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def query(term: str, project_dir: Path | None = None) -> list[dict[str, Any]]:
    """
    Substring search across all four self-knowledge artifacts.

    Returns up to 10 results sorted by relevance score (descending).
    Each result has keys: source, key, snippet, score.
    """
    if not term:
        return []

    results: list[dict[str, Any]] = []

    # --- api-surface.json ---
    surface = _load("api-surface.json", project_dir)
    if surface:
        for mod_path, info in surface.items():
            score = _score_entry(term, "api-surface", mod_path, info)
            if score > 0:
                # Build a short snippet
                fn_names = [f["name"] for f in info.get("functions", [])]
                snippet_parts = []
                if info.get("classes"):
                    snippet_parts.append("classes: " + ", ".join(info["classes"][:3]))
                if fn_names:
                    snippet_parts.append("functions: " + ", ".join(fn_names[:5]))
                results.append({
                    "source": "api-surface",
                    "key": mod_path,
                    "snippet": "; ".join(snippet_parts) or mod_path,
                    "score": score,
                })

    # --- dep-graph.json ---
    dep_graph = _load("dep-graph.json", project_dir)
    if dep_graph:
        for src_path, targets in dep_graph.items():
            score = _score_entry(term, "dep-graph", src_path, targets)
            if score > 0:
                results.append({
                    "source": "dep-graph",
                    "key": src_path,
                    "snippet": "imports: " + ", ".join(targets[:4]),
                    "score": score,
                })

    # --- glossary.md ---
    glossary_text = _load("glossary.md", project_dir)
    if glossary_text:
        # Parse sections
        section_re = re.compile(r'^#{1,3}\s+(.+)', re.MULTILINE)
        sections = list(section_re.finditer(glossary_text))
        for i, m in enumerate(sections):
            heading = m.group(1).strip()
            end = sections[i + 1].start() if i + 1 < len(sections) else len(glossary_text)
            body = glossary_text[m.end():end].strip()
            score = _score_entry(term, "glossary", heading, body)
            if score > 0:
                results.append({
                    "source": "glossary",
                    "key": heading,
                    "snippet": body[:120],
                    "score": score,
                })

    # --- codebase-summary.md ---
    summary_text = _load("codebase-summary.md", project_dir)
    if summary_text:
        tl = term.lower()
        for line in summary_text.splitlines():
            if tl in line.lower():
                results.append({
                    "source": "codebase-summary",
                    "key": line.strip(),
                    "snippet": line.strip(),
                    "score": 1,
                })
        # Deduplicate by key
        seen: set[str] = set()
        deduped = []
        for r in results:
            if r["source"] == "codebase-summary":
                if r["key"] not in seen:
                    seen.add(r["key"])
                    deduped.append(r)
            else:
                deduped.append(r)
        results = deduped

    # Sort by score desc, then key asc for stability
    results.sort(key=lambda r: (-r["score"], r["key"]))
    return results[:10]


def get_module(path: str, project_dir: Path | None = None) -> dict[str, Any] | None:
    """
    Return the api-surface entry for a module path, or None if not found.

    Example:
        get_module("lib/rate_limiter.py")
    """
    surface = _load("api-surface.json", project_dir)
    if not surface:
        return None
    return surface.get(path)


def get_importers(module: str, project_dir: Path | None = None) -> list[str]:
    """
    Return all source files that depend on `module` (reverse dep-graph lookup).

    Example:
        get_importers("lib/circuit_breaker.py")
        # -> ["lib/agent_bus.py", "lib/claude_executor.py"]
    """
    dep_graph = _load("dep-graph.json", project_dir)
    if not dep_graph:
        return []
    importers = []
    for src, targets in dep_graph.items():
        if module in targets:
            importers.append(src)
    return sorted(importers)


def is_index_stale(project_dir: Path | None = None) -> bool:
    """Return True if the self-knowledge index is missing or older than tracked source files."""
    idx = _index_dir(project_dir)
    mtime_file = idx / ".mtime"
    if not mtime_file.exists():
        return True

    try:
        import os
        index_mtime = mtime_file.stat().st_mtime
        if project_dir is None:
            project_dir = _find_project_dir()
        if project_dir is None:
            return False

        search_roots = [
            project_dir / "lib",
            project_dir / "hooks",
            project_dir / "scripts",
            project_dir / "docs" / "adrs",
        ]
        packages_dir = project_dir / "packages"
        if packages_dir.is_dir():
            for pkg in packages_dir.iterdir():
                pkg_lib = pkg / "lib"
                if pkg_lib.is_dir():
                    search_roots.append(pkg_lib)

        for root in search_roots:
            if not root.is_dir():
                continue
            for p in root.rglob("*"):
                if p.is_file() and p.suffix in (".py", ".sh", ".md"):
                    if p.stat().st_mtime > index_mtime:
                        return True
        return False
    except OSError:
        return True
