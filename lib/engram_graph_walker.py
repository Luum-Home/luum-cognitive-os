# SCOPE: both
"""Engram graph walker — Phase 3 of ADR-071.

FOR (use case)
--------------
After ``EngramLifecycle.search()`` returns initial results, this module walks
the ``memory_relations`` table in the SQLite database to discover connected
observations via typed edges (supersedes, related, compatible, etc.) and
merges them into the ranked result set.

Traversal is bounded at 2 hops by default to prevent combinatorial explosion.
Only read-only SQLite access is used — the module NEVER writes to the database.

ADR reference: ``docs/adrs/ADR-071-engram-lifecycle-evolution.md``

NOT (cross-reference)
----------------------
This module reads SQLite directly because the ``memory_relations`` table is
NOT exposed via the engram HTTP API — the ``mem_judge`` endpoint is only
available via the MCP server, not via the HTTP REST interface at port 7437.
For safety, the database connection uses ``mode=ro`` URI parameter.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import sys
from collections import deque
from typing import Any

_log = logging.getLogger(__name__)

_LIB_DIR = os.path.dirname(os.path.abspath(__file__))
if _LIB_DIR not in sys.path:
    sys.path.insert(0, os.path.dirname(_LIB_DIR))

from lib import engram_http_client as _http_mod_default

_ENGRAM_DATA_DIR = os.environ.get("ENGRAM_DATA_DIR", os.path.expanduser("~/.engram"))
_DEFAULT_DB_PATH = os.path.join(_ENGRAM_DATA_DIR, "engram.db")

_RELATIONS_SCHEMA = """
CREATE TABLE IF NOT EXISTS memory_relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_id TEXT NOT NULL UNIQUE,
    source_id TEXT,
    target_id TEXT,
    relation TEXT NOT NULL DEFAULT 'pending',
    reason TEXT,
    evidence TEXT,
    confidence REAL,
    judgment_status TEXT NOT NULL DEFAULT 'pending',
    superseded_at TEXT,
    superseded_by_relation_id INTEGER,
    created_at TEXT,
    updated_at TEXT
)
"""

_MAX_VISITED = 10_000


class EngramGraphWalker:
    """BFS over the memory_relations graph to extend search coverage.

    Reads ``memory_relations`` and ``observations`` tables from the SQLite DB
    in read-only mode.  Never writes.

    Args:
        db_path:            Path to the engram SQLite database.
                            Defaults to ``~/.engram/engram.db`` (or
                            ``$ENGRAM_DATA_DIR/engram.db``).
        http_client_module: Injectable HTTP client module for tests.
        max_depth:          Default BFS depth limit.
    """

    DEFAULT_MAX_DEPTH: int = 2
    DEFAULT_GRAPH_BOOST: float = 0.3
    DEFAULT_ALPHA_GRAPH: float = 0.2

    def __init__(
        self,
        db_path: str | None = None,
        http_client_module: Any = None,
        max_depth: int = DEFAULT_MAX_DEPTH,
    ) -> None:
        self._db_path = db_path or _DEFAULT_DB_PATH
        self._http = http_client_module or _http_mod_default
        self.max_depth = max_depth

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def walk(
        self,
        sync_ids: list[str],
        max_depth: int | None = None,
    ) -> dict[str, dict[str, Any]]:
        """BFS over memory_relations starting from *sync_ids*.

        Args:
            sync_ids:  Starting observation sync_ids.
            max_depth: Override instance max_depth for this call.

        Returns:
            Dict mapping neighbor sync_id → ``{hops: int, relation_path: list[str]}``.
            Starting sync_ids are excluded from the result.
            Rejected relations (``judgment_status='rejected'``) are skipped.
            Returns empty dict when the database does not exist or any error occurs.
        """
        depth = max_depth if max_depth is not None else self.max_depth
        if not sync_ids:
            return {}

        try:
            return self._bfs(sync_ids, depth)
        except Exception as exc:
            _log.debug("EngramGraphWalker.walk failed: %s", exc)
            return {}

    def fetch_observations_by_sync_id(
        self, sync_ids: list[str]
    ) -> list[dict[str, Any]]:
        """Fetch observation rows by sync_id directly from SQLite.

        Reads the ``observations`` table and returns rows matching *sync_ids*.
        Falls back to empty list on any error.

        Args:
            sync_ids: List of sync_id strings to retrieve.

        Returns:
            List of observation dicts.
        """
        if not sync_ids:
            return []
        try:
            conn = self._open_db_readonly()
            if conn is None:
                return []
            with conn:
                placeholders = ",".join("?" * len(sync_ids))
                rows = conn.execute(
                    f"SELECT id, sync_id, title, content, type, topic_key, "
                    f"project, created_at FROM observations WHERE sync_id IN ({placeholders})",
                    sync_ids,
                ).fetchall()
            conn.close()
            results = []
            for row in rows:
                results.append({
                    "id": row[0],
                    "sync_id": row[1],
                    "title": row[2],
                    "content": row[3],
                    "type": row[4],
                    "topic_key": row[5],
                    "project": row[6],
                    "created_at": row[7],
                })
            return results
        except Exception as exc:
            _log.debug("fetch_observations_by_sync_id failed: %s", exc)
            return []

    def merge_into_results(
        self,
        base_results: list[dict[str, Any]],
        neighbors: dict[str, dict[str, Any]],
        graph_boost: float = DEFAULT_GRAPH_BOOST,
        alpha_graph: float = DEFAULT_ALPHA_GRAPH,
    ) -> list[dict[str, Any]]:
        """Merge graph neighbors into the base result list and re-rank.

        For base results, applies:
            final = original_score * (1 - alpha_graph)

        For graph-only neighbors, assigns:
            adjusted_score = graph_boost

        Then merges and sorts descending by final score.

        Args:
            base_results: Ranked list from lifecycle search (may have ``adjusted_score``).
            neighbors:    Output of ``walk()``.
            graph_boost:  Score assigned to graph-only hits.
            alpha_graph:  Graph contribution weight for base results.

        Returns:
            Merged, re-ranked list of observation dicts.
        """
        base_sync_ids: set[str] = set()
        enriched: list[dict[str, Any]] = []
        for obs in base_results:
            sid = obs.get("sync_id", "")
            base_sync_ids.add(sid)
            original = float(obs.get("adjusted_score", obs.get("score", 1.0)))
            final = original * (1.0 - alpha_graph) + graph_boost * alpha_graph
            enriched.append({**obs, "final_score": final})

        neighbor_sync_ids = [s for s in neighbors if s not in base_sync_ids]
        if neighbor_sync_ids:
            fetched = self.fetch_observations_by_sync_id(neighbor_sync_ids)
            for obs in fetched:
                enriched.append({
                    **obs,
                    "adjusted_score": graph_boost,
                    "final_score": graph_boost,
                    "graph_only": True,
                    "hops": neighbors.get(obs.get("sync_id", ""), {}).get("hops", 1),
                })

        enriched.sort(key=lambda x: x.get("final_score", 0.0), reverse=True)
        return enriched

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _open_db_readonly(self) -> sqlite3.Connection | None:
        """Open the SQLite DB in read-only mode.

        Returns None when the file does not exist or cannot be opened.
        Never raises.
        """
        if not os.path.isfile(self._db_path):
            _log.debug("EngramGraphWalker: DB not found at %s", self._db_path)
            return None
        try:
            uri = f"file:{self._db_path}?mode=ro"
            conn = sqlite3.connect(uri, uri=True)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as exc:
            _log.debug("EngramGraphWalker: cannot open DB %s: %s", self._db_path, exc)
            return None

    def _bfs(
        self, start_sync_ids: list[str], max_depth: int
    ) -> dict[str, dict[str, Any]]:
        """BFS implementation over memory_relations.

        Builds the neighbor graph by reading edges from SQLite.
        """
        conn = self._open_db_readonly()
        if conn is None:
            return {}

        origin_set = set(start_sync_ids)
        visited: set[str] = set(start_sync_ids)
        result: dict[str, dict[str, Any]] = {}

        queue: deque[tuple[str, int, list[str]]] = deque()
        for sid in start_sync_ids:
            queue.append((sid, 0, []))

        try:
            while queue:
                current_id, current_depth, path_so_far = queue.popleft()
                if current_depth >= max_depth:
                    continue
                if len(visited) >= _MAX_VISITED:
                    break

                edges = self._fetch_edges(conn, current_id)
                for neighbor_id, relation in edges:
                    if not neighbor_id or neighbor_id in visited:
                        continue
                    visited.add(neighbor_id)
                    hops = current_depth + 1
                    relation_path = path_so_far + [relation]
                    if neighbor_id not in origin_set:
                        result[neighbor_id] = {
                            "hops": hops,
                            "relation_path": relation_path,
                        }
                    queue.append((neighbor_id, hops, relation_path))
        finally:
            conn.close()

        return result

    def _fetch_edges(
        self, conn: sqlite3.Connection, sync_id: str
    ) -> list[tuple[str, str]]:
        """Return (neighbor_sync_id, relation) pairs for *sync_id*.

        Fetches both outgoing (source_id = sync_id → target_id) and
        incoming (target_id = sync_id → source_id) edges, excluding
        rejected judgments.
        """
        try:
            rows = conn.execute(
                """
                SELECT target_id, relation FROM memory_relations
                WHERE source_id = ?
                  AND judgment_status != 'rejected'
                  AND target_id IS NOT NULL
                  AND target_id != ''
                UNION ALL
                SELECT source_id, relation FROM memory_relations
                WHERE target_id = ?
                  AND judgment_status != 'rejected'
                  AND source_id IS NOT NULL
                  AND source_id != ''
                """,
                (sync_id, sync_id),
            ).fetchall()
            return [(str(r[0]), str(r[1])) for r in rows]
        except Exception as exc:
            _log.debug("_fetch_edges failed for %s: %s", sync_id, exc)
            return []
