"""Integration tests for ADR-113 P3 (status) and P4 (break) commands.

Covers:
- cos-validation-status.sh --json output schema
- exit codes: 0=HEALTHY, 1=STALE, 2/0=NO_LOCK
- cos-validation-break.sh capsule-ID mismatch rejection
- break with valid capsule + --reason removes lock and writes audit
- audit JSONL required fields
- break without --reason is rejected (audit trail enforcement)

All tests use tempdir + COGNITIVE_OS_PROJECT_DIR env injection to avoid
touching the live .cognitive-os/runtime/validation-capsule.lock.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATUS_SCRIPT = PROJECT_ROOT / "scripts" / "cos-validation-status.sh"
BREAK_SCRIPT = PROJECT_ROOT / "scripts" / "cos-validation-break.sh"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _runtime(base: Path) -> Path:
    r = base / ".cognitive-os" / "runtime"
    r.mkdir(parents=True, exist_ok=True)
    return r


def _write_lock(runtime: Path, data: dict) -> Path:
    lock = runtime / "validation-capsule.lock"
    lock.write_text(json.dumps(data) + "\n", encoding="utf-8")
    return lock


def _base_env(project_dir: Path) -> dict:
    """Env with isolated PROJECT_DIR and a small activity threshold."""
    return {
        **os.environ,
        "COGNITIVE_OS_PROJECT_DIR": str(project_dir),
        "COS_VALIDATION_ACTIVITY_THRESHOLD": "30",
    }


def _run_status(project_dir: Path, extra_args: list[str] | None = None, **kw) -> subprocess.CompletedProcess:
    args = ["bash", str(STATUS_SCRIPT)] + (extra_args or [])
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=15,
        env=_base_env(project_dir),
        **kw,
    )


def _run_break(project_dir: Path, extra_args: list[str] | None = None, **kw) -> subprocess.CompletedProcess:
    args = ["bash", str(BREAK_SCRIPT)] + (extra_args or [])
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=20,
        env=_base_env(project_dir),
        **kw,
    )


# ---------------------------------------------------------------------------
# P3 — status command
# ---------------------------------------------------------------------------


class TestValidationStatus:
    def test_no_lock_returns_exit_0_and_json_verdict_no_lock(self, tmp_path: Path) -> None:
        """When there is no lock, status exits 0 and --json reports NO_LOCK."""
        result = _run_status(tmp_path, ["--json"])

        assert result.returncode == 0, f"Expected 0 for no lock; got {result.returncode}"
        payload = json.loads(result.stdout)
        assert payload["verdict"] == "NO_LOCK"

    def test_json_output_is_valid_json_when_flag_passed(self, tmp_path: Path) -> None:
        """--json must always emit parseable JSON, even for edge-case locks."""
        runtime = _runtime(tmp_path)
        _write_lock(
            runtime,
            {
                "run_id": "status-schema-test",
                "pid": os.getpid(),
                "expires_at_epoch": int(time.time()) + 600,
                "started_at_epoch": int(time.time()) - 60,
                "capsule_dir": str(tmp_path / "capsule"),
                "message": "schema check",
            },
        )

        result = _run_status(tmp_path, ["--json"])

        # Must be parseable JSON regardless of exit code.
        payload = json.loads(result.stdout)
        assert "verdict" in payload
        assert "lock" in payload
        assert "signals" in payload

    def test_json_schema_has_required_top_level_keys(self, tmp_path: Path) -> None:
        """The JSON output must include verdict, lock, and signals keys."""
        runtime = _runtime(tmp_path)
        interval = 30
        _write_lock(
            runtime,
            {
                "run_id": "status-keys-test",
                "pid": os.getpid(),
                "expires_at_epoch": int(time.time()) + 600,
                "started_at_epoch": int(time.time()) - 60,
                "last_heartbeat_epoch": int(time.time()) - 5,
                "heartbeat_interval_seconds": interval,
                "capsule_dir": str(tmp_path / "capsule"),
                "message": "schema keys test",
            },
        )

        result = _run_status(tmp_path, ["--json"])

        payload = json.loads(result.stdout)
        for key in ("verdict", "lock", "signals"):
            assert key in payload, f"Missing required key '{key}' in JSON output"

    def test_healthy_lock_returns_exit_0(self, tmp_path: Path) -> None:
        """A lock with live PID and fresh heartbeat → HEALTHY, exit 0."""
        runtime = _runtime(tmp_path)
        interval = 30
        _write_lock(
            runtime,
            {
                "run_id": "status-healthy",
                "pid": os.getpid(),
                "expires_at_epoch": int(time.time()) + 600,
                "started_at_epoch": int(time.time()) - 60,
                "last_heartbeat_epoch": int(time.time()) - 5,
                "heartbeat_interval_seconds": interval,
                "capsule_dir": str(tmp_path / "capsule"),
                "message": "healthy test",
            },
        )

        result = _run_status(tmp_path, ["--json"])

        payload = json.loads(result.stdout)
        assert result.returncode == 0, f"Expected 0 for HEALTHY lock; got {result.returncode}"
        assert payload["verdict"] == "HEALTHY"

    def test_stale_heartbeat_lock_returns_exit_1(self, tmp_path: Path) -> None:
        """A lock with stale heartbeat → STALE, exit 1."""
        runtime = _runtime(tmp_path)
        interval = 30
        stale_hb = int(time.time()) - (4 * interval)

        _write_lock(
            runtime,
            {
                "run_id": "status-stale",
                "pid": os.getpid(),
                "expires_at_epoch": int(time.time()) + 600,
                "started_at_epoch": int(time.time()) - 300,
                "last_heartbeat_epoch": stale_hb,
                "heartbeat_interval_seconds": interval,
                "capsule_dir": str(tmp_path / "capsule"),
                "message": "stale heartbeat test",
            },
        )

        result = _run_status(tmp_path, ["--json"])

        payload = json.loads(result.stdout)
        assert result.returncode == 1, f"Expected 1 for STALE lock; got {result.returncode}"
        assert payload["verdict"] == "STALE"


# ---------------------------------------------------------------------------
# P4 — break command
# ---------------------------------------------------------------------------


class TestValidationBreak:
    def test_break_requires_reason_flag(self, tmp_path: Path) -> None:
        """--reason is required for audit trail; omitting it must exit non-zero with error."""
        runtime = _runtime(tmp_path)
        run_id = "unit-break-no-reason"
        _write_lock(
            runtime,
            {
                "run_id": run_id,
                "pid": os.getpid(),
                "expires_at_epoch": int(time.time()) + 600,
                "started_at_epoch": int(time.time()) - 60,
                "capsule_dir": str(tmp_path / "capsule"),
                "message": "no-reason test",
            },
        )

        result = _run_break(tmp_path, ["--capsule", run_id, "--force"])

        assert result.returncode != 0, "break without --reason must be rejected"
        assert "reason" in result.stderr.lower(), (
            "Error message must mention 'reason'; got: " + result.stderr
        )

    def test_break_mismatched_capsule_id_is_rejected(self, tmp_path: Path) -> None:
        """--capsule must match the active lock's run_id; mismatch exits 1."""
        runtime = _runtime(tmp_path)
        run_id = "actual-capsule-id"
        _write_lock(
            runtime,
            {
                "run_id": run_id,
                "pid": os.getpid(),
                "expires_at_epoch": int(time.time()) + 600,
                "started_at_epoch": int(time.time()) - 60,
                "capsule_dir": str(tmp_path / "capsule"),
                "message": "mismatch test",
            },
        )

        result = _run_break(
            tmp_path,
            ["--capsule", "wrong-capsule-id", "--reason", "test mismatch", "--force"],
        )

        assert result.returncode == 1, (
            f"Expected 1 for capsule ID mismatch; got {result.returncode}"
        )
        assert "does not match" in result.stderr or "mismatch" in result.stderr.lower(), (
            "Error message must mention the mismatch; stderr: " + result.stderr
        )
        # Lock must still exist — not removed on mismatch.
        lock_path = runtime / "validation-capsule.lock"
        assert lock_path.exists(), "Mismatched break must not remove the lock"

    def test_break_with_valid_capsule_and_reason_removes_lock(self, tmp_path: Path) -> None:
        """Valid break removes the lock file."""
        runtime = _runtime(tmp_path)
        run_id = "unit-break-valid"
        # Use a dead PID so the script can proceed without killing a real process.
        dead_pid = 0  # pid=0 means no process to kill

        _write_lock(
            runtime,
            {
                "run_id": run_id,
                "pid": dead_pid,
                "expires_at_epoch": int(time.time()) - 10,  # expired
                "started_at_epoch": int(time.time()) - 300,
                "capsule_dir": str(tmp_path / "capsule"),
                "message": "valid break test",
            },
        )

        result = _run_break(
            tmp_path,
            [
                "--capsule", run_id,
                "--reason", "testing valid break",
                "--force",
                "--no-kill",
            ],
        )

        assert result.returncode == 0, (
            f"Expected 0 for valid break; got {result.returncode}. stderr={result.stderr}"
        )
        lock_path = runtime / "validation-capsule.lock"
        assert not lock_path.exists(), "Lock file must be removed after successful break"

    def test_break_writes_audit_jsonl_with_required_fields(self, tmp_path: Path) -> None:
        """Successful break appends an audit entry with all required fields."""
        runtime = _runtime(tmp_path)
        run_id = "unit-break-audit"

        _write_lock(
            runtime,
            {
                "run_id": run_id,
                "pid": 0,
                "expires_at_epoch": int(time.time()) - 10,
                "started_at_epoch": int(time.time()) - 300,
                "capsule_dir": str(tmp_path / "capsule"),
                "message": "audit fields test",
            },
        )

        reason_text = "testing audit trail completeness"
        result = _run_break(
            tmp_path,
            [
                "--capsule", run_id,
                "--reason", reason_text,
                "--force",
                "--no-kill",
            ],
        )

        assert result.returncode == 0, f"Break failed: {result.stderr}"

        audit_file = tmp_path / ".cognitive-os" / "audit" / "validation-breaks.jsonl"
        assert audit_file.exists(), f"Audit file not created at {audit_file}"

        entries = [json.loads(line) for line in audit_file.read_text().splitlines() if line.strip()]
        assert len(entries) >= 1, "Expected at least one audit entry"

        entry = entries[-1]
        required_fields = ("ts", "broken_capsule", "broken_pid", "reason", "stale_signals", "method")
        for field_name in required_fields:
            assert field_name in entry, f"Required audit field '{field_name}' missing; got {list(entry.keys())}"

        assert entry["broken_capsule"] == run_id
        assert entry["reason"] == reason_text
        assert isinstance(entry["stale_signals"], list)

    def test_break_audit_ts_is_iso8601_utc(self, tmp_path: Path) -> None:
        """Audit entry 'ts' must be an ISO-8601 UTC timestamp (YYYY-MM-DDTHH:MM:SSZ)."""
        import re

        runtime = _runtime(tmp_path)
        run_id = "unit-break-ts"

        _write_lock(
            runtime,
            {
                "run_id": run_id,
                "pid": 0,
                "expires_at_epoch": int(time.time()) - 10,
                "started_at_epoch": int(time.time()) - 300,
                "capsule_dir": str(tmp_path / "capsule"),
                "message": "ts format test",
            },
        )

        result = _run_break(
            tmp_path,
            [
                "--capsule", run_id,
                "--reason", "ts format check",
                "--force",
                "--no-kill",
            ],
        )
        assert result.returncode == 0

        audit_file = tmp_path / ".cognitive-os" / "audit" / "validation-breaks.jsonl"
        entries = [json.loads(line) for line in audit_file.read_text().splitlines() if line.strip()]
        ts = entries[-1]["ts"]

        pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"
        assert re.match(pattern, ts), f"Audit ts is not ISO-8601 UTC: {ts!r}"
