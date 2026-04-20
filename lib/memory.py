# SCOPE: os-only
"""Memory access stub — thin interface to the engram observation store.

Provides mem_search() and related helpers used by Python modules that
need to query the agent memory system without going through the engram
CLI directly.

Primary consumers:
  - lib/agent_context_injector.py (searches for prior context before injecting)

When engram is unavailable, all functions return empty results.
For write operations with untrusted content, use lib.safe_engram instead.
"""

from __future__ import annotations

from typing import Any

try:
    from lib.engram_client import search_observations, get_observation, save_observation
    _ENGRAM_AVAILABLE = True
except ImportError:
    _ENGRAM_AVAILABLE = False

    def search_observations(query: str, **kwargs: Any) -> list[dict[str, Any]]:  # type: ignore[misc]
        return []

    def get_observation(observation_id: Any, **kwargs: Any) -> dict[str, Any] | None:  # type: ignore[misc]
        return None

    def save_observation(title: str, content: str, **kwargs: Any) -> dict[str, Any] | None:  # type: ignore[misc]
        return None


def mem_search(
    query: str,
    *,
    project: str = "",
    limit: int = 5,
    max_results: int | None = None,
    type_filter: str = "",
) -> list[dict[str, Any]]:
    """Search engram observations and return matching results.

    Args:
        query:        Free-text search query.
        project:      Optional project scope.
        limit:        Maximum number of results (alias: max_results).
        max_results:  Alias for *limit* (agent_context_injector compatibility).
        type_filter:  Filter by observation type (e.g. "discovery").

    Returns:
        List of observation dicts with at minimum:
          - title (str)
          - type (str)
          - content (str)
    """
    effective_limit = max_results if max_results is not None else limit
    return search_observations(
        query,
        limit=effective_limit,
        project=project,
        type_filter=type_filter,
    )


def mem_get(observation_id: int | str) -> dict[str, Any] | None:
    """Fetch a single observation by ID. Returns None if not found."""
    return get_observation(observation_id)


def mem_save(
    title: str,
    content: str,
    *,
    type_: str = "manual",
    topic_key: str = "",
    project: str = "",
) -> dict[str, Any] | None:
    """Save an observation to engram. Returns the created observation or None."""
    return save_observation(
        title,
        content,
        type_=type_,
        topic_key=topic_key,
        project=project,
    )
