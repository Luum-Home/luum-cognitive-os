"""Engram client stub — thin wrapper around the engram CLI for observation search.

This module provides a Python interface to the engram memory system.
It wraps the engram CLI via subprocess. When engram is unavailable,
all functions degrade gracefully (return empty results, log to stderr).

Primary consumers:
  - hooks/inject-phase-context.sh (searches for discovery/bugfix/feedback memories)
  - hooks/subagent-context-injector.sh (searches for agent sidecar context)
"""

from __future__ import annotations

import json
import os
import subprocess
from typing import Any

# Path to engram binary — override via ENGRAM_BIN env var
_ENGRAM_BIN = os.environ.get("ENGRAM_BIN", "engram")


def search_observations(
    query: str,
    *,
    limit: int = 5,
    type_filter: str = "",
    project: str = "",
    timeout: int = 5,
) -> list[dict[str, Any]]:
    """Search engram observations matching *query*.

    Returns a list of observation dicts with keys:
      id, title, content, type, topic_key, project, created_at

    Returns an empty list if engram is unavailable or the query fails.

    Args:
        query:        Free-text search query.
        limit:        Maximum number of results to return.
        type_filter:  Optional observation type to filter by
                      (e.g. ``"discovery"``, ``"bugfix"``).
        project:      Optional project scope for the search.
        timeout:      Subprocess timeout in seconds.
    """
    cmd = [_ENGRAM_BIN, "search", "--json", "--limit", str(limit), query]
    if type_filter:
        cmd.extend(["--type", type_filter])
    if project:
        cmd.extend(["--project", project])

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if proc.returncode != 0:
            return []

        output = proc.stdout.strip()
        if not output:
            return []

        data = json.loads(output)
        if isinstance(data, list):
            return data[:limit]
        if isinstance(data, dict) and "results" in data:
            return data["results"][:limit]
        return []

    except FileNotFoundError:
        # engram binary not installed — silent no-op
        return []
    except subprocess.TimeoutExpired:
        return []
    except (json.JSONDecodeError, ValueError):
        return []
    except Exception:
        return []


def get_observation(observation_id: int | str, *, timeout: int = 5) -> dict[str, Any] | None:
    """Fetch a single observation by its ID.

    Returns the observation dict or ``None`` if not found / unavailable.
    """
    cmd = [_ENGRAM_BIN, "get", "--json", str(observation_id)]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if proc.returncode != 0:
            return None

        output = proc.stdout.strip()
        if not output:
            return None

        data = json.loads(output)
        return data if isinstance(data, dict) else None

    except FileNotFoundError:
        return None
    except subprocess.TimeoutExpired:
        return None
    except (json.JSONDecodeError, ValueError):
        return None
    except Exception:
        return None


def save_observation(
    title: str,
    content: str,
    *,
    type_: str = "manual",
    topic_key: str = "",
    project: str = "",
    timeout: int = 10,
) -> dict[str, Any] | None:
    """Save a new observation to engram.

    Returns the created observation dict, or ``None`` on failure.
    Prefer :func:`lib.safe_engram.safe_save` when content may be
    untrusted (it runs MemoryScanner first).
    """
    cmd = [
        _ENGRAM_BIN, "save",
        "--json",
        "--title", title,
        "--content", content,
        "--type", type_,
    ]
    if topic_key:
        cmd.extend(["--topic-key", topic_key])
    if project:
        cmd.extend(["--project", project])

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if proc.returncode != 0:
            return None

        output = proc.stdout.strip()
        if not output:
            return None

        data = json.loads(output)
        return data if isinstance(data, dict) else None

    except FileNotFoundError:
        return None
    except subprocess.TimeoutExpired:
        return None
    except (json.JSONDecodeError, ValueError):
        return None
    except Exception:
        return None
