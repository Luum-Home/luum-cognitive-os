# SCOPE: both
"""Engram Crystallization pipeline — Phase 2 of ADR-071.

FOR (use case)
--------------
When multiple observations accumulate under the same ``topic_key``, this module
synthesises a digest observation (``type=pattern``) that consolidates their content.
This implements the "working memory → semantic memory" consolidation tier described
in the LLM Wiki v2 research backing ADR-071.

Trigger thresholds (either condition fires crystallisation):
  - N ≥ 5 observations with the same ``topic_key`` within 30 days, OR
  - N ≥ 10 total observations with the same ``topic_key`` regardless of age.

Crystallisation v1 is intentionally deterministic — NO LLM call.
The digest is constructed from constituent observation titles and content via
text deduplication.  A future phase may upgrade to LLM synthesis.

ADR reference: ``docs/adrs/ADR-071-engram-lifecycle-evolution.md``

NOT (cross-reference)
----------------------
This module does NOT modify constituent observations — the engram HTTP API does
not expose the ``mem_judge`` relation endpoint.  Instead, the digest trailer
carries ``crystallized: true`` and ``superseded_obs_ids`` for downstream consumers.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Callable

_LIB_DIR = os.path.dirname(os.path.abspath(__file__))
if _LIB_DIR not in sys.path:
    sys.path.insert(0, os.path.dirname(_LIB_DIR))

from lib import engram_client as _cli_mod_default
from lib import engram_http_client as _http_mod_default
from lib.engram_lifecycle import EngramLifecycle, _parse_iso8601_utc

_MAX_DIGEST_CHARS = 4000
_CRYSTALLIZED_SUFFIX = "/crystallized"


class EngramCrystallizer:
    """Detect over-represented topic_keys and synthesise digest observations.

    All public methods follow the never-raise contract: errors yield empty
    results or None instead of propagating exceptions.

    Args:
        lifecycle:          Optional EngramLifecycle instance. Created with
                            default settings when not supplied.
        http_client_module: Injectable HTTP client module (for testing).
        cli_client_module:  Injectable CLI client module (for testing).
        now:                Injectable clock callable returning UTC datetime
                            (for deterministic testing).
    """

    THRESHOLD_RECENT_COUNT: int = 5
    THRESHOLD_RECENT_DAYS: int = 30
    THRESHOLD_TOTAL_COUNT: int = 10

    def __init__(
        self,
        lifecycle: EngramLifecycle | None = None,
        http_client_module: Any = None,
        cli_client_module: Any = None,
        now: Callable[[], datetime] | None = None,
        _save_override: Any = None,
    ) -> None:
        self._lifecycle = lifecycle or EngramLifecycle()
        self._http = http_client_module or _http_mod_default
        self._cli = cli_client_module or _cli_mod_default
        self._now: Callable[[], datetime] = now or (
            lambda: datetime.now(timezone.utc).replace(tzinfo=None)
        )
        self._save_override = _save_override

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def candidates(self, project: str | None = None) -> list[dict[str, Any]]:
        """Return topic_keys that meet crystallisation thresholds.

        Fetches recent observations and groups by ``topic_key``.  Because engram
        deduplicates observations with the same ``topic_key`` into a single
        observation (incrementing ``revision_count``), this method treats
        ``revision_count`` as a proxy for the number of times information was
        saved under that topic_key.  A ``revision_count`` ≥ 5 on a recent obs
        satisfies the "recent count" threshold; ≥ 10 satisfies the total
        threshold.

        Args:
            project: Optional project scope.

        Returns:
            List of dicts:
            ``{topic_key, count_recent, count_total, obs_ids}``
        """
        try:
            all_obs = self._search_all(project=project)
        except Exception:
            return []

        now = self._now()
        cutoff_days = self.THRESHOLD_RECENT_DAYS

        grouped: dict[str, list[dict[str, Any]]] = {}
        for obs in all_obs:
            tk = (obs.get("topic_key") or "").strip()
            if not tk:
                continue
            if tk.endswith(_CRYSTALLIZED_SUFFIX):
                continue
            grouped.setdefault(tk, []).append(obs)

        results = []
        for topic_key, obs_list in grouped.items():
            revision_total = sum(
                int(obs.get("revision_count") or 1) for obs in obs_list
            )
            count_total = max(len(obs_list), revision_total)

            count_recent = 0
            for obs in obs_list:
                rev = int(obs.get("revision_count") or 1)
                last_seen_str = (
                    obs.get("last_seen_at")
                    or obs.get("updated_at")
                    or obs.get("created_at", "")
                )
                if last_seen_str:
                    try:
                        last_seen = _parse_iso8601_utc(last_seen_str)
                        age_days = (now - last_seen).total_seconds() / 86400.0
                        if age_days <= cutoff_days:
                            count_recent += rev
                    except Exception:
                        count_recent += rev
                else:
                    count_recent += rev

            meets_threshold = (
                count_recent >= self.THRESHOLD_RECENT_COUNT
                or count_total >= self.THRESHOLD_TOTAL_COUNT
            )
            if not meets_threshold:
                continue

            crystallized_key = topic_key + _CRYSTALLIZED_SUFFIX
            if self._digest_exists(crystallized_key, project=project):
                continue

            results.append(
                {
                    "topic_key": topic_key,
                    "count_recent": count_recent,
                    "count_total": count_total,
                    "obs_ids": [obs.get("sync_id") or str(obs.get("id", "")) for obs in obs_list],
                }
            )

        return results

    def crystallize(
        self,
        topic_key: str,
        project: str | None = None,
        force: bool = False,
    ) -> dict[str, Any] | None:
        """Synthesise and save a digest observation for *topic_key*.

        Args:
            topic_key: The source topic_key to crystallise.
            project:   Optional project scope.
            force:     When True, create a new digest even if one already exists.

        Returns:
            The new observation dict on success, or None if:
            - already crystallised and force=False
            - no constituent observations found
            - save fails
        """
        crystallized_key = topic_key + _CRYSTALLIZED_SUFFIX

        if not force and self._digest_exists(crystallized_key, project=project):
            return None

        observations = self._fetch_observations_for_topic(topic_key, project=project)
        if not observations:
            return None

        content = self.synthesize_content(observations)

        trailer_fields: dict[str, Any] = {
            "confidence": 0.85,
            "last_reinforced": self._iso_now(),
            "reinforcement_count": 0,
            "decay_class": "pattern",
            "crystallized": True,
            "superseded_obs_ids": [
                obs.get("sync_id") or str(obs.get("id", "")) for obs in observations
            ],
        }
        trailer_block = (
            "<engram-lifecycle>\n"
            + json.dumps(trailer_fields, separators=(",", ":"))
            + "\n</engram-lifecycle>"
        )
        full_content = content.rstrip() + "\n" + trailer_block

        title = f"Crystallized pattern: {topic_key}"
        kwargs: dict[str, Any] = {
            "type_": "pattern",
            "topic_key": crystallized_key,
        }
        if project:
            kwargs["project"] = project

        if self._save_override is not None:
            result = self._save_override(title, full_content, **kwargs)
        elif self._cli is not _cli_mod_default:
            result = self._cli.save_observation(title, full_content, **kwargs)
        else:
            result = self._save_observation(title, full_content, **kwargs)
        return result

    def synthesize_content(self, observations: list[dict[str, Any]]) -> str:
        """Deterministically synthesise a digest from constituent observations.

        Pure function — same input always produces same output.
        Cap at 4000 chars; truncate with ``...[truncated]`` when exceeded.

        Args:
            observations: List of observation dicts with at least
                          ``title``, ``content``, ``id``/``sync_id``,
                          ``created_at`` keys.

        Returns:
            Synthesised digest string.
        """
        n = len(observations)
        header = f"Crystallized digest of {n} observation{'s' if n != 1 else ''}"

        seen_lines: set[str] = set()
        body_parts: list[str] = []
        for obs in observations:
            raw_content = obs.get("content", "") or ""
            from lib.engram_lifecycle import _TRAILER_RE
            base_content = _TRAILER_RE.sub("", raw_content).strip()
            for line in base_content.splitlines():
                stripped = line.strip()
                if stripped and stripped not in seen_lines:
                    seen_lines.add(stripped)
                    body_parts.append(stripped)

        obs_list_lines = []
        for obs in observations:
            obs_id = obs.get("sync_id") or str(obs.get("id", "?"))
            obs_title = obs.get("title", "(untitled)")
            created = obs.get("created_at", "")
            obs_list_lines.append(f"- [{obs_id}] {obs_title} ({created})")

        body_text = "\n".join(body_parts)
        obs_index = "\n".join(obs_list_lines)

        full = f"{header}\n\n{body_text}\n\nConstituent observations ({n}):\n{obs_index}"

        if len(full) > _MAX_DIGEST_CHARS:
            cutoff = _MAX_DIGEST_CHARS - len("\n...[truncated]")
            full = full[:cutoff] + "\n...[truncated]"

        return full

    def crystallize_all(self, project: str | None = None) -> list[dict[str, Any]]:
        """Crystallise all eligible topic_keys.

        Short-circuits when there are no candidates (latency budget: ≤500ms
        at session end when the candidate list is empty).

        Args:
            project: Optional project scope.

        Returns:
            List of newly created digest observation dicts (may be empty).
        """
        candidate_list = self.candidates(project=project)
        if not candidate_list:
            return []

        digests = []
        for candidate in candidate_list:
            result = self.crystallize(candidate["topic_key"], project=project)
            if result is not None:
                digests.append(result)
        return digests

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _save_observation(
        self,
        title: str,
        content: str,
        type_: str = "pattern",
        topic_key: str = "",
        project: str | None = None,
    ) -> dict[str, Any] | None:
        """Save an observation using the engram CLI positional-arg interface.

        The standard ``engram_client.save_observation`` uses ``--title`` /
        ``--content`` flags which this version of the engram binary does NOT
        support.  This method uses the correct positional syntax:
        ``engram save <title> <content> --type TYPE --topic TOPIC_KEY``.
        Falls back to ``self._cli.save_observation`` for injected mocks in tests.
        """
        import subprocess
        import json as _json
        import os as _os

        engram_bin = _os.environ.get("ENGRAM_BIN", "engram")
        cmd = [engram_bin, "save", title, content, "--type", type_]
        if topic_key:
            cmd.extend(["--topic", topic_key])
        if project:
            cmd.extend(["--project", project])

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if proc.returncode != 0:
                result = self._cli.save_observation(
                    title, content, type_=type_, topic_key=topic_key or "",
                    project=project or "",
                )
                return result
            output = proc.stdout.strip()
            if not output:
                return {"saved": True, "title": title}
            try:
                data = _json.loads(output)
                return data if isinstance(data, dict) else {"saved": True, "raw": output}
            except Exception:
                return {"saved": True, "raw": output}
        except FileNotFoundError:
            return self._cli.save_observation(
                title, content, type_=type_, topic_key=topic_key or "",
                project=project or "",
            )
        except Exception:
            return self._cli.save_observation(
                title, content, type_=type_, topic_key=topic_key or "",
                project=project or "",
            )

    def _iso_now(self) -> str:
        return self._now().strftime("%Y-%m-%dT%H:%M:%SZ")

    def _search_all(self, project: str | None = None) -> list[dict[str, Any]]:
        """Fetch a broad sample of recent observations via the HTTP API.

        Prefers the ``/observations/recent`` endpoint which returns all
        observations without requiring a query string.  Falls back to
        ``search_observations`` when the recent endpoint is unavailable.
        Falls back to empty list when the HTTP daemon is not available.
        """
        if not self._http.is_available():
            return []

        try:
            recent = self._http.get_recent(limit=500, project=project)
            if isinstance(recent, list) and recent:
                return recent
        except Exception:
            pass

        kwargs: dict[str, Any] = {"limit": 500}
        if project:
            kwargs["project"] = project
        results = self._http.search_observations("the", **kwargs)
        if not results:
            results = self._http.search_observations("content", **kwargs)
        return results if isinstance(results, list) else []

    def _digest_exists(self, crystallized_key: str, project: str | None = None) -> bool:
        """Return True if a digest with this crystallized topic_key already exists."""
        try:
            kwargs: dict[str, Any] = {"limit": 1}
            if project:
                kwargs["project"] = project
            results = self._http.search_observations(crystallized_key, **kwargs)
            if not isinstance(results, list):
                return False
            for obs in results:
                if obs.get("topic_key") == crystallized_key:
                    return True
            return False
        except Exception:
            return False

    def _fetch_observations_for_topic(
        self, topic_key: str, project: str | None = None
    ) -> list[dict[str, Any]]:
        """Fetch all observations matching the given topic_key.

        Because engram deduplicates by topic_key (merging multiple saves into
        one observation with an incremented ``revision_count``), this may return
        as few as one observation even when the topic had many saves.  The
        returned list is sufficient to synthesise a meaningful digest.
        """
        try:
            kwargs: dict[str, Any] = {"limit": 500}
            if project:
                kwargs["project"] = project
            results = self._http.search_observations(topic_key, **kwargs)
            if not isinstance(results, list):
                return []
            matching = [
                obs for obs in results
                if (obs.get("topic_key") or "").strip() == topic_key
                and not (obs.get("topic_key") or "").endswith(_CRYSTALLIZED_SUFFIX)
            ]
            if not matching:
                recent = self._http.get_recent(limit=500)
                if isinstance(recent, list):
                    matching = [
                        obs for obs in recent
                        if (obs.get("topic_key") or "").strip() == topic_key
                        and not (obs.get("topic_key") or "").endswith(_CRYSTALLIZED_SUFFIX)
                    ]
            return matching
        except Exception:
            return []
