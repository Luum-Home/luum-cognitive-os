"""SQLite-backed nonce dedup store for grant tokens (ADR-260 §2).

Closes the replay gap left open by the reference pattern. Each successful
verify of a grant records its nonce; subsequent verifies of the same nonce
are rejected until eviction.

Schema:
    nonces(nonce TEXT PRIMARY KEY, exp INTEGER)

Defaults:
    db path: .cognitive-os/state/cosd-nonce-store.db (mode 0600)
    max:     10000 live nonces; eviction triggered when row count > max/2

Pattern adopted from external pattern (see ADR-259) (clean-room rewrite).
Refs: .private/external-pattern-research/comparison-2026-05-10.md
Source-pattern: AnnexD::§1.grant-signing (luum addition — not in reference)
License: Apache-2.0 modified (BSL-like). No source code copied.
"""
from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path
from typing import Optional


DEFAULT_DB_PATH = Path(".cognitive-os/state/cosd-nonce-store.db")
DEFAULT_MAX = 10000


class GrantNonceStore:
    """SQLite-backed nonce deduplication for grant tokens."""

    def __init__(
        self,
        db_path: Optional[Path] = None,
        *,
        max_rows: int = DEFAULT_MAX,
    ) -> None:
        self._db_path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
        self._max = int(max_rows)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        # touch + chmod the db file so it lands with 0600 even on first connect
        first_create = not self._db_path.exists()
        self._conn = sqlite3.connect(str(self._db_path), isolation_level=None)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS nonces (nonce TEXT PRIMARY KEY, exp INTEGER NOT NULL)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_nonces_exp ON nonces(exp)"
        )
        if first_create:
            try:
                os.chmod(self._db_path, 0o600)
            except OSError:
                pass

    # ------------------------------------------------------------------

    def mark_seen(self, nonce: str, exp: int) -> bool:
        """Record a nonce. Returns True if newly recorded, False if duplicate."""
        try:
            self._conn.execute(
                "INSERT INTO nonces (nonce, exp) VALUES (?, ?)",
                (nonce, int(exp)),
            )
        except sqlite3.IntegrityError:
            return False
        self._maybe_evict()
        return True

    # Alias used by lib/cosd_grant.verify_token's nonce_store contract.
    def check_and_record(self, nonce: str, exp: int) -> bool:
        return self.mark_seen(nonce, exp)

    def cleanup_expired(self) -> int:
        """Delete rows where exp <= now. Returns count deleted."""
        return self.evict_expired()

    def evict_expired(self) -> int:
        now = int(time.time())
        cur = self._conn.execute("DELETE FROM nonces WHERE exp <= ?", (now,))
        return int(cur.rowcount or 0)

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass

    # ------------------------------------------------------------------

    def _maybe_evict(self) -> None:
        cur = self._conn.execute("SELECT COUNT(*) FROM nonces")
        row = cur.fetchone()
        count = int(row[0] if row else 0)
        if count > self._max // 2:
            self.evict_expired()


__all__ = ["GrantNonceStore"]
