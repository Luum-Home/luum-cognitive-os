"""Behavioral tests for scripts/reserve_adr_slot.py (ADR-089 Layer 3).

Tests execute the script as a subprocess and assert on observable output
and side-effects (reservation file contents, slot numbers).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "reserve_adr_slot.py"


def _run(
    *args: str,
    project_dir: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(SCRIPT)]
    if project_dir:
        cmd += ["--project-dir", str(project_dir)]
    cmd += list(args)
    base_env = {**os.environ}
    base_env.setdefault("COGNITIVE_OS_SESSION_ID", "test-session")
    if env:
        base_env.update(env)
    return subprocess.run(cmd, capture_output=True, text=True, env=base_env)


def _reservations_path(project_dir: Path) -> Path:
    return project_dir / ".cognitive-os" / "runtime" / "adr-reservations" / "reservations.json"


# ── Existence ─────────────────────────────────────────────────────────────────


def test_script_exists():
    assert SCRIPT.exists(), f"reserve_adr_slot.py not found at {SCRIPT}"


# ── Default output is the slot number (integer) ────────────────────────────────


def test_default_output_is_slot_number(tmp_path: Path):
    result = _run("--title", "My feature", project_dir=tmp_path)
    assert result.returncode == 0, result.stderr
    number = int(result.stdout.strip())
    assert number >= 1


def test_slot_number_accounts_for_existing_adrs(tmp_path: Path):
    adrs = tmp_path / "docs" / "adrs"
    adrs.mkdir(parents=True)
    (adrs / "ADR-010-some-decision.md").write_text("# ADR-010\n")
    (adrs / "ADR-015-another.md").write_text("# ADR-015\n")

    result = _run("--title", "Next slot", project_dir=tmp_path)
    assert result.returncode == 0, result.stderr
    number = int(result.stdout.strip())
    assert number == 16  # next after max(10, 15)


# ── Reservation placeholder is created ───────────────────────────────────────


def test_reservation_file_written(tmp_path: Path):
    _run("--title", "Test ADR", project_dir=tmp_path)
    rpath = _reservations_path(tmp_path)
    assert rpath.exists(), "reservations.json not created"
    data = json.loads(rpath.read_text())
    assert len(data["reservations"]) == 1
    reservation = data["reservations"][0]
    assert reservation["number"] == 1
    assert reservation["session_id"] == "test-session"


# ── Two sequential reservations get unique, monotonically increasing slots ────


def test_sequential_reservations_are_unique(tmp_path: Path):
    r1 = _run("--title", "First", project_dir=tmp_path)
    r2 = _run("--title", "Second", project_dir=tmp_path)
    assert r1.returncode == 0
    assert r2.returncode == 0
    n1, n2 = int(r1.stdout.strip()), int(r2.stdout.strip())
    assert n1 != n2
    assert n2 == n1 + 1


# ── Expired reservation does not block next slot ──────────────────────────────


def test_expired_reservation_does_not_block_slot(tmp_path: Path):
    rpath = _reservations_path(tmp_path)
    rpath.parent.mkdir(parents=True, exist_ok=True)
    rpath.write_text(json.dumps({
        "reservations": [{
            "number": 5,
            "adr_id": "ADR-005",
            "title": "Expired reservation",
            "slug": "expired-reservation",
            "session_id": "old-session",
            "owner": "test",
            "reserved_at": "2000-01-01T00:00:00+00:00",
            "expires_at": "2000-01-01T01:00:00+00:00",
            "path": "docs/02-Decisions/adrs/ADR-005-expired-reservation.md",
        }]
    }))

    result = _run("--title", "Fresh slot", project_dir=tmp_path)
    assert result.returncode == 0, result.stderr
    number = int(result.stdout.strip())
    # Slot 5 is expired — next should be 1 (no active ADR files, no live reservations)
    assert number == 1


# ── --list shows in-flight reservations ──────────────────────────────────────


def test_list_shows_reservations(tmp_path: Path):
    _run("--title", "My ADR", project_dir=tmp_path, env={"COGNITIVE_OS_SESSION_ID": "listed-session"})
    result = _run("--list", project_dir=tmp_path)
    assert result.returncode == 0, result.stderr
    assert "ADR-001" in result.stdout
    assert "listed-session" in result.stdout


def test_list_json_format(tmp_path: Path):
    _run("--title", "My ADR", project_dir=tmp_path)
    result = _run("--list", "--json", project_dir=tmp_path)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert "reservations" in payload
    assert len(payload["reservations"]) >= 1


# ── --release frees a slot ────────────────────────────────────────────────────


def test_release_frees_slot(tmp_path: Path):
    r1 = _run("--title", "To release", project_dir=tmp_path)
    number = int(r1.stdout.strip())

    # Verify it's there
    rpath = _reservations_path(tmp_path)
    data = json.loads(rpath.read_text())
    assert any(r["number"] == number for r in data["reservations"])

    # Release it
    result = _run("--release", str(number), project_dir=tmp_path)
    assert result.returncode == 0, result.stderr

    # Verify it's gone
    data_after = json.loads(rpath.read_text())
    assert not any(r["number"] == number for r in data_after["reservations"])


def test_release_nonexistent_slot_fails(tmp_path: Path):
    result = _run("--release", "999", project_dir=tmp_path)
    assert result.returncode == 1
    assert "not found" in result.stderr


# ── --cleanup removes expired reservations ────────────────────────────────────


def test_cleanup_removes_expired(tmp_path: Path):
    rpath = _reservations_path(tmp_path)
    rpath.parent.mkdir(parents=True, exist_ok=True)
    rpath.write_text(json.dumps({
        "reservations": [
            {
                "number": 1,
                "adr_id": "ADR-001",
                "title": "Expired",
                "slug": "expired",
                "session_id": "old",
                "owner": "test",
                "reserved_at": "2000-01-01T00:00:00+00:00",
                "expires_at": "2000-01-01T01:00:00+00:00",
                "path": "docs/02-Decisions/adrs/ADR-001-expired.md",
            },
            {
                "number": 2,
                "adr_id": "ADR-002",
                "title": "Active",
                "slug": "active",
                "session_id": "current",
                "owner": "test",
                "reserved_at": "2999-01-01T00:00:00+00:00",
                "expires_at": "2999-01-01T01:00:00+00:00",
                "path": "docs/02-Decisions/adrs/ADR-002-active.md",
            },
        ]
    }))

    result = _run("--cleanup", project_dir=tmp_path)
    assert result.returncode == 0, result.stderr
    assert "1" in result.stdout  # "removed 1 expired reservation(s)"

    data = json.loads(rpath.read_text())
    numbers = [r["number"] for r in data["reservations"]]
    assert numbers == [2]


# ── Slot reservation collision handling (concurrent processes) ────────────────


def test_concurrent_slot_reservations_are_unique(tmp_path: Path):
    """Multiple concurrent process-level invocations must produce unique slots."""
    def reserve_one(i: int) -> int:
        result = _run(
            "--title", f"Concurrent {i}",
            project_dir=tmp_path,
            env={"COGNITIVE_OS_SESSION_ID": f"session-{i}"},
        )
        assert result.returncode == 0, f"session-{i} failed: {result.stderr}"
        return int(result.stdout.strip())

    with ThreadPoolExecutor(max_workers=6) as pool:
        numbers = list(pool.map(reserve_one, range(10)))

    assert len(numbers) == 10
    assert len(set(numbers)) == 10, f"Slot collision detected: {sorted(numbers)}"
    assert sorted(numbers) == list(range(1, 11))


# ── TTL default is 30 minutes ────────────────────────────────────────────────


def test_default_ttl_is_30_minutes(tmp_path: Path):
    import datetime

    _run("--title", "TTL check", project_dir=tmp_path)
    rpath = _reservations_path(tmp_path)
    data = json.loads(rpath.read_text())
    reservation = data["reservations"][0]
    expires_at = datetime.datetime.fromisoformat(reservation["expires_at"])
    now = datetime.datetime.now(datetime.timezone.utc)
    delta = expires_at - now
    # Should be approximately 30 minutes (1800s) — allow 60s slack for test execution
    assert 1740 <= delta.total_seconds() <= 1860, f"TTL out of range: {delta.total_seconds()}s"
