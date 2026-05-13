# SCOPE: os-only
"""Unit tests for lib/skill_drift_detector.py.

Tests execute the actual SkillDriftDetector code — not just file existence.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from lib.skill_drift_detector import (
    DriftEvent,
    SkillDriftDetector,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _make_lock(tmp_path: Path, entries: list[dict]) -> Path:
    lock_path = tmp_path / "skills" / "REGISTRY.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(
        yaml.dump(
            {
                "schema_version": 1,
                "generated_at": "2026-05-13T00:00:00+00:00",
                "policy": "test",
                "skills": entries,
            }
        ),
        encoding="utf-8",
    )
    return lock_path


def _make_skill_file(tmp_path: Path, rel_path: str, content: bytes) -> Path:
    p = tmp_path / rel_path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(content)
    return p


def _make_detector(tmp_path: Path) -> SkillDriftDetector:
    lock_path = tmp_path / "skills" / "REGISTRY.lock"
    return SkillDriftDetector(
        lock_path=lock_path,
        skills_root=tmp_path / "skills",
        project_root=tmp_path,
    )


# ---------------------------------------------------------------------------
# Test A: detects drift when hash differs
# ---------------------------------------------------------------------------


def test_detect_drift_when_hash_differs(tmp_path: Path) -> None:
    """detect_drift() returns a DriftEvent when a file's hash does not match the lock."""
    original_content = b"# original skill content"
    mutated_content = b"# mutated skill content - injected by test"

    rel_path = "skills/my-skill/SKILL.md"
    locked_hash = _sha256_bytes(original_content)

    _make_lock(tmp_path, [{"path": rel_path, "sha256": locked_hash}])
    _make_skill_file(tmp_path, rel_path, mutated_content)

    detector = _make_detector(tmp_path)
    events = detector.detect_drift()

    assert len(events) == 1
    ev = events[0]
    assert isinstance(ev, DriftEvent)
    assert ev.skill == rel_path
    assert ev.expected == locked_hash
    assert ev.actual == _sha256_bytes(mutated_content)
    assert ev.actual != ev.expected


# ---------------------------------------------------------------------------
# Test B: no drift when hash matches
# ---------------------------------------------------------------------------


def test_no_drift_when_hash_matches(tmp_path: Path) -> None:
    """detect_drift() returns an empty list when all skill hashes match the lock."""
    content = b"# canonical skill content\nNo changes."
    rel_path = "skills/clean-skill/SKILL.md"
    locked_hash = _sha256_bytes(content)

    _make_lock(tmp_path, [{"path": rel_path, "sha256": locked_hash}])
    _make_skill_file(tmp_path, rel_path, content)

    detector = _make_detector(tmp_path)
    events = detector.detect_drift()

    assert events == []


# ---------------------------------------------------------------------------
# Test C: handles skill present in lock but missing on disk
# ---------------------------------------------------------------------------


def test_missing_skill_file_reported_as_drift(tmp_path: Path) -> None:
    """A skill recorded in REGISTRY.lock but absent from disk is reported as drift."""
    rel_path = "skills/removed-skill/SKILL.md"
    locked_hash = _sha256_bytes(b"some content that was promoted")

    _make_lock(tmp_path, [{"path": rel_path, "sha256": locked_hash}])
    # Do NOT create the file on disk — it was removed post-promotion.

    detector = _make_detector(tmp_path)
    events = detector.detect_drift()

    assert len(events) == 1
    ev = events[0]
    assert ev.skill == rel_path
    assert ev.actual == "<missing>"


# ---------------------------------------------------------------------------
# Test D: mtime cache avoids re-hashing unchanged files
# ---------------------------------------------------------------------------


def test_mtime_cache_avoids_rehashing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A file with a matching mtime cache entry is not re-hashed."""
    content = b"# cached skill"
    rel_path = "skills/cached-skill/SKILL.md"
    locked_hash = _sha256_bytes(content)

    _make_lock(tmp_path, [{"path": rel_path, "sha256": locked_hash}])
    _make_skill_file(tmp_path, rel_path, content)

    detector = _make_detector(tmp_path)

    # First run — populates cache
    events_first = detector.detect_drift()
    assert events_first == []

    # Verify cache file was written
    cache_path = tmp_path / ".cognitive-os" / "state" / "skill-hash-cache.json"
    assert cache_path.exists(), "mtime cache file should be created after first run"
    cache_data = json.loads(cache_path.read_text())
    assert rel_path in cache_data
    cached_entry = cache_data[rel_path]
    assert "mtime" in cached_entry
    assert "sha256" in cached_entry
    assert cached_entry["sha256"] == locked_hash

    # Track calls to _sha256_file via monkeypatching
    call_count = {"n": 0}
    import lib.skill_drift_detector as sdd_module
    original_sha256 = sdd_module._sha256_file

    def counting_sha256(path: Path) -> str:
        call_count["n"] += 1
        return original_sha256(path)

    monkeypatch.setattr(sdd_module, "_sha256_file", counting_sha256)

    # Second run — file is unchanged, cache should be hit, no re-hash
    detector2 = _make_detector(tmp_path)
    events_second = detector2.detect_drift()
    assert events_second == []
    assert call_count["n"] == 0, (
        f"_sha256_file was called {call_count['n']} time(s) on second run — "
        "mtime cache should have prevented re-hashing"
    )


# ---------------------------------------------------------------------------
# Test E: is_skill_locked and verify_single helpers
# ---------------------------------------------------------------------------


def test_is_skill_locked(tmp_path: Path) -> None:
    """is_skill_locked() returns True for locked paths, False for unknown."""
    rel_path = "skills/known/SKILL.md"
    content = b"known skill"
    _make_lock(tmp_path, [{"path": rel_path, "sha256": _sha256_bytes(content)}])

    detector = _make_detector(tmp_path)
    assert detector.is_skill_locked(rel_path) is True
    assert detector.is_skill_locked("skills/unknown/SKILL.md") is False


def test_verify_single_matches(tmp_path: Path) -> None:
    """verify_single() returns True when on-disk hash matches lock."""
    content = b"correct content"
    rel_path = "skills/single/SKILL.md"
    _make_lock(tmp_path, [{"path": rel_path, "sha256": _sha256_bytes(content)}])
    skill_file = _make_skill_file(tmp_path, rel_path, content)

    detector = _make_detector(tmp_path)
    assert detector.verify_single(skill_file) is True


def test_verify_single_mismatch(tmp_path: Path) -> None:
    """verify_single() returns False when on-disk hash differs from lock."""
    content = b"correct content"
    mutated = b"wrong content"
    rel_path = "skills/single/SKILL.md"
    _make_lock(tmp_path, [{"path": rel_path, "sha256": _sha256_bytes(content)}])
    skill_file = _make_skill_file(tmp_path, rel_path, mutated)

    detector = _make_detector(tmp_path)
    assert detector.verify_single(skill_file) is False


# ---------------------------------------------------------------------------
# Test F: audit trail is written on drift
# ---------------------------------------------------------------------------


def test_audit_trail_written_on_drift(tmp_path: Path) -> None:
    """Drift events are appended to skill-drift.jsonl."""
    rel_path = "skills/drifted/SKILL.md"
    locked_hash = _sha256_bytes(b"original")
    _make_lock(tmp_path, [{"path": rel_path, "sha256": locked_hash}])
    _make_skill_file(tmp_path, rel_path, b"mutated")

    detector = _make_detector(tmp_path)
    detector.detect_drift()

    audit_path = tmp_path / ".cognitive-os" / "metrics" / "skill-drift.jsonl"
    assert audit_path.exists(), "Audit trail file should be created"
    lines = [l for l in audit_path.read_text().splitlines() if l.strip()]
    assert len(lines) >= 1
    record = json.loads(lines[-1])
    assert record["skill"] == rel_path
    assert record["expected"] == locked_hash
    assert "ts" in record
