from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "adr_reserve.py"
spec = importlib.util.spec_from_file_location("adr_reserve", MODULE_PATH)
assert spec and spec.loader
adr_reserve = importlib.util.module_from_spec(spec)
sys.modules["adr_reserve"] = adr_reserve
spec.loader.exec_module(adr_reserve)


def test_reserve_skips_existing_and_active_reserved_numbers(tmp_path: Path) -> None:
    adrs = tmp_path / "docs" / "adrs"
    adrs.mkdir(parents=True)
    (adrs / "ADR-001-existing.md").write_text("# ADR-001\n")

    first = adr_reserve.reserve(project_dir=tmp_path, title="First new", session_id="s1", owner="test", ttl_seconds=3600)
    second = adr_reserve.reserve(project_dir=tmp_path, title="Second new", session_id="s2", owner="test", ttl_seconds=3600)

    assert first.number == 2
    assert first.path == "docs/02-Decisions/adrs/ADR-002-first-new.md"
    assert second.number == 3
    data = json.loads((tmp_path / ".cognitive-os" / "locks" / "adr-reservations.json").read_text())
    assert [item["number"] for item in data["reservations"]] == [2, 3]


def test_expired_reservation_does_not_block_monotonic_next_number(tmp_path: Path) -> None:
    locks = tmp_path / ".cognitive-os" / "locks"
    locks.mkdir(parents=True)
    adrs = tmp_path / "docs" / "adrs"
    adrs.mkdir(parents=True)
    (adrs / "ADR-005-existing.md").write_text("# ADR-005\n")
    (locks / "adr-reservations.json").write_text(
        json.dumps(
            {
                "reservations": [
                    {
                        "number": 1,
                        "adr_id": "ADR-001",
                        "title": "Expired",
                        "slug": "expired",
                        "session_id": "old",
                        "owner": "test",
                        "expires_at": "2000-01-01T00:00:00+00:00",
                        "path": "docs/02-Decisions/adrs/ADR-001-expired.md",
                    }
                ]
            }
        )
    )

    reservation = adr_reserve.reserve(project_dir=tmp_path, title="Fresh", session_id="s", owner="test", ttl_seconds=3600)

    assert reservation.number == 6


def test_concurrent_reservations_are_unique(tmp_path: Path) -> None:
    def reserve_one(i: int) -> int:
        return adr_reserve.reserve(
            project_dir=tmp_path,
            title=f"Concurrent {i}",
            session_id=f"s{i}",
            owner="test",
            ttl_seconds=3600,
        ).number

    with ThreadPoolExecutor(max_workers=8) as pool:
        numbers = list(pool.map(reserve_one, range(12)))

    assert len(numbers) == 12
    assert sorted(numbers) == list(range(1, 13))


def test_concurrent_cli_reservations_are_unique_across_processes(tmp_path: Path) -> None:
    def reserve_one(i: int) -> int:
        result = subprocess.run(
            [
                sys.executable,
                str(MODULE_PATH),
                "--project-dir",
                str(tmp_path),
                "--title",
                f"Process Concurrent {i}",
                "--session-id",
                f"process-{i}",
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        return int(json.loads(result.stdout)["number"])

    with ThreadPoolExecutor(max_workers=8) as pool:
        numbers = list(pool.map(reserve_one, range(12)))

    assert len(numbers) == 12
    assert sorted(numbers) == list(range(1, 13))


def test_cli_outputs_json(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(MODULE_PATH),
            "--project-dir",
            str(tmp_path),
            "--title",
            "Hook execution observability",
            "--session-id",
            "cli-session",
            "--json",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["adr_id"] == "ADR-001"
    assert payload["path"] == "docs/02-Decisions/adrs/ADR-001-hook-execution-observability.md"
    assert payload["session_id"] == "cli-session"


def test_list_and_cleanup_expired_reservations(tmp_path: Path) -> None:
    locks = tmp_path / ".cognitive-os" / "locks"
    locks.mkdir(parents=True)
    state = locks / "adr-reservations.json"
    state.write_text(
        json.dumps(
            {
                "reservations": [
                    {
                        "number": 1,
                        "adr_id": "ADR-001",
                        "title": "Expired",
                        "slug": "expired",
                        "session_id": "old",
                        "owner": "test",
                        "expires_at": "2000-01-01T00:00:00+00:00",
                        "path": "docs/02-Decisions/adrs/ADR-001-expired.md",
                    },
                    {
                        "number": 2,
                        "adr_id": "ADR-002",
                        "title": "Active",
                        "slug": "active",
                        "session_id": "new",
                        "owner": "test",
                        "expires_at": "2999-01-01T00:00:00+00:00",
                        "path": "docs/02-Decisions/adrs/ADR-002-active.md",
                    },
                ]
            }
        )
    )

    rows = adr_reserve.list_reservations(project_dir=tmp_path)
    assert [row["status"] for row in rows] == ["expired", "active"]

    result = subprocess.run(
        [
            sys.executable,
            str(MODULE_PATH),
            "--project-dir",
            str(tmp_path),
            "--cleanup-expired",
            "--json",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["removed_count"] == 1
    remaining = json.loads(state.read_text())["reservations"]
    assert [item["adr_id"] for item in remaining] == ["ADR-002"]
