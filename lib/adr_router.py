# SCOPE: os-only
# scope: both
"""ADR Router — Suggest relevant Architecture Decision Records from prompt context.

Analogous to ``lib/skill_router.py`` (ADR-174) and ``lib/rule_router.py`` (ADR-179),
but for ADRs under ``docs/02-Decisions/adrs/``. See ADR-181.

Each ADR may have YAML frontmatter::

    ---
    adr: 181
    title: ADR Relevance Suggester
    status: accepted
    tags: [adr-routing, suggestion, rejected-surface, hooks]
    ---

The router indexes:
  1. ``tags`` list from frontmatter
  2. ``title`` keywords (lowercased, stop-words removed)
  3. First paragraph of the ``## Context`` section

Confidence threshold is 0.85 (higher than skill/rule routers, 0.80) because
ADR false positives are noisy — a stale or tangentially related ADR creates
more confusion than it resolves.

ADRs with ``status: superseded`` or ``status: deprecated`` are silently skipped.
Tombstones (``status: tombstone``) are also skipped.

Usage::

    from lib.adr_router import AdrRouter

    router = AdrRouter()
    matches = router.top_matches("how should I handle a rejected surface?", n=3)
    for m in matches:
        print(m.adr_id, m.title, m.confidence)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AdrMatch:
    """A matched ADR with confidence and display metadata."""

    adr_id: str    # e.g. "ADR-181"
    title: str     # ADR title from frontmatter or heading
    confidence: float
    reason: str    # keyword(s) that triggered this match
    file_path: str  # repo-relative path

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.adr_id} ({self.title}, confidence={self.confidence:.2f})"


# ---------------------------------------------------------------------------
# Stop words — excluded from title keyword matching to avoid noise
# ---------------------------------------------------------------------------

_STOP_WORDS: Set[str] = {
    "a", "an", "the", "and", "or", "for", "to", "of", "in", "on", "at",
    "is", "as", "by", "with", "from", "this", "that", "it", "be", "not",
    "are", "was", "were", "has", "have", "had", "do", "does", "did",
    "will", "would", "can", "could", "should", "may", "might",
    "adr", "decision", "record", "architecture",  # ubiquitous in ADR titles
}

# Minimum keyword length — single-char tokens add noise
_MIN_KW_LEN = 3


# ---------------------------------------------------------------------------
# Internal index entry
# ---------------------------------------------------------------------------

@dataclass
class _AdrEntry:
    adr_id: str      # "ADR-042"
    adr_num: int     # 42
    title: str
    status: str      # "accepted" | "proposed" | "superseded" | "deprecated" | "tombstone"
    file_path: Path
    repo_relative: str
    keywords: List[str]  # all lowercase, deduplicated, already cleaned
    tag_keywords: Set[str]   # subset of keywords sourced from frontmatter tags
    title_keywords: Set[str]  # subset of keywords sourced from title


# ---------------------------------------------------------------------------
# Frontmatter parser (no hard dep on PyYAML)
# ---------------------------------------------------------------------------

def _read_frontmatter_block(text: str) -> Optional[str]:
    """Return raw YAML between the first two '---' lines, or None."""
    lines = text.splitlines()
    start: Optional[int] = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "---":
            start = i
            break
        if stripped.startswith("<!--") or stripped == "":
            continue
        return None  # non-comment content before frontmatter
    if start is None:
        return None
    end: Optional[int] = None
    for i in range(start + 1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return None
    return "\n".join(lines[start + 1:end])


def _parse_frontmatter(text: str) -> Dict[str, Any]:
    """Parse YAML frontmatter.  Falls back to a minimal line parser."""
    block = _read_frontmatter_block(text)
    if not block:
        return {}
    try:
        import yaml  # type: ignore[import]
        return yaml.safe_load(block) or {}
    except Exception:
        pass
    # Minimal fallback: only handles flat key: value and simple inline lists
    result: Dict[str, Any] = {}
    for line in block.splitlines():
        if not line or line.startswith("#"):
            continue
        if ":" not in line or line.startswith(" "):
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()
        # Inline list: [a, b, c]
        if val.startswith("[") and val.endswith("]"):
            inner = val[1:-1]
            items = [
                item.strip().strip('"').strip("'")
                for item in inner.split(",")
                if item.strip()
            ]
            result[key] = items
        else:
            result[key] = val.strip('"').strip("'")
    return result


# ---------------------------------------------------------------------------
# Context section extractor
# ---------------------------------------------------------------------------

_CONTEXT_SECTION_RE = re.compile(
    r"^##\s+Context\s*\n(.*?)(?=^##\s|\Z)",
    re.MULTILINE | re.DOTALL,
)


def _extract_context_paragraph(text: str) -> str:
    """Return the first non-empty paragraph of the ## Context section."""
    m = _CONTEXT_SECTION_RE.search(text)
    if not m:
        return ""
    body = m.group(1)
    for para in body.split("\n\n"):
        stripped = para.strip()
        if stripped:
            return stripped
    return ""


# ---------------------------------------------------------------------------
# Keyword extraction helpers
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_\-]*")


def _tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall(text.lower())


def _keywords_from_text(text: str) -> List[str]:
    """Return lowercased tokens, deduped, stop-words removed, min length enforced."""
    seen: Set[str] = set()
    result: List[str] = []
    for tok in _tokenize(text):
        # Split hyphenated tokens into parts as well
        parts = tok.replace("-", "_").split("_")
        for part in [tok] + parts:
            part = part.strip("-_")
            if len(part) >= _MIN_KW_LEN and part not in _STOP_WORDS and part not in seen:
                seen.add(part)
                result.append(part)
    return result


def _keywords_from_tags(tags: Any) -> List[str]:
    """Normalise tags list from frontmatter to keyword tokens."""
    if not isinstance(tags, list):
        return []
    result: List[str] = []
    for tag in tags:
        result.extend(_keywords_from_text(str(tag)))
    return result


# ---------------------------------------------------------------------------
# ADR file loader
# ---------------------------------------------------------------------------

def _adr_num_from_filename(path: Path) -> Optional[int]:
    """Extract ADR number from filename like ADR-042-..."""
    m = re.match(r"ADR-(\d+)", path.stem, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return None


def _load_adr_entry(path: Path, project_root: Path) -> Optional[_AdrEntry]:
    """Parse a single ADR file into an index entry.  Returns None on skip/error."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    fm = _parse_frontmatter(text)

    # --- status checks ---
    raw_status = str(fm.get("status", "")).strip().lower()
    # Tombstone files also contain "tombstone" in filename
    is_tombstone = ("tombstone" in path.name.lower() or raw_status == "tombstone")
    if is_tombstone or raw_status in ("superseded", "deprecated"):
        return None

    # --- ADR ID ---
    adr_num = fm.get("adr")
    if adr_num is None:
        adr_num = _adr_num_from_filename(path)
    if adr_num is None:
        return None
    try:
        adr_num_int = int(adr_num)
    except (ValueError, TypeError):
        return None
    adr_id = f"ADR-{adr_num_int:03d}"

    # --- title ---
    title_raw = str(fm.get("title", "")).strip()
    if not title_raw:
        # Try first H1 heading
        m = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        if m:
            title_raw = m.group(1).strip()
    title = title_raw or adr_id

    # --- keywords from tags ---
    tag_kws = _keywords_from_tags(fm.get("tags", []))
    tag_set = set(tag_kws)

    # --- keywords from title ---
    title_kws = _keywords_from_text(title_raw)
    title_set = set(title_kws)

    # --- keywords from first Context paragraph ---
    ctx = _extract_context_paragraph(text)
    ctx_kws = _keywords_from_text(ctx)

    # Merge all, deduplicate while preserving order (tags first = higher weight)
    seen: Set[str] = set()
    deduped: List[str] = []
    for k in tag_kws + title_kws + ctx_kws:
        if k not in seen:
            seen.add(k)
            deduped.append(k)

    try:
        repo_relative = str(path.relative_to(project_root))
    except ValueError:
        repo_relative = str(path)

    return _AdrEntry(
        adr_id=adr_id,
        adr_num=adr_num_int,
        title=title,
        status=raw_status,
        file_path=path,
        repo_relative=repo_relative,
        keywords=deduped,
        tag_keywords=tag_set,
        title_keywords=title_set,
    )


# ---------------------------------------------------------------------------
# AdrRouter
# ---------------------------------------------------------------------------

class AdrRouter:
    """Match user prompts to relevant ADRs.

    Args:
        adrs_dir: Path to the directory containing ADR-*.md files.
                  Auto-detected from this file's location if not provided.
        project_root: Repo root for computing relative paths in results.
    """

    def __init__(
        self,
        adrs_dir: Optional[Path | str] = None,
        *,
        project_root: Optional[Path | str] = None,
    ) -> None:
        if project_root is None:
            _lib_dir = Path(__file__).resolve().parent
            self._project_root = _lib_dir.parent
        else:
            self._project_root = Path(project_root).resolve()

        if adrs_dir is None:
            self._adrs_dir = self._project_root / "docs" / "02-Decisions" / "adrs"
        else:
            self._adrs_dir = Path(adrs_dir).resolve()

        # Lazy-loaded index: None means not yet built.
        self._index: Optional[List[_AdrEntry]] = None

    # ------------------------------------------------------------------
    # Index management (lazy, cached)
    # ------------------------------------------------------------------

    def _build_index(self) -> List[_AdrEntry]:
        """Scan adrs_dir and build the keyword index.  Called once."""
        entries: List[_AdrEntry] = []
        if not self._adrs_dir.is_dir():
            return entries
        for adr_file in sorted(self._adrs_dir.glob("ADR-*.md")):
            entry = _load_adr_entry(adr_file, self._project_root)
            if entry is not None:
                entries.append(entry)
        return entries

    @property
    def index(self) -> List[_AdrEntry]:
        """Lazy-loaded, cached keyword index."""
        if self._index is None:
            self._index = self._build_index()
        return self._index

    def invalidate_cache(self) -> None:
        """Force re-indexing on next access (e.g. after a new ADR is written)."""
        self._index = None

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    @staticmethod
    def _score(prompt_kws: List[str], entry: _AdrEntry) -> Tuple[float, str]:
        """Compute a confidence score in [0,1] for (prompt, entry).

        Scoring strategy (three weighted tiers):
          1. Tag matches  (weight 3.0) — frontmatter tags are curated signals.
          2. Title matches (weight 2.0) — title keywords are strong signals.
          3. Context matches (weight 1.0) — context paragraph is weaker signal.

        Weighted hit score = sum(weight_i for each matching keyword).
        Normalised by sqrt(total_entry_kw_count) to avoid penalising large ADRs.
        Capped at 1.0.

        The weights are tuned so that a 3-token title match on a 15-token ADR
        gives ~3*2/sqrt(15) ≈ 1.55 → capped to 1.0, and a single tag match on
        a 40-token ADR gives 3/sqrt(40) ≈ 0.47.  Good tag coverage rewards
        precision; title matching ensures untagged ADRs are still discoverable.

        Returns (confidence, matched_keywords_str).
        """
        if not entry.keywords or not prompt_kws:
            return 0.0, ""

        prompt_set = set(prompt_kws)
        all_kw_set = set(entry.keywords)

        hits = prompt_set & all_kw_set
        if not hits:
            return 0.0, ""

        weighted_hits = 0.0
        for kw in hits:
            if kw in entry.tag_keywords:
                weighted_hits += 3.0
            elif kw in entry.title_keywords:
                weighted_hits += 2.0
            else:
                weighted_hits += 1.0

        normaliser = len(all_kw_set) ** 0.5 if all_kw_set else 1.0
        confidence = min(weighted_hits / normaliser, 1.0)
        return confidence, ", ".join(sorted(hits))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def top_matches(
        self,
        prompt: str,
        n: int = 3,
        min_confidence: float = 0.85,
    ) -> List[AdrMatch]:
        """Return up to *n* ADRs most relevant to *prompt*.

        Only results with confidence >= *min_confidence* are returned.
        Results are sorted by confidence descending.

        Args:
            prompt: The user prompt text to match against.
            n: Maximum number of results.
            min_confidence: Minimum confidence threshold (default 0.85).

        Returns:
            List of AdrMatch, possibly empty.
        """
        if not prompt or not prompt.strip():
            return []

        prompt_kws = _keywords_from_text(prompt)
        if not prompt_kws:
            return []

        scored: List[Tuple[float, str, _AdrEntry]] = []
        for entry in self.index:
            conf, matched = self._score(prompt_kws, entry)
            if conf >= min_confidence:
                scored.append((conf, matched, entry))

        scored.sort(key=lambda t: t[0], reverse=True)

        results: List[AdrMatch] = []
        for conf, matched, entry in scored[:n]:
            results.append(AdrMatch(
                adr_id=entry.adr_id,
                title=entry.title,
                confidence=round(conf, 4),
                reason=f"keyword match: {matched}",
                file_path=entry.repo_relative,
            ))
        return results

    # ------------------------------------------------------------------
    # Coverage helpers (used by manifests/adr-routing-coverage.yaml)
    # ------------------------------------------------------------------

    def coverage_stats(self) -> Dict[str, Any]:
        """Return tag coverage statistics for the manifest."""
        all_entries_on_disk: List[Tuple[str, bool]] = []
        if not self._adrs_dir.is_dir():
            return {}
        for adr_file in sorted(self._adrs_dir.glob("ADR-*.md")):
            try:
                text = adr_file.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            fm = _parse_frontmatter(text)
            raw_status = str(fm.get("status", "")).strip().lower()
            is_tombstone = "tombstone" in adr_file.name.lower() or raw_status == "tombstone"
            if is_tombstone:
                continue  # exclude tombstones from denominator
            has_tags = bool(fm.get("tags"))
            all_entries_on_disk.append((adr_file.name, has_tags))

        total = len(all_entries_on_disk)
        with_tags = sum(1 for _, ht in all_entries_on_disk if ht)
        coverage_pct = round(100.0 * with_tags / total, 1) if total else 0.0
        return {
            "total_non_tombstone": total,
            "with_tags": with_tags,
            "coverage_percent": coverage_pct,
            "target_min_percent": 75.0,
            "meets_target": coverage_pct >= 75.0,
        }
