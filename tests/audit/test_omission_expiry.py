"""Behavioural contract for scripts/audit_omission_expiry.py.

These tests EXECUTE the audit against fixtures. A test that only asserted the
file exists would pass against a script that returns 0 unconditionally, which is
the exact failure mode this gate is supposed to prevent elsewhere.

Branch coverage mirrors the drill in
docs/06-Daily/reports/omisiones-con-fecha-y-dueno-2026-08-21.md:
clean -> 0, expired -> 1, schema violation -> 1, empty ledger -> 2.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

pytestmark = [pytest.mark.audit]

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = PROJECT_ROOT / "scripts" / "audit_omission_expiry.py"
CLASSIFICATION = PROJECT_ROOT / "manifests" / "hook-registration-classification.yaml"
ULTIMATUM = PROJECT_ROOT / "manifests" / "gate-instrumentation-ultimatum.yaml"

# Kept in sync with PERMANENT_STATUSES in the script. Duplicated on purpose:
# if someone widens the script's allowlist to silence a red, this copy disagrees
# and the test says so.
PERMANENT_STATUSES = {
    "active",
    "internal_helper",
    "projected_elsewhere",
    "git_or_manual",
    "manual_trigger",
    "profile_scoped",
}


def _run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )


@pytest.fixture()
def fixture_root(tmp_path: Path) -> Path:
    (tmp_path / "manifests").mkdir()
    for src in (CLASSIFICATION, ULTIMATUM):
        (tmp_path / "manifests" / src.name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    return tmp_path


def _load_classification(root: Path) -> dict:
    return json.loads((root / "manifests" / CLASSIFICATION.name).read_text(encoding="utf-8"))


def _write_classification(root: Path, data: dict) -> None:
    (root / "manifests" / CLASSIFICATION.name).write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def test_real_manifests_are_clean_today() -> None:
    """The live tree must be green, otherwise every other assertion here is moot."""
    proc = _run(PROJECT_ROOT)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_seeded_expired_row_is_caught(fixture_root: Path) -> None:
    data = _load_classification(fixture_root)
    data["entries"][0]["expires"] = "2020-01-01"
    _write_classification(fixture_root, data)

    proc = _run(fixture_root, "--as-of", "2026-08-21")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "EXPIRED" in proc.stdout
    assert data["entries"][0]["path"] in proc.stdout


def test_removing_the_seed_returns_to_green(fixture_root: Path) -> None:
    """The other half of the counterfactual: if both branches agree, it is decoration."""
    data = _load_classification(fixture_root)
    original = data["entries"][0]["expires"]
    data["entries"][0]["expires"] = "2020-01-01"
    _write_classification(fixture_root, data)
    assert _run(fixture_root, "--as-of", "2026-08-21").returncode == 1

    data["entries"][0]["expires"] = original
    _write_classification(fixture_root, data)
    assert _run(fixture_root, "--as-of", "2026-08-21").returncode == 0


def test_empty_ledger_exits_two_not_zero(fixture_root: Path) -> None:
    """A checker that walks zero rows must not report success."""
    data = _load_classification(fixture_root)
    data["entries"] = []
    _write_classification(fixture_root, data)

    proc = _run(fixture_root, "--as-of", "2026-08-21")
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "ZERO entries" in proc.stderr


def test_missing_ledger_exits_two(fixture_root: Path) -> None:
    (fixture_root / "manifests" / ULTIMATUM.name).unlink()
    proc = _run(fixture_root, "--as-of", "2026-08-21")
    assert proc.returncode == 2, proc.stdout + proc.stderr


def test_never_on_a_deferred_status_is_a_violation(fixture_root: Path) -> None:
    """`never` is the cheap green. It is only legal where absence is structural."""
    data = _load_classification(fixture_root)
    target = next(e for e in data["entries"] if e["status"] == "future")
    target["expires"] = "never"
    _write_classification(fixture_root, data)

    proc = _run(fixture_root, "--as-of", "2026-08-21")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "never" in proc.stdout and target["path"] in proc.stdout


def test_stripping_owner_or_expires_is_a_violation(fixture_root: Path) -> None:
    data = _load_classification(fixture_root)
    data["entries"][2].pop("owner", None)
    data["entries"][3].pop("expires", None)
    _write_classification(fixture_root, data)

    proc = _run(fixture_root, "--as-of", "2026-08-21")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert data["entries"][2]["path"] in proc.stdout
    assert data["entries"][3]["path"] in proc.stdout


def test_json_mode_matches_the_control_plane_contract(fixture_root: Path) -> None:
    """manifests/control-plane-audits.yaml pins expected_schema; a drift here makes
    the runner emit `audit-schema-mismatch` instead of the real findings."""
    proc = _run(fixture_root, "--as-of", "2026-08-21", "--json")
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "omission-expiry-audit/v1"
    assert set(payload["summary"]) == {"block", "warn", "findings"}
    for finding in payload["findings"]:
        assert finding["severity"] in {"warn", "block"}
        assert finding["code"] and finding["stable_id"]

    declared = yaml.safe_load((PROJECT_ROOT / "manifests" / "control-plane-audits.yaml").read_text(encoding="utf-8"))
    spec = declared["audits"]["omission-expiry"]
    assert spec["expected_schema"] == payload["schema_version"]
    assert spec["mutates"] is False
    lanes = declared["lanes"]
    assert "omission-expiry" in lanes["hook-fast"]["audits"]


def test_expiry_dates_are_staggered_not_a_single_wall() -> None:
    """106 rows expiring the same day is a wall that gets ignored whole on day one."""
    entries = json.loads(CLASSIFICATION.read_text(encoding="utf-8"))["entries"]
    dated = [e["expires"] for e in entries if e["expires"] != "never"]
    assert dated, "no dated omission left in the manifest"
    busiest = max(dated.count(d) for d in set(dated))
    assert busiest <= 3, f"{busiest} omissions share one expiry date"


def test_every_row_carries_owner_and_expires() -> None:
    entries = json.loads(CLASSIFICATION.read_text(encoding="utf-8"))["entries"]
    for entry in entries:
        assert entry.get("owner"), entry
        assert entry.get("expires"), entry
        if entry["expires"] == "never":
            assert entry["status"] in PERMANENT_STATUSES, entry

    ultimatum = yaml.safe_load(ULTIMATUM.read_text(encoding="utf-8"))
    assert ultimatum["entries"], "ultimatum ledger must not be empty"
    for entry in ultimatum["entries"]:
        assert entry.get("owner"), entry
        assert entry["expires"] != "never", entry
