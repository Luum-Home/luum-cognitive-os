# SCOPE: both
"""Engram lifecycle wrapper — confidence scoring, Ebbinghaus decay, and reinforcement.

This module wraps ``lib.engram_client`` to add lifecycle metadata to every
observation as a structured trailer in the ``content`` field.  The trailer is
engram-transparent: the binary stores and retrieves it as opaque text.

FOR (use case)
--------------
Use this module when you want search results ranked by actual epistemic state
rather than text relevance alone.  Frequently confirmed, recently accessed
observations surface above stale ones with equal BM25+vector relevance.

ADR reference: ``docs/adrs/ADR-071-engram-lifecycle-evolution.md``

Trailer schema (appended to the end of observation content):

    <engram-lifecycle>
    {"confidence": 0.5, "last_reinforced": "2026-04-27T15:30:00Z", "reinforcement_count": 0, "decay_class": "decision"}
    </engram-lifecycle>

Lifecycle metadata stays inert to engram's search and storage — it is
machine-readable only by this module.

NOT (cross-reference)
----------------------
This module does NOT replace ``lib.engram_client``.  It wraps it.  Direct
callers of ``engram_client`` (hooks, memory.py) are unaffected.  The lifecycle
layer is opt-in by using this module instead of calling ``engram_client``
directly.
"""

from __future__ import annotations

import json
import math
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any, Callable

# Allow both `from lib.engram_lifecycle import ...` and direct execution
_LIB_DIR = os.path.dirname(os.path.abspath(__file__))
if _LIB_DIR not in sys.path:
    sys.path.insert(0, os.path.dirname(_LIB_DIR))

from lib import engram_client  # noqa: E402 (after sys.path setup)
from lib import engram_http_client  # noqa: E402 (after sys.path setup)

# Path to engram binary — same override as engram_client
_ENGRAM_BIN = os.environ.get("ENGRAM_BIN", "engram")

# Regex anchored at end-of-string, tolerant of trailing whitespace/newlines.
# Matches the exact tag literals required by ADR-071.
_TRAILER_RE = re.compile(
    r"<engram-lifecycle>\s*(\{.*?\})\s*</engram-lifecycle>\s*$",
    re.DOTALL,
)

# Decay time constants (τ) in days per decay class — ADR-071 §Decay classes
_DECAY_TAU: dict[str, int] = {
    "architecture": 365,
    "decision": 180,
    "pattern": 180,
    "discovery": 90,
    "bugfix": 60,
    "manual": 90,
}

# Type → decay_class mapping — ADR-071 §Decay classes
_TYPE_TO_DECAY_CLASS: dict[str, str] = {
    "architecture": "architecture",
    "decision": "decision",
    "pattern": "pattern",
    "discovery": "discovery",
    "config": "discovery",
    "bugfix": "bugfix",
}

# Ranking constants — ADR-071 §Ranking formula
_ALPHA: float = 0.3   # lifecycle weight; engram relevance dominates at 70%
_BETA: float = 0.15   # confidence increment per reinforcement


# ---------------------------------------------------------------------------
# Module-level pure functions (testable without class instantiation)
# ---------------------------------------------------------------------------


def decay_retention(t_days: float, tau: float) -> float:
    """Ebbinghaus retention function R(t) = exp(-t / tau).

    Args:
        t_days: Days elapsed since last reinforcement. Must be >= 0.
        tau:    Decay time constant in days (class-specific half-life proxy).

    Returns:
        Retention value in (0, 1].  R(0) == 1.0 exactly.
    """
    return math.exp(-t_days / tau)


def reinforce_confidence(current: float, beta: float = _BETA) -> float:
    """Asymptotic confidence update: confidence_new = confidence_old + (1 - confidence_old) * beta.

    Confidence converges toward 1.0 but never reaches it.

    Args:
        current: Current confidence value in [0.0, 1.0).
        beta:    Reinforcement increment factor (default 0.15).

    Returns:
        Updated confidence value strictly greater than ``current`` and < 1.0.
    """
    return current + (1.0 - current) * beta


def adjusted_score(
    base_score: float,
    confidence: float,
    retention: float,
    alpha: float = _ALPHA,
) -> float:
    """Lifecycle-adjusted ranking score.

    Formula: adjusted = base_score * (1 - alpha) + confidence * retention * alpha

    The result is always in [0.0, 1.0] because:
    - base_score ∈ [0, 1], confidence ∈ [0, 1], retention ∈ (0, 1], alpha ∈ [0, 1]

    Args:
        base_score: Engram's native relevance score (BM25+vector), normalized to [0, 1].
        confidence: Observation's current confidence value.
        retention:  R(t) from decay_retention().
        alpha:      Lifecycle weight (default 0.3).

    Returns:
        Adjusted score in [0.0, 1.0].
    """
    return base_score * (1.0 - alpha) + confidence * retention * alpha


# ---------------------------------------------------------------------------
# EngramLifecycle class
# ---------------------------------------------------------------------------


class EngramLifecycle:
    """Wrapper around engram_client that adds confidence scoring and Ebbinghaus decay.

    Inject a ``now`` callable for deterministic testing:

        lc = EngramLifecycle(now=lambda: datetime(2026, 4, 27, 15, 30, 0))

    All public methods inherit engram_client's never-raise contract — errors
    produce empty/None/False returns silently.
    """

    DECAY_TAU: dict[str, int] = _DECAY_TAU
    ALPHA: float = _ALPHA
    BETA: float = _BETA

    def __init__(self, now: Callable[[], datetime] | None = None) -> None:
        """
        Args:
            now: Optional callable that returns the current UTC datetime.
                 Defaults to datetime.utcnow.  Inject for deterministic tests.
        """
        self._now: Callable[[], datetime] = now or (
            lambda: datetime.now(timezone.utc).replace(tzinfo=None)
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save(
        self,
        title: str,
        content: str,
        type_: str,
        topic_key: str = "",
        project: str = "",
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        """Save an observation with a lifecycle trailer appended to content.

        Args:
            title:     Observation title.
            content:   Observation body (trailer will be appended).
            type_:     Engram type (e.g. ``"decision"``, ``"bugfix"``).
            topic_key: Optional topic key for grouping related observations.
            project:   Optional project scope.
            **kwargs:  Forwarded to ``engram_client.save_observation`` if supported.

        Returns:
            The created observation dict, or ``None`` on failure.
        """
        decay_class = self._decay_class_for_type(type_)
        content_with_trailer = self.build_content_with_trailer(content, decay_class)
        return engram_client.save_observation(
            title,
            content_with_trailer,
            type_=type_,
            topic_key=topic_key,
            project=project,
        )

    def search(
        self,
        query: str,
        project: str | None = None,
        limit: int = 10,
        lifecycle_weight: bool = True,
        type_filter: str = "",
        graph_walk: bool = False,
    ) -> list[dict[str, Any]]:
        """Search observations with optional lifecycle-based re-ranking.

        When ``lifecycle_weight=True`` (default), results are re-ranked by the
        formula: adjusted_score = base * 0.7 + confidence * R(t) * 0.3.

        Results without a lifecycle trailer are treated as confidence=0.5,
        retention=1.0 (neutral, not penalized).

        When ``graph_walk=True``, the ``memory_relations`` SQLite table is
        traversed (up to 2 hops) for each result, and connected observations
        are merged into the ranked set.  Default is OFF so callers from Phase 1
        and Phase 2 are unaffected.

        Args:
            query:            Free-text search query.
            project:          Optional project scope.
            limit:            Maximum results to return.
            lifecycle_weight: Set False to return engram's native ordering.
            type_filter:      Optional type filter forwarded to engram_client.
            graph_walk:       When True, extend results via graph traversal.

        Returns:
            List of observation dicts, each extended with:
            ``confidence``, ``retention``, ``adjusted_score`` (when lifecycle_weight=True).
            When ``graph_walk=True``, graph-only hits also include ``graph_only=True``
            and ``hops`` fields.
        """
        kwargs: dict[str, Any] = {"limit": limit, "type_filter": type_filter}
        if project:
            kwargs["project"] = project

        results = engram_client.search_observations(query, **kwargs)

        if not lifecycle_weight:
            return results

        enriched = []
        for obs in results:
            trailer = self._parse_trailer(obs.get("content", ""))
            retention = self._apply_decay(trailer)

            if trailer is not None:
                confidence = float(trailer.get("confidence", 0.5))
            else:
                confidence = 0.5

            # Engram does not return a normalised score field; use 1.0 as base
            # so lifecycle signal still applies.  If engram ever exposes a score
            # field, prefer it here.
            raw_score = float(obs.get("score", 1.0))
            score = adjusted_score(raw_score, confidence, retention, self.ALPHA)

            enriched.append(
                {
                    **obs,
                    "confidence": confidence,
                    "retention": retention,
                    "adjusted_score": score,
                }
            )

        enriched.sort(key=lambda x: x["adjusted_score"], reverse=True)

        if not graph_walk:
            return enriched

        # Phase 3: walk memory_relations graph and merge neighbors
        try:
            from lib.engram_graph_walker import EngramGraphWalker

            walker = EngramGraphWalker()
            all_sync_ids = [
                obs.get("sync_id", "") for obs in enriched if obs.get("sync_id")
            ]
            if all_sync_ids:
                neighbors = walker.walk(all_sync_ids)
                if neighbors:
                    enriched = walker.merge_into_results(enriched, neighbors)
        except Exception:
            pass

        return enriched

    def reinforce(self, observation_id: str | int) -> bool:
        """Bump reinforcement_count, reset last_reinforced, and increase confidence.

        Uses the engram HTTP API (port 7437) to fetch and update the observation
        in-place via GET /observations/<id> + PATCH /observations/<id>.  This is
        the correct approach now that the HTTP daemon exposes the full CRUD API.

        Falls back to False when the HTTP daemon is unreachable — callers that
        do not have an engram daemon running get a no-op rather than an error.

        Phase 1 caveat correction (ADR-071 addendum 2026-04-27): the original
        implementation re-saved observations under new IDs because the CLI lacked
        ``get``/``update`` commands.  The HTTP API at port 7437 was discovered to
        support both operations, so this method now performs a true in-place update.

        Args:
            observation_id: Engram observation ID (integer or string).

        Returns:
            True if reinforcement succeeded, False otherwise.
        """
        if not engram_http_client.is_available():
            return False

        obs = engram_http_client.get_observation(observation_id)
        if obs is None:
            return False

        content = obs.get("content", "")
        trailer = self._parse_trailer(content)

        if trailer is None:
            # Observation predates Phase 1 — synthesise default trailer
            decay_class = self._decay_class_for_type(obs.get("type", "manual"))
            trailer = {
                "confidence": 0.5,
                "last_reinforced": self._now_iso(),
                "reinforcement_count": 0,
                "decay_class": decay_class,
            }
        else:
            trailer = dict(trailer)  # copy to avoid mutation of parsed dict

        trailer["reinforcement_count"] = int(trailer.get("reinforcement_count", 0)) + 1
        trailer["last_reinforced"] = self._now_iso()
        trailer["confidence"] = reinforce_confidence(
            float(trailer.get("confidence", 0.5)), self.BETA
        )

        new_content = self._strip_trailer(content) + self._format_trailer(trailer)
        result = engram_http_client.update_observation(
            observation_id, content=new_content
        )
        return result is not None

    # ------------------------------------------------------------------
    # Trailer helpers
    # ------------------------------------------------------------------

    def build_content_with_trailer(self, content: str, decay_class: str) -> str:
        """Append a lifecycle trailer with default values to *content*.

        Args:
            content:     Original observation body.
            decay_class: One of the keys in DECAY_TAU.

        Returns:
            Content string with trailer block appended.
        """
        trailer = self.default_trailer()
        trailer["decay_class"] = decay_class
        return self._append_trailer_json(content, trailer)

    def default_trailer(self) -> dict[str, Any]:
        """Return a default lifecycle trailer dict with current UTC time.

        Returns:
            Dict with keys: confidence, last_reinforced, reinforcement_count, decay_class.
        """
        return {
            "confidence": 0.5,
            "last_reinforced": self._iso_now(),
            "reinforcement_count": 0,
            "decay_class": "manual",
        }

    def _parse_trailer(self, content: str) -> dict[str, Any] | None:
        """Extract and parse the lifecycle trailer from observation content.

        Args:
            content: Raw observation content string.

        Returns:
            Parsed trailer dict, or None if no valid trailer is found.
            Never raises.
        """
        if not content:
            return None
        try:
            match = _TRAILER_RE.search(content)
            if not match:
                return None
            return json.loads(match.group(1))
        except Exception:
            return None

    def _apply_decay(self, trailer: dict[str, Any] | None) -> float:
        """Compute current retention R(t) from the trailer.

        Args:
            trailer: Parsed trailer dict, or None for observations without a trailer.

        Returns:
            Retention value in (0, 1].  Returns 1.0 for missing/malformed trailers.
        """
        if trailer is None:
            return 1.0
        try:
            last_reinforced_str = trailer.get("last_reinforced", "")
            if not last_reinforced_str:
                return 1.0

            last_reinforced = _parse_iso8601_utc(last_reinforced_str)
            now = self._now()
            t_days = max(0.0, (now - last_reinforced).total_seconds() / 86400.0)

            decay_class = trailer.get("decay_class", "manual")
            tau = float(self.DECAY_TAU.get(decay_class, self.DECAY_TAU["manual"]))
            return decay_retention(t_days, tau)
        except Exception:
            return 1.0

    def _decay_class_for_type(self, type_: str) -> str:
        """Map an engram observation type to a decay class.

        Args:
            type_: Engram type string (e.g. ``"decision"``, ``"bugfix"``).

        Returns:
            Decay class string.  Unknown types map to ``"manual"``.
        """
        return _TYPE_TO_DECAY_CLASS.get(type_, "manual")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _iso_now(self) -> str:
        """Return current UTC time as ISO-8601 string with trailing Z."""
        return self._now().strftime("%Y-%m-%dT%H:%M:%SZ")

    def _now_iso(self) -> str:
        """Alias for _iso_now() — used by reinforce() for readability."""
        return self._iso_now()

    def _strip_trailer(self, content: str) -> str:
        """Remove the lifecycle trailer block from content and return the base text.

        Returns the content with the trailer stripped, plus a trailing newline
        so that ``_format_trailer`` can be concatenated directly.

        Args:
            content: Raw observation content, may or may not have a trailer.

        Returns:
            Content without the trailer block, ending with a newline.
        """
        stripped = _TRAILER_RE.sub("", content).rstrip()
        return stripped + "\n" if stripped else ""

    def _format_trailer(self, trailer: dict[str, Any]) -> str:
        """Serialize a trailer dict as the lifecycle XML block.

        Args:
            trailer: Lifecycle metadata dict.

        Returns:
            Formatted ``<engram-lifecycle>...</engram-lifecycle>`` block string.
        """
        trailer_json = json.dumps(trailer, separators=(",", ":"))
        return f"<engram-lifecycle>\n{trailer_json}\n</engram-lifecycle>"

    def _append_trailer_json(self, content: str, trailer: dict[str, Any]) -> str:
        """Append a trailer block to content (handles trailing whitespace)."""
        trailer_json = json.dumps(trailer, separators=(",", ":"))
        return f"{content.rstrip()}\n<engram-lifecycle>\n{trailer_json}\n</engram-lifecycle>"


# ---------------------------------------------------------------------------
# ISO-8601 parsing helper (compatible with Python 3.10 and 3.11+)
# ---------------------------------------------------------------------------


def _parse_iso8601_utc(timestamp: str) -> datetime:
    """Parse an ISO-8601 UTC timestamp string to a naive UTC datetime.

    Handles both ``2026-04-27T15:30:00Z`` (Python 3.10 fromisoformat cannot
    parse the trailing Z) and RFC-3339 variants.

    Args:
        timestamp: ISO-8601 string, potentially ending in ``Z``.

    Returns:
        Naive datetime in UTC.

    Raises:
        ValueError: If the string cannot be parsed.
    """
    ts = timestamp.strip()
    if ts.endswith("Z"):
        ts = ts[:-1]
    return datetime.fromisoformat(ts)


# ---------------------------------------------------------------------------
# CLI entry point for hook usage: python3 lib/engram_lifecycle.py reinforce <id>
# ---------------------------------------------------------------------------


def _cli_main() -> None:  # pragma: no cover
    if len(sys.argv) < 3 or sys.argv[1] != "reinforce":
        print(f"Usage: {sys.argv[0]} reinforce <observation_id>", file=sys.stderr)
        sys.exit(1)
    obs_id = sys.argv[2]
    lc = EngramLifecycle()
    ok = lc.reinforce(obs_id)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    _cli_main()
