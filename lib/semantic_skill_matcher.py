# SCOPE: os-only
"""Semantic skill matcher — language-agnostic fallback for SkillRouter.

This module provides a *fallback* layer to the regex-based primary routing in
`lib/skill_router.py`. It is only consulted when the regex path does not yield
a confident match (>= 0.75). The motivation is correctness: regex patterns are
inherently language-dependent — `\\b(ayudar|help)\\b` fails for French,
Portuguese, German, Italian, etc. The semantic path uses the skill's
``description`` plus optional ``intent_examples`` from the frontmatter as the
training signal.

Strategy (cheapest path first):
  1. If `sentence-transformers` is installed, use a multilingual MiniLM model
     to embed prompt + skill corpora once, then return cosine similarity.
  2. Otherwise fall back to a token-overlap heuristic that normalises case,
     strips diacritics, and uses character n-gram Jaccard overlap. This is
     intentionally a weak signal — it is better than zero, and avoids any
     network call.

The LLM-based fallback (via ``lib/dispatch.py``) is exposed via
:meth:`SemanticSkillMatcher.llm_classify` but is *not* invoked automatically
from ``SkillRouter.match`` because dispatch cost > regex cost. Callers (e.g.
the orchestrator) may invoke it explicitly when both regex and the embedding
fallback miss.

ADR justification: additive — new optional fallback path, regex path
unchanged. See ADR-017 (Stabilization Freeze) carve-out for
correctness/language-agnostic fixes.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# Lazy global cache for the embedding model — loading takes ~3s, so we never
# want to do it more than once per process.
_EMBEDDING_MODEL = None
_EMBEDDING_MODEL_TRIED = False


def _try_load_embedding_model():
    """Attempt to load a small multilingual sentence-transformer model.

    Returns the model or None if unavailable. Caches result globally so we
    never re-try the import after a failure.
    """
    global _EMBEDDING_MODEL, _EMBEDDING_MODEL_TRIED
    if _EMBEDDING_MODEL_TRIED:
        return _EMBEDDING_MODEL
    _EMBEDDING_MODEL_TRIED = True
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore

        # Multilingual, ~120MB, supports 50+ languages
        _EMBEDDING_MODEL = SentenceTransformer(
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
    except Exception:
        _EMBEDDING_MODEL = None
    return _EMBEDDING_MODEL


# ---------------------------------------------------------------------------
# Diacritic-insensitive token utilities (the fallback path)
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    """Lowercase, strip diacritics, collapse whitespace."""
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_only = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", ascii_only.lower()).strip()


_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> List[str]:
    return _TOKEN_RE.findall(_normalize(text))


# A modest multilingual stoplist — keeps the overlap signal focused on
# content words. Missing a language here only causes false-positive overlap
# (downgraded by the threshold), never a false negative.
_STOPWORDS: frozenset[str] = frozenset({
    # English
    "the", "a", "an", "and", "or", "is", "are", "to", "for", "of", "in",
    "on", "with", "this", "that", "it", "be", "can", "do", "does", "have",
    "has", "i", "you", "we", "they", "my", "your", "our", "what", "which",
    "if", "when", "how", "why", "from", "as", "at",
    # Spanish
    "el", "la", "los", "las", "un", "una", "unos", "unas", "y", "o", "de",
    "del", "al", "en", "para", "por", "con", "este", "esta", "estos", "estas",
    "ese", "esa", "esos", "esas", "es", "son", "ser", "estar", "que", "quien",
    "como", "cuando", "donde", "porque", "sirve", "puede", "ayudar",
    # Portuguese
    "este", "esta", "isto", "esse", "essa", "isso", "para", "por", "com",
    "que", "qual", "quem", "como", "quando", "onde", "porque", "serve",
    "pode", "ajudar", "nao", "sim",
    # German
    "der", "die", "das", "den", "dem", "des", "ein", "eine", "einer",
    "einen", "und", "oder", "ist", "sind", "fur", "mit", "von", "im", "in",
    "auf", "kann", "konnen", "wer", "was", "wie", "warum", "wann", "wo",
    "ohne",
    # French
    "le", "la", "les", "un", "une", "des", "et", "ou", "est", "sont", "de",
    "du", "pour", "avec", "ce", "cette", "ces", "que", "qui", "comment",
    "quand", "pourquoi", "peut", "aider",
    # Italian
    "il", "lo", "la", "i", "gli", "le", "un", "uno", "una", "e", "o", "di",
    "del", "della", "in", "per", "con", "questo", "questa", "questi", "queste",
    "che", "chi", "come", "quando", "dove", "perche", "puo", "aiutare",
})


def _content_tokens(text: str) -> set[str]:
    return {t for t in _tokens(text) if len(t) >= 2 and t not in _STOPWORDS}


def _jaccard_overlap(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@dataclass
class SemanticMatch:
    """A semantic-fallback match."""

    skill_name: str
    confidence: float
    reason: str
    invoke_command: str
    via: str = "semantic"  # "embedding" | "overlap" | "llm"


@dataclass
class _SkillSemanticIndex:
    """In-memory semantic corpus for one skill."""

    skill_name: str
    invoke_command: str
    description: str
    intent_examples: List[str] = field(default_factory=list)
    # Cached embeddings (one vector per example + description), lazily filled
    _embeddings: Any = None
    _normalized_tokens: Optional[List[set[str]]] = None

    def corpus(self) -> List[str]:
        items: List[str] = []
        if self.description:
            items.append(self.description)
        items.extend(self.intent_examples)
        return items

    def token_sets(self) -> List[set[str]]:
        if self._normalized_tokens is None:
            self._normalized_tokens = [_content_tokens(s) for s in self.corpus()]
        return self._normalized_tokens


class SemanticSkillMatcher:
    """Match prompts to skills via embeddings or token overlap.

    Designed to be cheap on cold start when no skill has ``intent_examples``:
    skills with only a description still index, but the signal is weaker.
    """

    def __init__(self, indices: List[_SkillSemanticIndex]):
        self._indices = indices
        # Try to warm the embedding model — non-blocking semantics: if it
        # fails we'll just use the overlap path.
        self._model = _try_load_embedding_model()
        if self._model is not None:
            self._encode_corpus()

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    @classmethod
    def from_routing_table(
        cls, entries: List[Any], skill_metadata: Dict[str, Dict[str, Any]]
    ) -> "SemanticSkillMatcher":
        """Build a matcher from a SkillRouter's routing entries.

        Args:
            entries: list of `_RoutingEntry` (each has skill_name + invoke_command)
            skill_metadata: dict skill_name -> {"description": str,
                "intent_examples": list[str]}
        """
        indices: List[_SkillSemanticIndex] = []
        seen: set[str] = set()
        for entry in entries:
            name = getattr(entry, "skill_name", None)
            if not name or name in seen:
                continue
            seen.add(name)
            meta = skill_metadata.get(name, {})
            desc = (meta.get("description") or "").strip()
            examples = meta.get("intent_examples") or []
            if not isinstance(examples, list):
                examples = []
            # Skip skills with no semantic signal at all.
            if not desc and not examples:
                continue
            indices.append(
                _SkillSemanticIndex(
                    skill_name=name,
                    invoke_command=getattr(entry, "invoke_command", f"/{name}"),
                    description=desc,
                    intent_examples=[str(e) for e in examples if str(e).strip()],
                )
            )
        return cls(indices)

    # ------------------------------------------------------------------
    # Core matching
    # ------------------------------------------------------------------

    def _encode_corpus(self) -> None:
        if self._model is None:
            return
        for idx in self._indices:
            try:
                idx._embeddings = self._model.encode(
                    idx.corpus(), normalize_embeddings=True
                )
            except Exception:
                idx._embeddings = None

    def match(self, text: str, threshold: float = 0.55) -> List[SemanticMatch]:
        """Return semantic matches sorted by confidence (descending).

        Skills below ``threshold`` are excluded. The threshold is intentionally
        lower than the regex 0.75 gate because the semantic confidence scale
        is calibrated differently — values above ~0.55 indicate genuine
        semantic alignment for the multilingual MiniLM model.
        """
        text = (text or "").strip()
        if not text or not self._indices:
            return []
        if self._model is not None:
            return self._match_embeddings(text, threshold)
        return self._match_overlap(text, threshold=max(0.18, threshold * 0.4))

    # ------------------------------------------------------------------
    # Embedding path
    # ------------------------------------------------------------------

    def _match_embeddings(self, text: str, threshold: float) -> List[SemanticMatch]:
        try:
            import numpy as np  # type: ignore
        except Exception:
            return self._match_overlap(text, threshold=max(0.18, threshold * 0.4))

        try:
            query_vec = self._model.encode([text], normalize_embeddings=True)[0]
        except Exception:
            return self._match_overlap(text, threshold=max(0.18, threshold * 0.4))

        results: List[SemanticMatch] = []
        for idx in self._indices:
            if idx._embeddings is None or len(idx._embeddings) == 0:
                continue
            try:
                sims = np.asarray(idx._embeddings) @ np.asarray(query_vec)
                best_sim = float(sims.max())
            except Exception:
                continue
            if best_sim >= threshold:
                # Map cosine similarity [threshold..1.0] -> confidence [0.55..0.85].
                # We cap below 0.90 so regex matches always dominate when they fire.
                normalised = (best_sim - threshold) / max(1e-6, (1.0 - threshold))
                conf = 0.55 + min(0.30, max(0.0, normalised * 0.30))
                results.append(SemanticMatch(
                    skill_name=idx.skill_name,
                    confidence=conf,
                    reason=f"Semantic match (embedding sim={best_sim:.2f})",
                    invoke_command=idx.invoke_command,
                    via="embedding",
                ))
        results.sort(key=lambda r: r.confidence, reverse=True)
        return results

    # ------------------------------------------------------------------
    # Overlap path (fallback when no embeddings)
    # ------------------------------------------------------------------

    def _match_overlap(self, text: str, threshold: float) -> List[SemanticMatch]:
        query_tokens = _content_tokens(text)
        if not query_tokens:
            return []
        results: List[SemanticMatch] = []
        for idx in self._indices:
            best = 0.0
            for ts in idx.token_sets():
                score = _jaccard_overlap(query_tokens, ts)
                if score > best:
                    best = score
            if best >= threshold:
                # Map overlap [threshold..0.6] -> confidence [0.55..0.80].
                normalised = min(1.0, (best - threshold) / max(1e-6, 0.6 - threshold))
                conf = 0.55 + 0.25 * normalised
                results.append(SemanticMatch(
                    skill_name=idx.skill_name,
                    confidence=conf,
                    reason=f"Semantic match (token overlap={best:.2f})",
                    invoke_command=idx.invoke_command,
                    via="overlap",
                ))
        results.sort(key=lambda r: r.confidence, reverse=True)
        return results

    # ------------------------------------------------------------------
    # Optional LLM fallback (explicit opt-in only — costs tokens)
    # ------------------------------------------------------------------

    def llm_classify(self, text: str) -> Optional[SemanticMatch]:
        """Use lib/dispatch.py to ask an LLM which skill best matches.

        Returns None if dispatch is unavailable or the response is malformed.
        Intentionally not called from ``SkillRouter.match`` — callers must
        opt-in (e.g. orchestrator on truly unmatched prompts).
        """
        try:
            from lib import dispatch  # type: ignore
        except Exception:
            return None

        candidates = "\n".join(
            f"- {idx.skill_name}: {idx.description[:120]}"
            for idx in self._indices
        )
        prompt = (
            "You are a skill router. Pick the single best skill for the user "
            "message, in any language. Reply with ONLY the skill name from the "
            "list, or NONE if no skill fits.\n\n"
            f"Skills:\n{candidates}\n\nUser message:\n{text}\n\nSkill:"
        )
        try:
            result = dispatch.run(prompt=prompt, task_type="classification")  # type: ignore[attr-defined]
            response = (result.get("response") if isinstance(result, dict) else str(result)) or ""
        except Exception:
            return None

        chosen = response.strip().splitlines()[0].strip() if response.strip() else ""
        chosen = chosen.split()[0].strip(".,:;") if chosen else ""
        if not chosen or chosen.upper() == "NONE":
            return None
        for idx in self._indices:
            if idx.skill_name == chosen:
                return SemanticMatch(
                    skill_name=idx.skill_name,
                    confidence=0.70,
                    reason="Semantic match (LLM classifier)",
                    invoke_command=idx.invoke_command,
                    via="llm",
                )
        return None


# ---------------------------------------------------------------------------
# Frontmatter loader for intent_examples
# ---------------------------------------------------------------------------

def load_skill_metadata(skill_md_paths: Dict[str, "Any"]) -> Dict[str, Dict[str, Any]]:
    """Load description + intent_examples from a set of SKILL.md paths.

    Returns mapping skill_name -> {"description": str, "intent_examples": list}.
    Never raises — bad files are skipped silently.
    """
    out: Dict[str, Dict[str, Any]] = {}
    for name, path in skill_md_paths.items():
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if "intent_examples" not in text and "description" not in text:
            continue
        try:
            import yaml  # type: ignore
            lines = text.splitlines()
            start = None
            for i, line in enumerate(lines):
                if line.strip() == "---":
                    start = i
                    break
                if line.strip().startswith("<!--") or line.strip() == "":
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
        examples = data.get("intent_examples") or []
        if not isinstance(examples, list):
            examples = []
        out[name] = {
            "description": str(desc).strip(),
            "intent_examples": [str(e).strip() for e in examples if str(e).strip()],
        }
    return out
