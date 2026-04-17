"""Engram client — structured read/write API for trusted internal callers.

FOR (use case)
--------------
Use this module when **internal, trusted code** needs to search, fetch, or save
observations programmatically and wants machine-parseable results (``dict | None``
or ``list[dict]``).  All CLI commands include ``--json`` so callers can parse
structured output without string-matching.  If you need search or structured
persistence from a hook or library, this is the right module.

CONSUMERS (as of 2026-04-17)
-----------------------------
- ``lib/memory.py:19`` — ``mem_search``, ``mem_get_observation``, and ``mem_save``
  helper functions used by the orchestrator memory layer.
- ``hooks/inject-phase-context.sh`` — searches for discovery/bugfix/feedback
  observations to inject into sub-agent context.
- ``hooks/subagent-context-injector.sh`` — searches for agent sidecar context.
- ``tests/unit/test_engram_client.py`` — full characterization test suite (46 tests).

CONTRACT
--------
- All three functions **never raise** — errors produce empty/None returns silently.
- ``search_observations()`` returns ``list[dict]`` (empty on any failure).
- ``get_observation()`` returns ``dict | None`` (None on any failure).
- ``save_observation()`` returns ``dict | None`` (None on any failure).
- All CLI commands include ``--json``; output is parsed as JSON, not returned as
  a raw string.  Callers receive structured data, not human-readable text.
- Binary-missing (``FileNotFoundError``) is silently swallowed — callers see empty
  results, not an error, enabling graceful degradation when engram is not installed.

NOT (cross-reference)
----------------------
This module is **not** for content from untrusted sources (agent output, user input,
LLM-generated text).  For those, use ``lib.safe_engram`` (see ``lib/safe_engram.py``),
which runs ``MemoryScanner`` before any write and returns a ``SafeEngramResult``
dataclass with human-readable ``engram_output`` strings (no ``--json``).

The two modules have **zero overlapping callers** — the boundary is intentional.
Merging them would require either adding scanner overhead to every internal read,
or exposing ``--json`` output to MCP clients, breaking the user-facing string contract
in ``mcp-server/cos_mcp.py``.

ADR references: ``docs/architecture/adrs/026-r2-r3-design-review.md`` (R3 findings)
               ``docs/architecture/adrs/026a-decisions.md`` (D3.1 decision)
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
