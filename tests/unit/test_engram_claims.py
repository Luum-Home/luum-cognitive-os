"""Unit tests for lib/engram_claims.py (P5.1).

All engram I/O is mocked via the _save_fn / _search_fn injection points.
No live engram daemon is required.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

# Ensure lib/ is on sys.path so the symlinked module resolves.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT / "lib") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "lib"))

import engram_claims  # noqa: E402 — after path setup


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class FakeEngramStore:
    """In-memory store that mimics engram's save/search behavior."""

    def __init__(self) -> None:
        # Maps topic_key -> latest saved content string
        self._store: dict[str, str] = {}
        self.save_calls: list[dict] = []

    def save(self, title: str, content: str, *, type_: str = "architecture",
             topic_key: str = "", project: str = "") -> dict[str, Any] | None:
        self.save_calls.append({"title": title, "content": content,
                                 "topic_key": topic_key, "project": project})
        if topic_key:
            self._store[topic_key] = content
        return {"id": 1, "title": title, "content": content, "topic_key": topic_key}

    def search(self, query: str, *, limit: int = 5,
               project: str = "") -> list[dict[str, Any]]:
        results = []
        for tk, content in self._store.items():
            if query in tk or query in content:
                results.append({
                    "id": 1,
                    "title": tk,
                    "content": content,
                    "topic_key": tk,
                })
        return results[:limit]


@pytest.fixture(autouse=True)
def patch_engram(monkeypatch):
    """Replace module-level _save_fn / _search_fn with a FakeEngramStore."""
    store = FakeEngramStore()
    monkeypatch.setattr(engram_claims, "_save_fn", store.save)
    monkeypatch.setattr(engram_claims, "_search_fn", store.search)
    return store


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

class TestClaimTask:
    def test_claim_creates_record(self, patch_engram):
        """claim_task returns a dict with expected keys."""
        record = engram_claims.claim_task("T123", "session-A")

        assert record["task_id"] == "T123"
        assert record["session_id"] == "session-A"
        assert record["status"] == "claimed"
        assert "claimed_at" in record

    def test_claim_with_optional_fields(self, patch_engram):
        """claim_task stores expected_files and fingerprint."""
        record = engram_claims.claim_task(
            "T456", "session-B",
            expected_files=["lib/foo.py"],
            fingerprint="abc123",
        )
        assert record["expected_files"] == ["lib/foo.py"]
        assert record["fingerprint"] == "abc123"

    def test_claim_saves_to_engram(self, patch_engram):
        """claim_task invokes _save_fn with the correct topic_key."""
        engram_claims.claim_task("T789", "session-C")
        assert any(
            c["topic_key"] == "claims/T789"
            for c in patch_engram.save_calls
        )


class TestFindClaim:
    def test_find_returns_none_for_unknown_task(self, patch_engram):
        """find_claim returns None when no claim exists."""
        result = engram_claims.find_claim("nonexistent-task")
        assert result is None

    def test_find_claim_roundtrip(self, patch_engram):
        """claim then find returns the same record."""
        engram_claims.claim_task("T001", "session-X")
        found = engram_claims.find_claim("T001")

        assert found is not None
        assert found["task_id"] == "T001"
        assert found["session_id"] == "session-X"
        assert found["status"] == "claimed"


class TestCompleteTask:
    def test_complete_upserts_claim(self, patch_engram):
        """complete_task updates status to 'completed' and stores evidence."""
        engram_claims.claim_task("T200", "session-D")
        record = engram_claims.complete_task("T200", "session-D", "all tests pass")

        assert record["status"] == "completed"
        assert record["completed_by_session"] == "session-D"
        assert "completed_at" in record
        assert record["completion_evidence"] == {"description": "all tests pass"}

    def test_complete_with_dict_evidence(self, patch_engram):
        """complete_task accepts a dict as evidence."""
        engram_claims.claim_task("T201", "session-E")
        evidence = {"tests_passed": 12, "commit": "deadbeef"}
        record = engram_claims.complete_task("T201", "session-E", evidence)

        assert record["completion_evidence"] == evidence

    def test_complete_preserves_claimed_at(self, patch_engram):
        """complete_task keeps original claimed_at from the claim."""
        engram_claims.claim_task("T202", "session-F")
        original = engram_claims.find_claim("T202")
        assert original is not None
        orig_claimed_at = original["claimed_at"]

        record = engram_claims.complete_task("T202", "session-F", "done")
        assert record.get("claimed_at") == orig_claimed_at


class TestDupClaim:
    def test_dup_claim_same_session_is_idempotent(self, patch_engram):
        """Re-claiming the same task with the same session refreshes the claim."""
        engram_claims.claim_task("T300", "session-G")
        record2 = engram_claims.claim_task("T300", "session-G")

        assert record2["session_id"] == "session-G"
        assert record2["status"] == "claimed"

    def test_dup_claim_different_session_returns_existing(self, patch_engram):
        """Claiming a task already owned by another session returns existing claim."""
        engram_claims.claim_task("T301", "session-H")
        result = engram_claims.claim_task("T301", "session-I")

        assert result["session_id"] == "session-H", (
            "Should return existing claim by session-H, not overwrite it"
        )


class TestReleaseClaim:
    def test_release_marks_record_released(self, patch_engram):
        """release_claim writes a released status."""
        engram_claims.claim_task("T400", "session-J")
        engram_claims.release_claim("T400", "session-J")

        # After release, find_claim should return None or a released record.
        # The store keeps the last saved version.
        found = engram_claims.find_claim("T400")
        # Released record has status="released"
        if found is not None:
            assert found["status"] == "released"

    def test_release_noop_for_different_session(self, patch_engram):
        """release_claim is a no-op if called by a non-owner session."""
        engram_claims.claim_task("T401", "session-K")
        engram_claims.release_claim("T401", "session-L")  # wrong session

        # Claim should still belong to session-K.
        found = engram_claims.find_claim("T401")
        assert found is not None
        assert found["session_id"] == "session-K"

    def test_release_noop_for_nonexistent_task(self, patch_engram):
        """release_claim on unknown task does not raise."""
        engram_claims.release_claim("nonexistent", "session-M")  # must not raise


# ---------------------------------------------------------------------------
# Portability tests
# ---------------------------------------------------------------------------

class TestPortability:
    def test_module_importable_without_engram_binary(self, monkeypatch):
        """Module loads even when engram binary is absent (ENGRAM_BIN=missing)."""
        monkeypatch.setenv("ENGRAM_BIN", "/nonexistent/engram-binary")
        # Re-importing the module should not raise.
        import importlib
        importlib.reload(engram_claims)

    def test_save_fn_accepts_none_project(self, patch_engram):
        """claim_task works when _save_fn receives an empty project string."""
        # The fake store handles empty strings — no KeyError expected.
        record = engram_claims.claim_task("T500", "session-N")
        assert record["task_id"] == "T500"

    def test_search_fn_returns_empty_on_no_match(self, patch_engram):
        """find_claim returns None gracefully when _search_fn returns []."""
        result = engram_claims.find_claim("definitely-not-there")
        assert result is None
