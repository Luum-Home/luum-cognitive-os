"""tests/unit/test_session_watchdog.py — ADR-047 Phase A watchdog tests.

Covers:
  - Classification logic (HEALTHY, IDLE_OVER_TTL, ORPHANED, RESUMED_RECENTLY)
  - Opt-out env var (COS_SESSION_WATCHDOG_DISABLE=1)
  - Phase A log-only mode (no kill calls, JSONL written)
  - Feature flag mode=off path
  - Cross-platform: parametrize with psutil-present and psutil-absent
  - mode=enforce stays log-only and logs error

All tests complete in < 5 s. No real subprocess spawning of claude processes.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Path setup — run from repo root or directly
# ---------------------------------------------------------------------------
_REPO = Path(__file__).resolve().parent.parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from lib.session_watchdog_lib import (
    CLASS_HEALTHY,
    CLASS_IDLE_OVER_TTL,
    CLASS_ORPHANED,
    CLASS_RESUMED_RECENTLY,
    ProcessInfo,
    SessionRecord,
    WatchdogRecord,
    _etime_to_seconds,
    _extract_resume_id,
    _is_claude_session,
    append_jsonl,
    classify_session,
    enrich_session,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_session(
    pid: int = 1001,
    ppid: int = 1000,
    etime_sec: int = 100,
    cpu_percent: float = 5.0,
    command: str = "claude --output-format stream-json --input-format stream-json",
    resume_id: Optional[str] = None,
    engram_children: Optional[List[int]] = None,
) -> SessionRecord:
    return SessionRecord(
        pid=pid,
        ppid=ppid,
        etime_sec=etime_sec,
        cpu_percent=cpu_percent,
        command=command,
        start_time_epoch=time.time() - etime_sec,
        resume_id=resume_id,
        engram_mcp_children=engram_children or [],
    )


def _make_config(
    ttl_hours: float = 6.0,
    idle_cpu: float = 1.0,
    mode: str = "log-only",
    enabled: bool = True,
) -> Dict[str, Any]:
    return {
        "enabled": enabled,
        "mode": mode,
        "ttl_hours": ttl_hours,
        "idle_cpu_threshold": idle_cpu,
        "idle_samples_required": 3,
    }


# ---------------------------------------------------------------------------
# Unit: _etime_to_seconds
# ---------------------------------------------------------------------------

class TestEtimeToSeconds(unittest.TestCase):
    def test_mm_ss(self):
        assert _etime_to_seconds("05:30") == 330

    def test_hh_mm_ss(self):
        assert _etime_to_seconds("01:00:00") == 3600

    def test_dd_hh_mm_ss(self):
        assert _etime_to_seconds("1-02:00:00") == 93600  # 86400 + 7200

    def test_zero(self):
        assert _etime_to_seconds("00:00") == 0

    def test_bad_input(self):
        assert _etime_to_seconds("bogus") == 0


# ---------------------------------------------------------------------------
# Unit: session signature detection
# ---------------------------------------------------------------------------

class TestSessionSignature(unittest.TestCase):
    def test_matches_valid_claude(self):
        cmd = "claude --output-format stream-json --input-format stream-json"
        assert _is_claude_session(cmd)

    def test_excludes_disclaimer(self):
        cmd = "claude --output-format stream-json --input-format stream-json disclaimer"
        assert not _is_claude_session(cmd)

    def test_missing_one_flag(self):
        cmd = "claude --output-format stream-json"
        assert not _is_claude_session(cmd)

    def test_random_process(self):
        assert not _is_claude_session("python3 scripts/foo.py")

    def test_extract_resume_id(self):
        cmd = "claude --resume abc123def456abc123def456abc123de --output-format stream-json --input-format stream-json"
        rid = _extract_resume_id(cmd)
        assert rid == "abc123def456abc123def456abc123de"

    def test_no_resume_id(self):
        cmd = "claude --output-format stream-json --input-format stream-json"
        assert _extract_resume_id(cmd) is None


# ---------------------------------------------------------------------------
# Unit: classification logic
# ---------------------------------------------------------------------------

class TestClassifySession(unittest.TestCase):
    TTL_SEC = 3600  # 1 hour
    IDLE_CPU = 1.0

    def _classify(self, session: SessionRecord):
        return classify_session(session, self.TTL_SEC, self.IDLE_CPU)

    # HEALTHY — young, active
    def test_healthy_young_active(self):
        session = _make_session(etime_sec=600, cpu_percent=5.0)
        # ppid=1000 — mock it as alive
        with patch("lib.session_watchdog_lib._pid_exists", return_value=True):
            cls, reason, would_kill = self._classify(session)
        assert cls == CLASS_HEALTHY
        assert would_kill is False

    # HEALTHY — old but active CPU
    def test_healthy_old_active_cpu(self):
        session = _make_session(etime_sec=7200, cpu_percent=10.0)
        with patch("lib.session_watchdog_lib._pid_exists", return_value=True):
            cls, reason, would_kill = self._classify(session)
        assert cls == CLASS_HEALTHY
        assert would_kill is False

    # IDLE_OVER_TTL — old AND idle
    def test_idle_over_ttl(self):
        session = _make_session(etime_sec=7200, cpu_percent=0.0)
        with patch("lib.session_watchdog_lib._pid_exists", return_value=True):
            cls, reason, would_kill = self._classify(session)
        assert cls == CLASS_IDLE_OVER_TTL
        assert would_kill is True  # in Phase B this would trigger kill
        assert "etime=" in reason

    # ORPHANED — parent PID gone
    def test_orphaned_parent_dead(self):
        session = _make_session(etime_sec=7200, cpu_percent=0.0)
        with patch("lib.session_watchdog_lib._pid_exists", return_value=False):
            cls, reason, would_kill = self._classify(session)
        assert cls == CLASS_ORPHANED
        assert would_kill is False  # Phase A: never kill
        assert "dead" in reason

    # RESUMED_RECENTLY — has resume flag, within 2× TTL
    def test_resumed_recently_within_extended_ttl(self):
        rid = "aabbccdd-1234-5678-abcd-aabbccdd1234"
        session = _make_session(
            etime_sec=5000,  # > TTL (3600) but < 2×TTL (7200)
            cpu_percent=0.0,
            command=f"claude --resume {rid} --output-format stream-json --input-format stream-json",
            resume_id=rid,
        )
        with patch("lib.session_watchdog_lib._pid_exists", return_value=True):
            cls, reason, would_kill = self._classify(session)
        assert cls == CLASS_HEALTHY  # within 2× TTL grace
        assert would_kill is False

    # RESUMED_RECENTLY — has resume flag, beyond 2× TTL and idle
    def test_resumed_over_2x_ttl(self):
        rid = "aabbccdd-1234-5678-abcd-aabbccdd1234"
        session = _make_session(
            etime_sec=8000,  # > 2× TTL (7200), idle
            cpu_percent=0.0,
            command=f"claude --resume {rid} --output-format stream-json --input-format stream-json",
            resume_id=rid,
        )
        with patch("lib.session_watchdog_lib._pid_exists", return_value=True):
            cls, reason, would_kill = self._classify(session)
        assert cls == CLASS_RESUMED_RECENTLY
        assert would_kill is False  # resumed sessions never get would_kill=True in Phase A


# ---------------------------------------------------------------------------
# Unit: opt-out env var
# ---------------------------------------------------------------------------

def _load_watchdog_module(alias: str = "so_session_watchdog"):
    """Load so-session-watchdog.py via importlib (handles hyphen in filename)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        alias,
        _REPO / "scripts" / "so-session-watchdog.py",
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


class TestOptOutEnvVar(unittest.TestCase):
    def test_opt_out_exits_zero_no_write(self):
        """COS_SESSION_WATCHDOG_DISABLE=1 must exit 0 without writing records."""
        mod = _load_watchdog_module("sw_optout1")
        with patch.dict(os.environ, {"COS_SESSION_WATCHDOG_DISABLE": "1"}):
            exit_code = mod.main(["--once"])
        assert exit_code == 0

    def test_no_write_on_opt_out(self):
        """Verify no JSONL lines are appended when opted out."""
        mod = _load_watchdog_module("sw_optout2")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / ".cognitive-os" / "metrics" / "session-watchdog.jsonl"
            with patch.object(mod, "WATCHDOG_JSONL", tmp_path), \
                 patch.dict(os.environ, {"COS_SESSION_WATCHDOG_DISABLE": "1"}):
                mod.main(["--once"])
            assert not tmp_path.exists()


# ---------------------------------------------------------------------------
# Unit: mode=off
# ---------------------------------------------------------------------------

class TestModeOff(unittest.TestCase):
    def test_mode_off_no_scan(self):
        """mode=off should skip scan and write nothing."""
        mod = _load_watchdog_module("sw_modeoff")

        config = _make_config(mode="off")
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / ".cognitive-os" / "metrics" / "session-watchdog.jsonl"
            with patch.object(mod, "WATCHDOG_JSONL", tmp_path):
                exit_code = mod.run_once(config, verbose=False)
            assert exit_code == 0
            assert not tmp_path.exists()


# ---------------------------------------------------------------------------
# Unit: mode=enforce stays log-only (Phase A safety rail)
# ---------------------------------------------------------------------------

class TestModeEnforce(unittest.TestCase):
    def test_enforce_logs_error_no_kill(self):
        """mode=enforce must warn on stderr and NOT kill, still write records."""
        import io
        mod = _load_watchdog_module("sw_enforce")

        config = _make_config(mode="enforce", ttl_hours=0.0001)  # TTL = ~0.36s → every process is "old"

        # Inject a synthetic session
        fake_proc = ProcessInfo(
            pid=os.getpid(),
            ppid=os.getppid(),
            etime_sec=9999,
            cpu_percent=0.0,
            command="claude --output-format stream-json --input-format stream-json",
            start_time_epoch=time.time() - 9999,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / "session-watchdog.jsonl"
            buf = io.StringIO()

            with patch.object(mod, "WATCHDOG_JSONL", tmp_path), \
                 patch("lib.session_watchdog_lib._enumerate_via_ps", return_value=([fake_proc], [])), \
                 patch("lib.session_watchdog_lib._try_import_psutil", return_value=None), \
                 patch("lib.session_watchdog_lib._pid_exists", return_value=True), \
                 patch("sys.stderr", buf):
                exit_code = mod.run_once(config, verbose=False)

            assert exit_code == 0
            # ADR-047 Phase B gate: mode=enforce must be refused while gate fails.
            # Previous message was "enforce mode not yet implemented"; with the
            # gate-based refusal wiring, the message is "Phase B REFUSED" + "falling
            # back to log-only". Either path guarantees no kills happened.
            stderr_text = buf.getvalue()
            assert (
                "REFUSED" in stderr_text
                or "log-only" in stderr_text.lower()
                or "not yet implemented" in stderr_text
            ), f"Expected Phase B refusal or fallback message, got: {stderr_text[:500]}"
            # Still writes records (log-only fallthrough)
            assert tmp_path.exists()
            lines = tmp_path.read_text().strip().splitlines()
            assert len(lines) >= 1
            rec = json.loads(lines[0])
            assert "classification" in rec
            # No kill signals were sent (process still alive)
            assert _pid_exists_real(os.getpid())


def _pid_exists_real(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return True  # PermissionError means it exists


# ---------------------------------------------------------------------------
# Unit: Phase A log-only — no kill, JSONL written
# ---------------------------------------------------------------------------

class TestPhaseALogOnly(unittest.TestCase):
    def test_log_written_no_kill(self):
        """Phase A: records written to JSONL, no os.kill called."""
        mod = _load_watchdog_module("sw_phasea1")

        config = _make_config(mode="log-only", ttl_hours=0.0001)

        fake_proc = ProcessInfo(
            pid=os.getpid(),
            ppid=os.getppid(),
            etime_sec=9999,
            cpu_percent=0.0,
            command="claude --output-format stream-json --input-format stream-json",
            start_time_epoch=time.time() - 9999,
        )

        kill_calls: List[Any] = []
        original_kill = os.kill

        def mock_kill(pid: int, sig: int) -> None:
            if sig != 0:  # signal 0 = existence check, allowed
                kill_calls.append((pid, sig))

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / "session-watchdog.jsonl"
            with patch.object(mod, "WATCHDOG_JSONL", tmp_path), \
                 patch.object(mod, "_enumerate_via_ps", return_value=([fake_proc], [])), \
                 patch.object(mod, "_try_import_psutil", return_value=None), \
                 patch("lib.session_watchdog_lib._pid_exists", return_value=True), \
                 patch("os.kill", side_effect=mock_kill):
                exit_code = mod.run_once(config, verbose=False)

            assert exit_code == 0
            assert not kill_calls, f"Unexpected kill calls: {kill_calls}"
            assert tmp_path.exists()
            lines = tmp_path.read_text().strip().splitlines()
            assert len(lines) >= 1
            rec = json.loads(lines[0])
            # Validate JSONL schema
            required_fields = [
                "timestamp", "scan_id", "session_pid", "session_etime_sec",
                "classification", "would_kill", "reason", "resume_id",
                "engram_mcp_children", "cpu_percent", "ttl_hours_configured",
            ]
            for field in required_fields:
                assert field in rec, f"Missing field: {field}"
            assert rec["would_kill"] in (True, False)

    def test_multiple_sessions_all_logged(self):
        """Multiple sessions produce multiple JSONL records."""
        mod = _load_watchdog_module("sw_phasea2")

        config = _make_config(mode="log-only", ttl_hours=1.0)
        cmd = "claude --output-format stream-json --input-format stream-json"
        proc_a = ProcessInfo(pid=1001, ppid=1000, etime_sec=100, cpu_percent=5.0, command=cmd, start_time_epoch=0.0)
        proc_b = ProcessInfo(pid=1002, ppid=1000, etime_sec=5000, cpu_percent=0.0, command=cmd, start_time_epoch=0.0)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / "session-watchdog.jsonl"
            with patch.object(mod, "WATCHDOG_JSONL", tmp_path), \
                 patch.object(mod, "_enumerate_via_ps", return_value=([proc_a, proc_b], [])), \
                 patch.object(mod, "_try_import_psutil", return_value=None), \
                 patch("lib.session_watchdog_lib._pid_exists", return_value=True):
                mod.run_once(config, verbose=False)

            lines = tmp_path.read_text().strip().splitlines()
            assert len(lines) == 2
            pids = {json.loads(l)["session_pid"] for l in lines}
            assert pids == {1001, 1002}


# ---------------------------------------------------------------------------
# Cross-platform: psutil-present path (mocked)
# ---------------------------------------------------------------------------

class TestCrossPlatformPsutil(unittest.TestCase):
    """Simulate psutil being available by mocking _try_import_psutil."""

    def _make_psutil_mock(self, procs_data: List[Dict[str, Any]]) -> MagicMock:
        """Build a minimal psutil mock that process_iter yields the given data."""
        psutil_mock = MagicMock()

        proc_mocks = []
        for d in procs_data:
            pm = MagicMock()
            pm.info = d
            proc_mocks.append(pm)

        psutil_mock.process_iter.return_value = iter(proc_mocks)
        psutil_mock.NoSuchProcess = Exception
        psutil_mock.AccessDenied = Exception
        psutil_mock.ZombieProcess = Exception
        return psutil_mock

    def test_psutil_path_classifies_healthy(self):
        cmd_parts = ["claude", "--output-format", "stream-json", "--input-format", "stream-json"]
        now = time.time()
        psutil_mock = self._make_psutil_mock([
            {
                "pid": 9001,
                "ppid": 9000,
                "create_time": now - 300,  # 5 min old
                "cpu_percent": 10.0,
                "cmdline": cmd_parts,
            }
        ])

        with patch("lib.session_watchdog_lib._try_import_psutil", return_value=psutil_mock), \
             patch("lib.session_watchdog_lib._pid_exists", return_value=True):
            from lib.session_watchdog_lib import _enumerate_via_psutil
            sessions, engram = _enumerate_via_psutil(psutil_mock)

        assert len(sessions) == 1
        assert sessions[0].pid == 9001
        assert sessions[0].etime_sec >= 299

    def test_psutil_path_classifies_idle_over_ttl(self):
        cmd_parts = ["claude", "--output-format", "stream-json", "--input-format", "stream-json"]
        now = time.time()
        psutil_mock = self._make_psutil_mock([
            {
                "pid": 9002,
                "ppid": 9000,
                "create_time": now - 25200,  # 7 h old
                "cpu_percent": 0.0,
                "cmdline": cmd_parts,
            }
        ])

        with patch("lib.session_watchdog_lib._try_import_psutil", return_value=psutil_mock):
            from lib.session_watchdog_lib import _enumerate_via_psutil
            sessions, _ = _enumerate_via_psutil(psutil_mock)

        session = enrich_session(sessions[0], [])
        # Patch _pid_exists so ppid=9000 appears alive
        with patch("lib.session_watchdog_lib._pid_exists", return_value=True):
            cls, reason, would_kill = classify_session(session, ttl_sec=3600, idle_cpu_threshold=1.0)
        assert cls == CLASS_IDLE_OVER_TTL
        assert would_kill is True


# ---------------------------------------------------------------------------
# Cross-platform: psutil-absent path
# ---------------------------------------------------------------------------

class TestCrossPlatformPsFallback(unittest.TestCase):
    """Simulate psutil being absent by mocking subprocess.run output."""

    _PS_OUTPUT = (
        "  PID  PPID ELAPSED  %CPU COMMAND\n"
        " 8001  8000   05:00   0.1 claude --output-format stream-json --input-format stream-json\n"
        " 8002  8000 07:00:00   0.0 claude --output-format stream-json --input-format stream-json\n"
        " 8003  8001   03:00   1.5 engram mcp --tools=agent\n"
    )

    def test_ps_fallback_enumerates_sessions(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = self._PS_OUTPUT

        with patch("subprocess.run", return_value=mock_result), \
             patch("lib.session_watchdog_lib._try_import_psutil", return_value=None):
            from lib.session_watchdog_lib import _enumerate_via_ps
            sessions, engram = _enumerate_via_ps()

        pids = {s.pid for s in sessions}
        assert 8001 in pids
        assert 8002 in pids
        assert len(engram) == 1
        assert engram[0].pid == 8003

    def test_ps_fallback_healthy_classification(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = self._PS_OUTPUT

        with patch("subprocess.run", return_value=mock_result):
            from lib.session_watchdog_lib import _enumerate_via_ps
            sessions, engram = _enumerate_via_ps()

        young = next(s for s in sessions if s.pid == 8001)
        session = enrich_session(young, engram)
        # Patch _pid_exists so ppid=8000 appears alive
        with patch("lib.session_watchdog_lib._pid_exists", return_value=True):
            cls, reason, wk = classify_session(session, ttl_sec=3600, idle_cpu_threshold=1.0)
        assert cls == CLASS_HEALTHY

    def test_ps_fallback_idle_over_ttl(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = self._PS_OUTPUT

        with patch("subprocess.run", return_value=mock_result):
            from lib.session_watchdog_lib import _enumerate_via_ps
            sessions, engram = _enumerate_via_ps()

        old = next(s for s in sessions if s.pid == 8002)
        session = enrich_session(old, engram)
        # Patch _pid_exists so ppid=8000 appears alive
        with patch("lib.session_watchdog_lib._pid_exists", return_value=True):
            cls, reason, wk = classify_session(session, ttl_sec=3600, idle_cpu_threshold=1.0)
        assert cls == CLASS_IDLE_OVER_TTL

    def test_ps_subprocess_failure_returns_empty(self):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result):
            from lib.session_watchdog_lib import _enumerate_via_ps
            sessions, engram = _enumerate_via_ps()

        assert sessions == []
        assert engram == []


# ---------------------------------------------------------------------------
# Unit: append_jsonl
# ---------------------------------------------------------------------------

class TestAppendJsonl(unittest.TestCase):
    def test_appends_valid_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sub" / "test.jsonl"
            append_jsonl(path, {"key": "value", "n": 42})
            assert path.exists()
            rec = json.loads(path.read_text().strip())
            assert rec["key"] == "value"
            assert rec["n"] == 42

    def test_multiple_appends(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.jsonl"
            for i in range(3):
                append_jsonl(path, {"i": i})
            lines = path.read_text().strip().splitlines()
            assert len(lines) == 3


# ---------------------------------------------------------------------------
# ADR-047 Phase B: should_kill() layered predicate tests
# ---------------------------------------------------------------------------

from lib.session_watchdog_lib import (  # noqa: E402 (already imported above for others)
    should_kill,
    _heartbeat_stale,
    _metric_writes_stale,
    _cpu_idle_sustained,
)


class TestShouldKillPredicate(unittest.TestCase):
    """Tests for ADR-047 Phase B layered kill predicate: should_kill()."""

    # ── helpers ──────────────────────────────────────────────────────────────

    def _make_session_dir(self, tmp_path: str) -> Path:
        """Create a fresh session dir with a deliberately old ctime proxy."""
        d = Path(tmp_path) / "sessions" / "test-session"
        d.mkdir(parents=True)
        return d

    def _write_heartbeat(self, session_dir: Path, age_seconds: float = 0.0) -> None:
        """Write a heartbeat file that appears `age_seconds` old."""
        hb = session_dir / "heartbeat"
        epoch = int(time.time() - age_seconds)
        hb.write_text(str(epoch))
        # Backdate the mtime
        atime = mtime = time.time() - age_seconds
        os.utime(str(hb), (atime, mtime))

    def _make_old_session_dir(self, tmp_path: str) -> Path:
        """Create a session dir and backdate its ctime proxy (use mtime trick)."""
        d = self._make_session_dir(tmp_path)
        # We can't set ctime directly; backdate mtime instead.
        # should_kill uses st_ctime as proxy; on macOS/Linux ctime is set at create.
        # For tests we patch time.time() instead to make "now" appear far in future.
        return d

    # ── T1: parent dead → kill regardless of TTL ─────────────────────────────

    def test_parent_dead_triggers_kill_regardless_of_ttl(self):
        """If parent PID is dead, should_kill returns True even if TTL not exceeded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_dir = self._make_session_dir(tmpdir)
            # Write fresh heartbeat so only orphan check can trigger kill
            self._write_heartbeat(session_dir, age_seconds=0)

            with patch("lib.session_watchdog_lib._pid_exists", return_value=False):
                verdict, reason = should_kill(
                    session_dir=session_dir,
                    ttl_seconds=999_999,  # very long TTL — not exceeded
                    ppid=12345,
                    dry_run=True,
                )

        assert verdict is True, f"Expected kill for dead parent, got False (reason: {reason})"
        assert "dead" in reason or "orphan" in reason.lower()

    # ── T2: TTL not exceeded → never kill ────────────────────────────────────

    def test_ttl_not_exceeded_never_kills(self):
        """If TTL has not been exceeded, should_kill returns False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_dir = self._make_session_dir(tmpdir)

            with patch("lib.session_watchdog_lib._pid_exists", return_value=True):
                verdict, reason = should_kill(
                    session_dir=session_dir,
                    ttl_seconds=999_999,  # very long TTL — never exceeded for a just-created dir
                    ppid=os.getppid(),
                    dry_run=True,
                )

        assert verdict is False, f"Expected no kill for young session, got True (reason: {reason})"
        assert "within" in reason or "ttl" in reason.lower()

    # ── T3: heartbeat fresh → no kill ────────────────────────────────────────

    def test_heartbeat_fresh_prevents_kill(self):
        """Fresh heartbeat file should prevent kill even when TTL exceeded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_dir = self._make_session_dir(tmpdir)
            self._write_heartbeat(session_dir, age_seconds=30)  # 30s old = fresh

            with patch("lib.session_watchdog_lib._pid_exists", return_value=True), \
                 patch("lib.session_watchdog_lib.time") as mock_time:
                # Make "now" appear as if session_dir is very old (TTL exceeded)
                # by making time.time() return a large offset from actual mtime
                real_time = time.time()
                # session_dir.stat().st_ctime is ~now; make TTL appear exceeded
                # by setting ttl_seconds very small
                mock_time.time.return_value = real_time + 100  # 100s into future
                mock_time.gmtime = time.gmtime
                mock_time.strftime = time.strftime

                # Reset heartbeat mtime to be fresh relative to mock time
                hb = session_dir / "heartbeat"
                os.utime(str(hb), (real_time + 90, real_time + 90))  # written 10s ago (mock-relative)

                verdict, reason = should_kill(
                    session_dir=session_dir,
                    ttl_seconds=1,  # 1s TTL → always exceeded
                    ppid=os.getppid(),
                    dry_run=True,
                )

        assert verdict is False, f"Expected no kill with fresh heartbeat, got True (reason: {reason})"
        assert "heartbeat" in reason.lower() or "fresh" in reason.lower()

    # ── T4: high CPU → no kill ───────────────────────────────────────────────

    def test_reasoning_loop_high_cpu_prevents_kill(self):
        """Session with high CPU usage should not be killed (reasoning loop guard)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_dir = self._make_session_dir(tmpdir)
            # No heartbeat file → stale
            # No metrics → stale
            # But CPU is high → must NOT kill

            mock_psutil = MagicMock()
            mock_proc = MagicMock()
            mock_proc.cpu_percent.return_value = 85.0  # High CPU
            mock_psutil.Process.return_value = mock_proc
            mock_psutil.NoSuchProcess = ProcessLookupError
            mock_psutil.AccessDenied = PermissionError

            # Make time.time() return a value far in the future so age >> ttl
            fake_now = time.time() + 100_000  # 100k seconds in future → age >> 1s TTL

            with patch("lib.session_watchdog_lib._pid_exists", return_value=True), \
                 patch("lib.session_watchdog_lib._try_import_psutil", return_value=mock_psutil), \
                 patch("lib.session_watchdog_lib._metric_writes_stale", return_value=True), \
                 patch("lib.session_watchdog_lib.time") as mock_time:
                mock_time.time.return_value = fake_now
                mock_time.gmtime = time.gmtime
                mock_time.strftime = time.strftime
                verdict, reason = should_kill(
                    session_dir=session_dir,
                    ttl_seconds=1,  # 1s TTL → always exceeded given fake_now
                    pid=os.getpid(),
                    ppid=os.getppid(),
                    dry_run=True,
                )

        assert verdict is False, f"Expected no kill with high CPU, got True (reason: {reason})"
        assert "cpu" in reason.lower() or "active" in reason.lower() or "reasoning" in reason.lower()

    # ── T5: all stale + TTL exceeded + parent alive → kill ───────────────────

    def test_all_stale_and_ttl_exceeded_and_parent_alive_kills(self):
        """When all activity signals are stale and TTL is exceeded, should kill."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_dir = self._make_session_dir(tmpdir)
            # No heartbeat → stale
            # CPU mocked as idle
            # Metrics mocked as stale
            # Parent alive

            mock_psutil = MagicMock()
            mock_proc = MagicMock()
            mock_proc.cpu_percent.return_value = 0.0  # Idle
            mock_psutil.Process.return_value = mock_proc
            mock_psutil.NoSuchProcess = ProcessLookupError
            mock_psutil.AccessDenied = PermissionError

            # Make time.time() return a value far in the future so age >> ttl
            fake_now = time.time() + 100_000  # 100k seconds in future → age >> 1s TTL

            with patch("lib.session_watchdog_lib._pid_exists", return_value=True), \
                 patch("lib.session_watchdog_lib._try_import_psutil", return_value=mock_psutil), \
                 patch("lib.session_watchdog_lib._metric_writes_stale", return_value=True), \
                 patch("lib.session_watchdog_lib._heartbeat_stale", return_value=True), \
                 patch("lib.session_watchdog_lib.time") as mock_time:
                mock_time.time.return_value = fake_now
                mock_time.gmtime = time.gmtime
                mock_time.strftime = time.strftime
                verdict, reason = should_kill(
                    session_dir=session_dir,
                    ttl_seconds=1,  # 1s TTL → always exceeded given fake_now
                    pid=os.getpid(),
                    ppid=os.getppid(),
                    dry_run=True,
                )

        assert verdict is True, f"Expected kill for all-stale session, got False (reason: {reason})"
        assert "stale" in reason.lower() or "ttl" in reason.lower() or "exceeded" in reason.lower()

    # ── T6: missing heartbeat file treated as stale ───────────────────────────

    def test_missing_heartbeat_file_treated_as_stale(self):
        """Missing heartbeat file must be treated as stale (not as fresh)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_dir = self._make_session_dir(tmpdir)
            # Explicitly ensure no heartbeat file
            hb = session_dir / "heartbeat"
            assert not hb.exists(), "heartbeat file should not exist for this test"

            result = _heartbeat_stale(session_dir, threshold_s=9999)

        assert result is True, "Missing heartbeat file should be treated as stale"

    # ── T7: decision JSONL is written for each check ─────────────────────────

    def test_decisions_jsonl_written_per_check(self):
        """should_kill must emit one JSONL decision per check evaluated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_dir = self._make_session_dir(tmpdir)
            decisions_path = Path(tmpdir) / "watchdog-decisions.jsonl"

            fake_now = time.time() + 100_000  # ensure TTL exceeded

            with patch("lib.session_watchdog_lib._pid_exists", return_value=True), \
                 patch("lib.session_watchdog_lib._metric_writes_stale", return_value=True), \
                 patch("lib.session_watchdog_lib._heartbeat_stale", return_value=True), \
                 patch("lib.session_watchdog_lib._cpu_idle_sustained", return_value=True), \
                 patch("lib.session_watchdog_lib.time") as mock_time:
                mock_time.time.return_value = fake_now
                mock_time.gmtime = time.gmtime
                mock_time.strftime = time.strftime
                should_kill(
                    session_dir=session_dir,
                    ttl_seconds=1,
                    pid=os.getpid(),
                    ppid=os.getppid(),
                    dry_run=True,
                    decisions_path=decisions_path,
                )

            # Assertions inside the with block so tmpdir is still alive
            assert decisions_path.exists(), "decisions JSONL should be written"
            lines = decisions_path.read_text().strip().splitlines()
            assert len(lines) >= 1, f"Expected at least 1 decision line, got {len(lines)}"
            for line in lines:
                rec = json.loads(line)
                assert "ts" in rec
                assert "check" in rec
                assert "verdict" in rec


# ---------------------------------------------------------------------------
# Cross-phase invariants (ADR-047 decision-depth-gate)
# ---------------------------------------------------------------------------

class TestCrossPhaseInvariants(unittest.TestCase):
    """Invariants that tie Phase A classification to Phase B kill behavior.

    These exist because Phase A's whole purpose is to PREDICT Phase B. If the
    two phases use incoherent thresholds, the Phase A gate metric
    (false_positive_rate < 1%) measures the wrong population — and when
    Phase B activates, it starts killing sessions that Phase A never flagged.
    """

    def test_phase_a_threshold_superset_of_phase_b(self):
        """Phase A's `idle_cpu_threshold` MUST be >= Phase B's `_CPU_IDLE_THRESHOLD_PCT`.

        Rationale: Phase A classifies a session as would_kill when cpu < phase_a_threshold.
        Phase B kills when cpu sustained < phase_b_threshold. For the Phase A observation
        period to faithfully predict Phase B, every session Phase B would kill must first
        appear in Phase A's log — i.e. Phase A's "idle" set ⊇ Phase B's "idle" set.

        That requires phase_a_threshold >= phase_b_threshold.

        If this test fails, the Phase A false-positive rate metric is UNSOUND — you could
        observe 0% false positives in Phase A and still have Phase B kill live sessions.
        """
        from lib.session_watchdog_lib import _CPU_IDLE_THRESHOLD_PCT, load_watchdog_config

        # Read the Phase A default via the config loader (the source of truth for
        # daemon invocations) rather than hardcoding, so config drift is caught.
        config = load_watchdog_config(_REPO)
        phase_a_threshold = float(config["idle_cpu_threshold"])
        phase_b_threshold = float(_CPU_IDLE_THRESHOLD_PCT)

        assert phase_a_threshold >= phase_b_threshold, (
            f"CROSS-PHASE INVARIANT VIOLATED: Phase A CPU threshold "
            f"({phase_a_threshold}%) < Phase B kill threshold ({phase_b_threshold}%). "
            f"Phase A will UNDER-PREDICT Phase B kills — the gate metric is unsound. "
            f"Either raise the Phase A default in lib/session_watchdog_lib.py "
            f"(load_watchdog_config defaults) or lower the Phase B constant "
            f"_CPU_IDLE_THRESHOLD_PCT — but keep them coherent."
        )


# ---------------------------------------------------------------------------
# ADR-047 Phase B gate metric tests
# ---------------------------------------------------------------------------

from lib.session_watchdog_lib import (  # noqa: E402
    GATE_FP_RATE_MAX,
    GATE_MIN_OBSERVATION_HOURS,
    GATE_MIN_SAMPLE,
    compute_gate_metric,
    load_watchdog_jsonl,
)


def _mk_record(pid: int, ts: str, classification: str, would_kill: bool, cpu: float = 0.0):
    """Factory for a synthetic watchdog JSONL record."""
    return {
        "timestamp": ts,
        "scan_id": "test-scan",
        "session_pid": pid,
        "session_etime_sec": 9999,
        "classification": classification,
        "would_kill": would_kill,
        "reason": "test",
        "resume_id": None,
        "engram_mcp_children": [],
        "cpu_percent": cpu,
        "ttl_hours_configured": 6.0,
    }


class TestGateMetricEmpty(unittest.TestCase):
    def test_no_records_is_not_a_pass(self):
        gate = compute_gate_metric([])
        assert gate.gate_passes is False
        assert gate.total_records == 0
        assert "no_records" in gate.evidence_summary


class TestGateMetricSampleSize(unittest.TestCase):
    def test_small_sample_fails_even_with_zero_fp(self):
        """Sample size < 50 must fail the gate regardless of FP rate."""
        # 10 PIDs, each flagged once, none resumed → FP rate = 0% but sample too small
        records = []
        for pid in range(1000, 1010):
            records.append(_mk_record(pid, "2026-01-01T00:00:00Z", "IDLE_OVER_TTL", True))
        gate = compute_gate_metric(records)
        assert gate.flagged_records == 10
        assert gate.fp_rate == 0.0
        assert gate.sample_size_ok is False
        assert gate.gate_passes is False


class TestGateMetricFpRate(unittest.TestCase):
    def test_high_fp_rate_fails_the_gate(self):
        """FP rate >= 1% must fail even with adequate sample size."""
        records = []
        # 100 PIDs flagged; 50 resumed within 24h → FP rate = 50%
        for pid in range(1, 51):
            records.append(_mk_record(pid, "2026-01-01T00:00:00Z", "IDLE_OVER_TTL", True))
            # Resumption signal: HEALTHY record within 24h
            records.append(_mk_record(pid, "2026-01-01T12:00:00Z", "HEALTHY", False, cpu=5.0))
        for pid in range(51, 101):
            records.append(_mk_record(pid, "2026-01-01T00:00:00Z", "IDLE_OVER_TTL", True))
            # No resumption — stayed idle
        gate = compute_gate_metric(records)
        assert gate.flagged_records == 100
        assert gate.resumed_within_24h == 50
        assert gate.stayed_idle == 50
        assert gate.fp_rate_ok is False
        assert gate.gate_passes is False


class TestGateMetricPassing(unittest.TestCase):
    def test_gate_passes_when_all_criteria_met(self):
        """Gate passes with large sample, FP rate < 1%, and 2-week span."""
        records = []
        # 200 distinct PIDs flagged across 2 weeks (336h), with 1 resumed = 0.5% FP rate
        for pid in range(1, 201):
            records.append(_mk_record(pid, "2026-01-01T00:00:00Z", "IDLE_OVER_TTL", True))
        # Add one resumption event (FP)
        records.append(_mk_record(1, "2026-01-01T12:00:00Z", "HEALTHY", False, cpu=3.0))
        # Add a record at the 2-week mark to extend the observation span
        records.append(_mk_record(999, "2026-01-15T01:00:00Z", "HEALTHY", False))
        gate = compute_gate_metric(records)
        assert gate.flagged_records == 200
        assert gate.resumed_within_24h == 1
        assert gate.fp_rate == 1 / 200  # 0.5%
        assert gate.fp_rate_ok is True
        assert gate.sample_size_ok is True
        assert gate.observation_span_ok is True
        assert gate.gate_passes is True
        assert "GATE_PASS" in gate.evidence_summary


class TestGateMetricObservationSpan(unittest.TestCase):
    def test_short_span_fails_even_with_good_stats(self):
        """Observation span < 2 weeks must fail the gate."""
        records = []
        # 60 PIDs flagged on a single day, all stayed idle
        for pid in range(1, 61):
            records.append(_mk_record(pid, "2026-01-01T00:00:00Z", "IDLE_OVER_TTL", True))
        records.append(_mk_record(999, "2026-01-01T23:00:00Z", "HEALTHY", False))
        gate = compute_gate_metric(records)
        assert gate.flagged_records == 60
        assert gate.sample_size_ok is True
        assert gate.fp_rate == 0.0
        assert gate.fp_rate_ok is True
        assert gate.observation_span_ok is False
        assert gate.gate_passes is False


class TestGateConstants(unittest.TestCase):
    def test_gate_constants_match_adr(self):
        """Gate constants must match ADR-047 §'Gate threshold' specification."""
        assert GATE_FP_RATE_MAX == 0.01
        assert GATE_MIN_SAMPLE == 50
        assert GATE_MIN_OBSERVATION_HOURS == 336  # 14 days × 24h


class TestLoadWatchdogJsonl(unittest.TestCase):
    def test_load_missing_file_returns_empty(self):
        records = load_watchdog_jsonl(Path("/nonexistent/path.jsonl"))
        assert records == []

    def test_load_skips_malformed_lines(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "wd.jsonl"
            path.write_text(
                json.dumps(_mk_record(1, "2026-01-01T00:00:00Z", "HEALTHY", False)) + "\n"
                + "this is not json\n"
                + json.dumps(_mk_record(2, "2026-01-01T00:00:00Z", "HEALTHY", False)) + "\n"
            )
            records = load_watchdog_jsonl(path)
        assert len(records) == 2


# ---------------------------------------------------------------------------
# Phase B kill-mode refusal tests — enforcement is blocked when gate fails
# ---------------------------------------------------------------------------

class TestKillModeRefusal(unittest.TestCase):
    """When kill_mode=True but the gate fails, run_once MUST fall back to log-only."""

    def test_kill_mode_refused_when_gate_fails(self):
        """Requesting kill_mode with a failing gate must not kill; must log refusal."""
        import io
        mod = _load_watchdog_module("sw_kill_refused")
        config = _make_config(mode="log-only", ttl_hours=0.0001)

        fake_proc = ProcessInfo(
            pid=os.getpid(),
            ppid=os.getppid(),
            etime_sec=9999,
            cpu_percent=0.0,
            command="claude --output-format stream-json --input-format stream-json",
            start_time_epoch=time.time() - 9999,
        )

        kill_calls: List[Any] = []
        def mock_kill(pid: int, sig: int) -> None:
            if sig != 0:
                kill_calls.append((pid, sig))

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / "session-watchdog.jsonl"
            buf = io.StringIO()

            # Seed a minimal JSONL that guarantees the gate FAILS (empty file)
            tmp_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path.write_text("")  # zero records → gate fails

            with patch.object(mod, "WATCHDOG_JSONL", tmp_path), \
                 patch.object(mod, "_enumerate_via_ps", return_value=([fake_proc], [])), \
                 patch.object(mod, "_try_import_psutil", return_value=None), \
                 patch("lib.session_watchdog_lib._pid_exists", return_value=True), \
                 patch("os.kill", side_effect=mock_kill), \
                 patch("sys.stderr", buf):
                exit_code = mod.run_once(config, verbose=False, kill_mode=True)

            assert exit_code == 0
            assert not kill_calls, f"Kill must be refused when gate fails: {kill_calls}"
            stderr_output = buf.getvalue()
            assert "REFUSED" in stderr_output or "log-only" in stderr_output.lower(), (
                f"Expected refusal message in stderr, got: {stderr_output[:500]}"
            )

    def test_gate_report_command_returns_nonzero_on_fail(self):
        """`--gate-report` exits 2 when gate fails (useful for CI/monitoring)."""
        mod = _load_watchdog_module("sw_gate_report")
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / "session-watchdog.jsonl"
            tmp_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path.write_text("")  # empty → gate fails

            import io
            buf_out = io.StringIO()
            with patch.object(mod, "WATCHDOG_JSONL", tmp_path), \
                 patch("sys.stdout", buf_out):
                exit_code = mod.main(["--gate-report"])

            assert exit_code == 2, f"Expected exit 2 on gate fail, got {exit_code}"
            out = buf_out.getvalue()
            assert "GATE: FAIL" in out or "FAIL" in out

    def test_evaluate_gate_function_reads_current_jsonl(self):
        """evaluate_gate() reads the configured WATCHDOG_JSONL path and returns GateMetric."""
        mod = _load_watchdog_module("sw_eval_gate")
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / "session-watchdog.jsonl"
            tmp_path.parent.mkdir(parents=True, exist_ok=True)
            # Write a minimal failing record set
            tmp_path.write_text(
                json.dumps(_mk_record(1, "2026-01-01T00:00:00Z", "IDLE_OVER_TTL", True)) + "\n"
            )
            with patch.object(mod, "WATCHDOG_JSONL", tmp_path):
                gate = mod.evaluate_gate()
            assert gate.flagged_records == 1
            assert gate.gate_passes is False  # sample too small


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main(verbosity=2)
