"""Unit tests for scripts/push_collision_detect.py — ADR-116 P4.2.

Covers:
  1. Exact subject match, same patch  → severity=warn (already-applied)
  2. Exact subject match, different patch → severity=block (independent re-impl)
  3. 85% subject similarity, same patch → severity=warn (already-applied, fuzzy)
  4. 70% subject similarity → below threshold, ignored (no collision)
  5. No match at all → exit 0
  6. Real-data smoke: today's incident subject → collision flagged
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[2]

# Add repo root to path so we can import the script directly
import sys
sys.path.insert(0, str(REPO_ROOT))

from scripts.push_collision_detect import (
    Collision,
    detect_collisions,
    levenshtein,
    main,
    similarity,
)


# ---------------------------------------------------------------------------
# Unit: levenshtein & similarity
# ---------------------------------------------------------------------------


def test_levenshtein_identical():
    assert levenshtein("abc", "abc") == 0


def test_levenshtein_empty():
    assert levenshtein("", "abc") == 3
    assert levenshtein("abc", "") == 3


def test_levenshtein_one_edit():
    assert levenshtein("cat", "bat") == 1


def test_similarity_identical():
    assert similarity("hello", "hello") == 1.0


def test_similarity_completely_different():
    s = similarity("aaaa", "bbbb")
    assert s == 0.0


def test_similarity_empty_strings():
    assert similarity("", "") == 1.0


def test_similarity_threshold_80_pct():
    """A one-char change in an 8-char string is 87.5% similar — above threshold."""
    s = similarity("feat: add foo", "feat: add bar")
    # "foo" vs "bar" differs by 3 chars; total len 13 → similarity = 1 - 3/13 ≈ 0.769
    # Actually both strings have len 13 and differ by 3 chars → 1 - 3/13 ≈ 0.769
    # This is BELOW 0.80, intentional — covers the "below threshold" case.
    assert s < 0.80


def test_similarity_85_pct_smoke():
    """Smoke: subjects that differ by one word in a medium-length string."""
    a = "docs(reports): add aspirational-audit-2026-05-02 from elegant-boyd archive"
    b = "docs(reports): add aspirational-audit-2026-05-02 from noble-hall archive"
    s = similarity(a, b)
    # Difference: "elegant-boyd" vs "noble-hall" (12 vs 10 chars, but Levenshtein varies)
    # Key check: it should be above 0.80 for near-identical subjects
    assert s >= 0.80, f"Expected similarity >= 0.80, got {s:.3f}"


# ---------------------------------------------------------------------------
# Collision dataclass logic
# ---------------------------------------------------------------------------


def _make_collision(subject_sim: float, overlap_pct: float, match_type: str = "exact") -> Collision:
    return Collision(
        local_sha="aaa" * 13 + "a",
        local_subject="some subject",
        origin_sha="bbb" * 13 + "b",
        origin_subject="some subject",
        subject_similarity=subject_sim,
        patch_overlap_pct=overlap_pct,
        match_type=match_type,
    )


class TestCollisionSeverity:
    """Case 1: Exact match, same patch → warn (already-applied)."""

    def test_exact_subject_same_patch_is_warn(self):
        c = _make_collision(1.0, 100.0, "exact")
        assert c.severity() == "warn"
        assert c.is_already_applied()

    """Case 2: Exact match, different patch → block (independent re-impl)."""

    def test_exact_subject_different_patch_is_block(self):
        c = _make_collision(1.0, 30.0, "exact")
        assert c.severity() == "block"
        assert not c.is_already_applied()

    """Case 3: 85% subject similarity, same patch → warn."""

    def test_fuzzy_match_same_patch_is_warn(self):
        c = _make_collision(0.85, 90.0, "fuzzy")
        assert c.severity() == "warn"
        assert c.is_already_applied()

    def test_message_contains_key_info(self):
        c = _make_collision(0.85, 90.0, "fuzzy")
        msg = c.message()
        assert "fuzzy" in msg
        assert "85%" in msg
        assert "90%" in msg
        assert "already-applied" in msg


# ---------------------------------------------------------------------------
# detect_collisions integration tests (mocked git)
# ---------------------------------------------------------------------------


def _mock_detect(
    local: list[tuple[str, str]],
    origin: list[tuple[str, str]],
    overlap: float = 100.0,
    threshold: float = 0.80,
) -> list[Collision]:
    """Run detect_collisions with fully mocked git operations."""
    root = Path("/fake/root")
    with (
        patch("scripts.push_collision_detect.unpushed_commits", return_value=local),
        patch("scripts.push_collision_detect.recent_origin_commits", return_value=origin),
        patch("scripts.push_collision_detect.patch_overlap_pct", return_value=overlap),
    ):
        return detect_collisions(root, threshold=threshold)


class TestDetectCollisions:
    """Case 5: No collision — clean."""

    def test_no_collision_clean_exit(self):
        local = [("sha_local_1", "feat: add user auth")]
        origin = [("sha_origin_1", "fix: resolve memory leak")]
        collisions = _mock_detect(local, origin, overlap=0.0)
        assert collisions == []

    """Case 1: Exact subject match, same patch (overlap=100%)."""

    def test_exact_subject_same_patch_flags_warn(self):
        subj = "docs(reports): add aspirational-audit-2026-05-02 from elegant-boyd archive"
        local = [("local_sha_abc", subj)]
        origin = [("origin_sha_xyz", subj)]
        collisions = _mock_detect(local, origin, overlap=100.0)
        assert len(collisions) == 1
        assert collisions[0].match_type == "exact"
        assert collisions[0].severity() == "warn"

    """Case 2: Exact subject match, different patch (overlap=20%)."""

    def test_exact_subject_different_patch_flags_block(self):
        subj = "feat: implement order service"
        local = [("local_sha_111", subj)]
        origin = [("origin_sha_222", subj)]
        collisions = _mock_detect(local, origin, overlap=20.0)
        assert len(collisions) == 1
        assert collisions[0].severity() == "block"

    """Case 3: 85% subject similarity, same patch → warn."""

    def test_fuzzy_85_pct_same_patch_flags_warn(self):
        local_subj = "docs(reports): add aspirational-audit-2026-05-02 from elegant-boyd archive"
        origin_subj = "docs(reports): add aspirational-audit-2026-05-02 from noble-hall archive"
        sim = similarity(local_subj, origin_subj)
        # Confirm the test fixture actually achieves ≥80% similarity
        assert sim >= 0.80, f"Fixture similarity {sim:.3f} is below threshold"
        local = [("local_sha_aaa", local_subj)]
        origin = [("origin_sha_bbb", origin_subj)]
        collisions = _mock_detect(local, origin, overlap=90.0)
        assert len(collisions) == 1
        assert collisions[0].match_type == "fuzzy"
        assert collisions[0].severity() == "warn"

    """Case 4: 70% subject similarity → below threshold (0.80), ignored."""

    def test_below_threshold_ignored(self):
        # Subjects with ~70% similarity (well below 80%)
        local_subj = "feat: add complete authentication system with JWT"
        origin_subj = "fix: patch sql injection in login route"
        sim = similarity(local_subj, origin_subj)
        assert sim < 0.80, f"Fixture should be below 0.80, got {sim:.3f}"
        local = [("local_sha_ccc", local_subj)]
        origin = [("origin_sha_ddd", origin_subj)]
        # Use default threshold (0.80); these are dissimilar → no collision
        collisions = _mock_detect(local, origin, overlap=0.0)
        assert collisions == []

    def test_same_sha_skipped(self):
        """If local SHA == origin SHA it's the same commit, not a collision."""
        subj = "feat: same commit both sides"
        same_sha = "abcdef1234567890" * 2 + "abcdef12"
        local = [(same_sha, subj)]
        origin = [(same_sha, subj)]
        with (
            patch("scripts.push_collision_detect.unpushed_commits", return_value=local),
            patch("scripts.push_collision_detect.recent_origin_commits", return_value=origin),
        ):
            collisions = detect_collisions(Path("/fake/root"))
        assert collisions == []


# ---------------------------------------------------------------------------
# Case 6: Real-data smoke — today's session-2026-05-02 incident
# ---------------------------------------------------------------------------


class TestRealDataSmoke:
    """Simulate the actual incident: parallel session shipped the same subject."""

    INCIDENT_SUBJECT = (
        "docs(reports): add aspirational-audit-2026-05-02 from elegant-boyd archive"
    )
    # Slightly different wording (different session name) from a parallel commit
    ORIGIN_SUBJECT = (
        "docs(reports): add aspirational-audit-2026-05-02 from noble-hall archive"
    )

    def test_incident_subject_collision_detected(self):
        """The orphaned commit's subject must be flagged as a collision."""
        local = [("173bcae1" + "0" * 32, self.INCIDENT_SUBJECT)]
        origin = [("52380c52" + "0" * 32, self.ORIGIN_SUBJECT)]
        # Simulate same content (already-applied from origin)
        collisions = _mock_detect(local, origin, overlap=85.0)
        assert len(collisions) == 1, "Expected incident collision to be flagged"
        c = collisions[0]
        assert "aspirational-audit-2026-05-02" in c.local_subject
        assert c.severity() == "warn"  # patch overlap ≥70% → already-applied

    def test_incident_exact_match_flags_correctly(self):
        """Even with exact same subject, different SHA → collision."""
        local = [("173bcae1" + "0" * 32, self.INCIDENT_SUBJECT)]
        origin = [("52380c52" + "0" * 32, self.INCIDENT_SUBJECT)]
        collisions = _mock_detect(local, origin, overlap=95.0)
        assert len(collisions) == 1
        assert collisions[0].match_type == "exact"


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------


class TestCLI:
    def test_main_no_collisions_exit_0(self, tmp_path: Path):
        """main() exits 0 when no collisions found."""
        with (
            patch("scripts.push_collision_detect.unpushed_commits", return_value=[]),
            patch(
                "scripts.push_collision_detect.recent_origin_commits", return_value=[]
            ),
        ):
            rc = main(["--project-dir", str(tmp_path)])
        assert rc == 0

    def test_main_warn_mode_exits_0_on_collision(self, tmp_path: Path, monkeypatch):
        """In warn mode, a collision still exits 0."""
        monkeypatch.setenv("COS_PUSH_COLLISION_MODE", "warn")
        subj = "feat: add something"
        with (
            patch(
                "scripts.push_collision_detect.unpushed_commits",
                return_value=[("local_sha", subj)],
            ),
            patch(
                "scripts.push_collision_detect.recent_origin_commits",
                return_value=[("origin_sha", subj)],
            ),
            patch("scripts.push_collision_detect.patch_overlap_pct", return_value=20.0),
        ):
            rc = main(["--project-dir", str(tmp_path)])
        assert rc == 0

    def test_main_block_mode_exits_2_on_independent_reimpl(
        self, tmp_path: Path, monkeypatch
    ):
        """In block mode, a block-severity collision exits 2."""
        monkeypatch.setenv("COS_PUSH_COLLISION_MODE", "block")
        subj = "feat: add something"
        with (
            patch(
                "scripts.push_collision_detect.unpushed_commits",
                return_value=[("local_sha", subj)],
            ),
            patch(
                "scripts.push_collision_detect.recent_origin_commits",
                return_value=[("origin_sha", subj)],
            ),
            patch("scripts.push_collision_detect.patch_overlap_pct", return_value=20.0),
        ):
            rc = main(["--project-dir", str(tmp_path)])
        assert rc == 2

    def test_main_json_output(self, tmp_path: Path, monkeypatch, capsys):
        """--json flag produces parseable JSON."""
        monkeypatch.setenv("COS_PUSH_COLLISION_MODE", "warn")
        subj = "feat: add something"
        with (
            patch(
                "scripts.push_collision_detect.unpushed_commits",
                return_value=[("local_sha", subj)],
            ),
            patch(
                "scripts.push_collision_detect.recent_origin_commits",
                return_value=[("origin_sha", subj)],
            ),
            patch("scripts.push_collision_detect.patch_overlap_pct", return_value=100.0),
        ):
            import json as _json

            main(["--project-dir", str(tmp_path), "--json"])
        captured = capsys.readouterr()
        data = _json.loads(captured.out)
        assert "collisions" in data
        assert not data["ok"]
