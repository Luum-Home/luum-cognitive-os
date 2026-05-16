# SCOPE: os-only
"""Semantic skill matcher — language-agnostic skill router (ADR-296).

Replaces the prior Jaccard token-overlap implementation, which silently
fell back to zero cross-language signal because the corpus and query
shared no normalised tokens across languages.

This module is the *semantic fallback* layer for the regex router in
``lib/skill_router.py`` (line ~1668). It is consulted only when the
regex path returns a top confidence below 0.75.

Engine
------
FastEmbed (qdrant) with the Apache-2.0 multilingual model
``sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2``:

* CPU-only ONNX INT8 — no torch dependency.
* Cold-start ~200-500ms after the first download; warm < 20ms / query.
* Native multilingual (50+ languages).
* O(1) skill add/delete; catalog is hashed and cached on disk.

Note on the upstream choice
---------------------------
ADR-296 originally surveyed ``aurelio-labs/semantic-router`` as a thin
routing layer on top of FastEmbed. At adoption time the live PyPI
release line was stuck at ``0.0.3`` (no ``Route``/``RouteLayer``
symbols exported) — the project's ``0.1.x`` line referenced in the
upstream README has not been published. We therefore consume
FastEmbed directly. The routing arithmetic (cosine top-k, threshold
gate, confidence calibration) is straightforward and we lose nothing
by skipping the wrapper. The ADR captures this divergence.

Behaviour contract (what ``skill_router.py`` depends on)
--------------------------------------------------------
* ``SemanticSkillMatcher.from_routing_table(entries, skill_metadata)``
  builds an in-memory matcher. ``entries`` is the router's routing
  table; ``skill_metadata`` is the dict produced by
  :func:`load_skill_metadata`.
* ``matcher.match(text)`` returns ``List[SemanticMatch]`` sorted by
  confidence (descending), filtered to those above the calibrated
  threshold. Empty list on any failure.
* ``load_skill_metadata(paths)`` parses SKILL.md frontmatter and
  returns ``{skill_name: {"description", "summary_line",
  "routing_intents"}}``.

Kill switch
-----------
``COS_DISABLE_SEMANTIC_ROUTING=1`` makes :meth:`match` return ``[]``
immediately, before any model load. The regex layer remains intact.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Apache-2.0; ~220 MB; 50+ languages. Calibrated default — TestSafetyRecoveryNegativeContext
# and TestNoMatchCases are tuned to MiniLM's score distribution
# (DEFAULT_THRESHOLD=0.50, CONF_MIN=0.55, CONF_MAX=0.85).
#
# ADR-300 Phase 2 (REJECTED 2026-05-13 after empirical exploration):
#   multilingual-e5-large gives +14 pts precision@1 on the seed corpus, BUT
#   no single threshold satisfies the test contract:
#     threshold 0.50 → negative-context tests fail (negs at 0.73-0.76 mapped)
#     threshold 0.65 → "hello" / "thanks" still match (0.68 mapped)
#     threshold 0.87 → filters negs AND legit prompts; held-out precision
#                       drops from 0.80 to 0.53 (8/17 legit prompts return
#                       None or wrong skill)
#   Conclusion: e5-large is NOT a drop-in replacement. Adopting it requires
#   coordinated changes to (a) ADR-297 LLM tie-breaker trigger band
#   recalibration for the denser score distribution, (b) ADR-296 test
#   architecture pivot to full-pipeline checks instead of isolated matcher,
#   and (c) operator decision on screenshot-bug confidence expectation.
#   Tracked as a future ADR-302 (architectural revisit), not this slice.
#
# OPERATOR SWAP (escape hatch): hot-swap via env var COS_SEMANTIC_ROUTING_MODEL.
# Cache is keyed by `(model_name, skill_corpus_hash)` so the swap auto-
# invalidates. Try the benchmark winner with caveats:
#   COS_SEMANTIC_ROUTING_MODEL=intfloat/multilingual-e5-large
# Or try the BGE-M3 alternative (better ES/PT/IT, worse EN/DE/FR, ADR-301):
#   COS_SEMANTIC_ROUTING_MODEL=BAAI/bge-m3
# Under any non-default override, some negative-context and no-match unit
# tests will fail — that's expected; production routing relies on the full
# ADR-296+297 pipeline, not the matcher in isolation.
MODEL_OVERRIDE_ENV = "COS_SEMANTIC_ROUTING_MODEL"
_ADOPTED_DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
_BENCHMARK_WINNER_BLOCKED = "intfloat/multilingual-e5-large"  # see ADR-300 §Phase-2-Rejected
DEFAULT_MODEL_NAME = os.environ.get(MODEL_OVERRIDE_ENV) or _ADOPTED_DEFAULT_MODEL

# Cosine-similarity gate. Calibrated on the held-out multilingual prompt
# set in tests/unit/test_semantic_skill_matcher.py: precision >= 0.8 at
# 0.50 with the MiniLM baseline. Lower => more recall, more false
# positives. Tunable via env COS_SEMANTIC_THRESHOLD.
#
# Empirical note (ADR-300 Phase 2 exploration): if the override env var
# selects multilingual-e5-large, the score distribution is denser
# (1024-dim vs 384-dim) — no single threshold value separates true
# positives from semantic-mention false positives. See module docstring
# for the rejection rationale.
DEFAULT_THRESHOLD = 0.50

# Confidence-mapping output band. We cap below the regex 0.75 gate so
# that any regex match dominates even when semantic similarity is high.
CONF_MIN = 0.55
CONF_MAX = 0.85

CACHE_DIR_DEFAULT = ".cognitive-os/cache/semantic-router"

KILL_SWITCH_ENV = "COS_DISABLE_SEMANTIC_ROUTING"


def _kill_switch_active() -> bool:
    return os.environ.get(KILL_SWITCH_ENV, "").strip() in ("1", "true", "yes", "on")


# ---------------------------------------------------------------------------
# Embedding model — lazy global so we never pay cold-start twice per process
# ---------------------------------------------------------------------------

_MODEL = None
_MODEL_TRIED = False
_MODEL_NAME_LOADED: Optional[str] = None


def _load_model(model_name: str = DEFAULT_MODEL_NAME):
    """Load FastEmbed model lazily. Returns model or None if unavailable."""
    global _MODEL, _MODEL_TRIED, _MODEL_NAME_LOADED
    if _MODEL_TRIED and _MODEL_NAME_LOADED == model_name:
        return _MODEL
    _MODEL_TRIED = True
    _MODEL_NAME_LOADED = model_name
    try:
        from fastembed import TextEmbedding  # type: ignore
    except Exception as exc:  # pragma: no cover - exercised only when missing
        LOGGER.warning(
            "semantic-routing disabled: fastembed not installed (%s). "
            "Install with `pip install fastembed` or `uv sync --extra semantic-routing`.",
            exc,
        )
        _MODEL = None
        return None
    try:
        _MODEL = TextEmbedding(model_name=model_name)
    except Exception as exc:  # pragma: no cover - download / runtime failure
        LOGGER.warning("semantic-routing disabled: failed to load %s (%s)", model_name, exc)
        _MODEL = None
    return _MODEL


# ---------------------------------------------------------------------------
# Data types — keep the names used by skill_router.py
# ---------------------------------------------------------------------------

@dataclass
class SemanticMatch:
    """A semantic-fallback match (contract preserved from prior impl)."""

    skill_name: str
    confidence: float
    reason: str
    invoke_command: str
    via: str = "semantic-router"  # historical field; "embedding" | "disabled"


@dataclass
class _SkillIndex:
    """Per-skill semantic corpus + cached embeddings."""

    skill_name: str
    invoke_command: str
    description: str
    summary_line: str = ""
    routing_intents: List[str] = field(default_factory=list)
    # Cached embeddings keyed by self.corpus_hash; filled by encoder.
    embeddings: Any = None

    def corpus(self) -> List[str]:
        """Language-agnostic corpus per skill.

        Order: routing_intents (richest signal) > description > summary_line.
        Deduplicated; preserves the description so all 196 skills participate
        even if they declare no explicit ``routing_intents``.
        """
        items: List[str] = []
        seen: set[str] = set()
        for src in (self.routing_intents, [self.description], [self.summary_line]):
            for line in src:
                s = (line or "").strip()
                if not s or s in seen:
                    continue
                seen.add(s)
                items.append(s)
        return items


# ---------------------------------------------------------------------------
# Catalog signature — used for on-disk cache key
# ---------------------------------------------------------------------------

def _catalog_signature(indices: List[_SkillIndex], model_name: str) -> str:
    """Stable SHA over the catalog text + model id."""
    h = hashlib.sha256()
    h.update(model_name.encode("utf-8"))
    for idx in sorted(indices, key=lambda x: x.skill_name):
        h.update(b"\0")
        h.update(idx.skill_name.encode("utf-8"))
        for s in idx.corpus():
            h.update(b"\x1e")
            h.update(s.encode("utf-8"))
    return h.hexdigest()[:16]


def _cache_path(sig: str, cache_dir: Path) -> Path:
    return cache_dir / f"catalog-{sig}.json"


# ---------------------------------------------------------------------------
# Public matcher
# ---------------------------------------------------------------------------

class SemanticSkillMatcher:
    """Match user prompts against skill descriptions via multilingual embeddings.

    Construction
    ------------
    Use :meth:`from_routing_table` from inside :class:`SkillRouter`. The
    matcher is lazy: the embedding model isn't loaded until :meth:`match`
    is called for the first time.
    """

    def __init__(
        self,
        indices: List[_SkillIndex],
        *,
        model_name: str = DEFAULT_MODEL_NAME,
        threshold: Optional[float] = None,
        cache_dir: Optional[Path] = None,
    ):
        self._indices = indices
        self._model_name = model_name
        env_thr = os.environ.get("COS_SEMANTIC_THRESHOLD")
        if threshold is not None:
            self._threshold = threshold
        elif env_thr:
            try:
                self._threshold = float(env_thr)
            except ValueError:
                self._threshold = DEFAULT_THRESHOLD
        else:
            self._threshold = DEFAULT_THRESHOLD
        self._cache_dir = cache_dir or self._default_cache_dir()
        self._catalog_sig = _catalog_signature(indices, model_name)
        self._encoded = False
        self._catalog_matrix = None  # numpy array shape (N, D), L2-normalised
        self._catalog_row_to_skill: List[int] = []  # row -> index in self._indices

    @staticmethod
    def _default_cache_dir() -> Path:
        root = Path(os.environ.get("COGNITIVE_OS_PROJECT_DIR") or Path.cwd())
        return root / CACHE_DIR_DEFAULT

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    @classmethod
    def from_routing_table(
        cls,
        entries: List[Any],
        skill_metadata: Dict[str, Dict[str, Any]],
        *,
        model_name: str = DEFAULT_MODEL_NAME,
        threshold: Optional[float] = None,
        cache_dir: Optional[Path] = None,
    ) -> "SemanticSkillMatcher":
        """Build a matcher from the router's routing table.

        Unlike the prior implementation, EVERY skill that has at least a
        non-empty ``description`` participates — not only those that
        declared ``routing_intents``. This brings the catalog to ~196 skills
        instead of ~19, which the held-out evaluation needs in order to
        differentiate near-neighbours.
        """
        indices: List[_SkillIndex] = []
        seen: set[str] = set()
        for entry in entries:
            name = getattr(entry, "skill_name", None)
            if not name or name in seen:
                continue
            seen.add(name)
            meta = skill_metadata.get(name, {})
            desc = (meta.get("description") or "").strip()
            summary = (meta.get("summary_line") or "").strip()
            intents_raw = meta.get("routing_intents") or []
            intents = (
                [str(x).strip() for x in intents_raw if str(x).strip()]
                if isinstance(intents_raw, list)
                else []
            )
            if not desc and not summary and not intents:
                # Nothing to embed — skip.
                continue
            indices.append(
                _SkillIndex(
                    skill_name=name,
                    invoke_command=getattr(entry, "invoke_command", f"/{name}"),
                    description=desc or name.replace("-", " ").replace("_", " "),
                    summary_line=summary,
                    routing_intents=intents,
                )
            )
        return cls(
            indices,
            model_name=model_name,
            threshold=threshold,
            cache_dir=cache_dir,
        )

    # ------------------------------------------------------------------
    # Encoding
    # ------------------------------------------------------------------

    def _ensure_encoded(self) -> bool:
        """Load model and encode the catalog. Returns True on success."""
        if self._encoded:
            return self._catalog_matrix is not None
        self._encoded = True
        if not self._indices:
            return False

        try:
            import numpy as np  # type: ignore
        except Exception:
            LOGGER.warning("semantic-routing disabled: numpy unavailable")
            return False

        # Try disk cache first.
        cached = self._load_disk_cache()
        if cached is not None:
            self._catalog_matrix, self._catalog_row_to_skill = cached
            return True

        model = _load_model(self._model_name)
        if model is None:
            return False

        # Build the corpus as one flat list so we can do a single embed batch.
        flat_corpus: List[str] = []
        row_to_skill: List[int] = []
        for i, idx in enumerate(self._indices):
            for line in idx.corpus():
                flat_corpus.append(line)
                row_to_skill.append(i)
        if not flat_corpus:
            return False

        try:
            vectors = list(model.embed(flat_corpus))
            mat = np.asarray(vectors, dtype=np.float32)
            # L2-normalise each row so dot product = cosine.
            norms = np.linalg.norm(mat, axis=1, keepdims=True)
            norms = np.where(norms == 0, 1.0, norms)
            mat = mat / norms
        except Exception as exc:
            LOGGER.warning("semantic-routing: corpus embed failed (%s)", exc)
            return False

        self._catalog_matrix = mat
        self._catalog_row_to_skill = row_to_skill
        self._save_disk_cache(mat, row_to_skill)
        return True

    # ------------------------------------------------------------------
    # Disk cache (re-index only on skill drift)
    # ------------------------------------------------------------------

    def _load_disk_cache(self):
        try:
            import numpy as np  # type: ignore
        except Exception:
            return None
        path = _cache_path(self._catalog_sig, self._cache_dir)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("model") != self._model_name:
                return None
            if payload.get("sig") != self._catalog_sig:
                return None
            mat = np.asarray(payload["matrix"], dtype=np.float32)
            mapping = list(payload["row_to_skill"])
            if mat.ndim != 2 or len(mapping) != mat.shape[0]:
                return None
            return mat, mapping
        except Exception:
            return None

    def _save_disk_cache(self, mat, row_to_skill: List[int]) -> None:
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            path = _cache_path(self._catalog_sig, self._cache_dir)
            payload = {
                "model": self._model_name,
                "sig": self._catalog_sig,
                "row_to_skill": row_to_skill,
                "matrix": mat.tolist(),
            }
            path.write_text(json.dumps(payload), encoding="utf-8")
        except Exception as exc:
            LOGGER.debug("semantic-routing: failed to write cache: %s", exc)

    # ------------------------------------------------------------------
    # Public match API
    # ------------------------------------------------------------------

    def match(self, text: str, threshold: Optional[float] = None) -> List[SemanticMatch]:
        """Return semantic matches sorted by confidence (descending).

        Returns ``[]`` when:
          * ``COS_DISABLE_SEMANTIC_ROUTING=1`` is set
          * the embedding stack is unavailable (fastembed / numpy missing)
          * the prompt is empty
          * no skill scores above ``threshold``
        """
        if _kill_switch_active():
            return []
        text = (text or "").strip()
        if not text:
            return []
        if not self._ensure_encoded():
            return []
        thr = self._threshold if threshold is None else threshold

        try:
            import numpy as np  # type: ignore
            model = _load_model(self._model_name)
            if model is None:
                return []
            q_vec = list(model.embed([text]))[0]
            q = np.asarray(q_vec, dtype=np.float32)
            q_norm = float(np.linalg.norm(q))
            if q_norm == 0:
                return []
            q = q / q_norm
            sims = self._catalog_matrix @ q  # type: ignore[operator]
        except Exception as exc:
            LOGGER.debug("semantic-routing: query failed (%s)", exc)
            return []

        # Aggregate per-skill best similarity across that skill's corpus rows.
        best_per_skill: Dict[int, float] = {}
        for row, sim in enumerate(sims.tolist()):
            skill_i = self._catalog_row_to_skill[row]
            if sim > best_per_skill.get(skill_i, -1.0):
                best_per_skill[skill_i] = sim

        results: List[SemanticMatch] = []
        span = max(1e-6, 1.0 - thr)
        conf_span = CONF_MAX - CONF_MIN
        for skill_i, sim in best_per_skill.items():
            if sim < thr:
                continue
            idx = self._indices[skill_i]
            normalised = (sim - thr) / span
            conf = CONF_MIN + min(conf_span, max(0.0, normalised * conf_span))
            results.append(
                SemanticMatch(
                    skill_name=idx.skill_name,
                    confidence=conf,
                    reason=f"Semantic match (cos={sim:.2f}, model={self._model_name.split('/')[-1]})",
                    invoke_command=idx.invoke_command,
                    via="embedding",
                )
            )
        results.sort(key=lambda r: r.confidence, reverse=True)
        return results


# ---------------------------------------------------------------------------
# Frontmatter loader — preserves prior signature
# ---------------------------------------------------------------------------

def load_skill_metadata(skill_md_paths: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Parse SKILL.md frontmatter and return semantic-routing metadata.

    Returns ``{skill_name: {"description", "summary_line", "routing_intents"}}``.
    Bad files are skipped silently. ``routing_intents`` is the legacy
    structured-intent field; under ADR-296 it is *optional* — the
    description alone is enough to participate in routing.
    """
    out: Dict[str, Dict[str, Any]] = {}
    try:
        import yaml  # type: ignore
    except Exception:
        return out

    for name, path in skill_md_paths.items():
        try:
            text = Path(path).read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if "description" not in text and "summary_line" not in text and "routing_intents" not in text:
            continue
        try:
            lines = text.splitlines()
            start = None
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped == "---":
                    start = i
                    break
                if stripped.startswith("<!--") or stripped == "":
                    continue
                break
            if start is None:
                continue
            end = None
            for i in range(start + 1, len(lines)):
                if lines[i].strip() == "---":
                    end = i
                    break
            if end is None:
                continue
            data = yaml.safe_load("\n".join(lines[start + 1:end])) or {}
        except Exception:
            continue

        desc = data.get("description") or ""
        summary = data.get("summary_line") or ""
        raw_intents = data.get("routing_intents") or []
        routing_intents: List[str] = []
        if isinstance(raw_intents, list):
            for item in raw_intents:
                if isinstance(item, dict):
                    intent = str(item.get("intent") or "").strip()
                    description = str(item.get("description") or "").strip()
                    if description:
                        routing_intents.append(f"{intent}: {description}" if intent else description)
                elif isinstance(item, str):
                    s = item.strip()
                    if s:
                        routing_intents.append(s)
        out[name] = {
            "description": str(desc).strip(),
            "summary_line": str(summary).strip(),
            "routing_intents": routing_intents,
        }
    return out
