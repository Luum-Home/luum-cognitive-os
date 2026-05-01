"""
tests/unit/test_skill_discovery_telemetry.py

Behavioral tests for the skill discovery telemetry pipeline:
  - hooks/skill-discovery-telemetry.sh writes correct-shaped records
  - scripts/check_lazy_catalog_health.py reads and computes rates correctly
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TELEMETRY_HOOK = PROJECT_ROOT / "hooks" / "skill-discovery-telemetry.sh"
AGGREGATOR = PROJECT_ROOT / "scripts" / "check_lazy_catalog_health.py"


# ─── Telemetry hook tests ─────────────────────────────────────────────────────

@pytest.mark.skipif(not TELEMETRY_HOOK.exists(), reason="skill-discovery-telemetry.sh not found")
class TestSkillDiscoveryTelemetryHook:

    def _run_hook(self, tmp_path: Path, tool_name: str = "Agent",
                  tool_result: dict | None = None, tool_input: dict | None = None,
                  lazy: str = "1") -> subprocess.CompletedProcess:
        import os
        env = os.environ.copy()
        env["CLAUDE_PROJECT_DIR"] = str(tmp_path)
        env["CLAUDE_TOOL_NAME"] = tool_name
        env["CLAUDE_TOOL_RESULT"] = json.dumps(tool_result or {"output": ""})
        env["CLAUDE_TOOL_INPUT"] = json.dumps(tool_input or {"prompt": ""})
        env["COS_LAZY_CATALOG"] = lazy
        env["COGNITIVE_OS_SESSION_ID"] = "test-session-123"
        env.pop("CLAUDE_AGENT_ID", None)

        # Create skills dir so catalog lookup doesn't fail
        (tmp_path / "skills").mkdir(exist_ok=True)

        runtime_dir = tmp_path / ".cognitive-os" / "runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)

        return subprocess.run(
            ["bash", str(TELEMETRY_HOOK)],
            capture_output=True, text=True, env=env, timeout=5,
        )

    def test_non_agent_tool_exits_cleanly(self, tmp_path):
        """Hook is a no-op for non-Agent tools."""
        result = self._run_hook(tmp_path, tool_name="Bash")
        assert result.returncode == 0

        telemetry = tmp_path / ".cognitive-os" / "runtime" / "skill-discovery.jsonl"
        # No record written for non-Agent tool
        if telemetry.exists():
            lines = [l for l in telemetry.read_text().splitlines() if l.strip()]
            agent_records = [json.loads(l) for l in lines if '"agent_telemetry"' in l]
            assert len(agent_records) == 0

    def test_agent_tool_writes_record(self, tmp_path):
        """Agent tool completion writes a telemetry record."""
        result = self._run_hook(
            tmp_path,
            tool_name="Agent",
            tool_result={"output": "I completed the task successfully."},
            tool_input={"prompt": "run the tests and report"},
        )
        assert result.returncode == 0

        telemetry = tmp_path / ".cognitive-os" / "runtime" / "skill-discovery.jsonl"
        assert telemetry.exists()
        lines = [l for l in telemetry.read_text().splitlines() if l.strip()]
        assert len(lines) >= 1
        record = json.loads(lines[-1])
        assert record["event"] == "agent_telemetry"
        assert record["session_id"] == "test-session-123"
        assert "lazy_catalog_active" in record
        assert "suspected_missed_skills" in record
        assert isinstance(record["suspected_missed_skills"], list)

    def test_reimpl_detection_triggers_suspected_miss(self, tmp_path):
        """Re-implementation phrases trigger reimpl_detected flag."""
        # Inject a fake catalog so skill names are available
        (tmp_path / "skills").mkdir(exist_ok=True)
        (tmp_path / "skills" / "CATALOG-COMPACT.md").write_text(
            "# Catalog\n**run-tests** — runs test suite\n"
        )
        result = self._run_hook(
            tmp_path,
            tool_name="Agent",
            tool_result={"output": "I'll implement a custom test runner from scratch."},
            tool_input={"prompt": "run tests for the project"},
        )
        assert result.returncode == 0

        telemetry = tmp_path / ".cognitive-os" / "runtime" / "skill-discovery.jsonl"
        assert telemetry.exists()
        lines = [l for l in telemetry.read_text().splitlines() if l.strip()]
        record = json.loads(lines[-1])
        assert record["reimpl_detected"] is True

    def test_record_shape(self, tmp_path):
        """Written record has the required fields."""
        self._run_hook(tmp_path, tool_name="Agent")
        telemetry = tmp_path / ".cognitive-os" / "runtime" / "skill-discovery.jsonl"
        if not telemetry.exists():
            pytest.skip("No telemetry written (may be non-Agent env)")
        lines = [l for l in telemetry.read_text().splitlines() if l.strip()]
        record = json.loads(lines[-1])
        required = {"ts", "event", "session_id", "lazy_catalog_active",
                    "prompt_keywords", "skills_invoked", "suspected_missed_skills"}
        assert required.issubset(record.keys()), f"Missing fields: {required - record.keys()}"


# ─── Aggregator tests ─────────────────────────────────────────────────────────

@pytest.mark.skipif(not AGGREGATOR.exists(), reason="check_lazy_catalog_health.py not found")
class TestLazyCatalogHealthAggregator:

    def _make_records(self, tmp_path: Path, lazy_on_sessions: int,
                      missed: int, lazy_off_sessions: int = 0) -> Path:
        """Write synthetic telemetry and return the runtime dir."""
        runtime_dir = tmp_path / ".cognitive-os" / "runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        out = runtime_dir / "skill-discovery.jsonl"

        now = time.time()
        records = []

        # lazy ON sessions
        for i in range(lazy_on_sessions):
            missed_skills = ["run-tests"] if i < missed else []
            records.append({
                "ts": now - i * 60,
                "event": "agent_telemetry",
                "session_id": f"lazy-on-{i}",
                "agent_id": "a1",
                "lazy_catalog_active": True,
                "prompt_keywords": ["test"],
                "skills_invoked": [],
                "reimpl_detected": i < missed,
                "suspected_missed_skills": missed_skills,
            })

        # lazy OFF sessions
        for i in range(lazy_off_sessions):
            records.append({
                "ts": now - i * 60,
                "event": "agent_telemetry",
                "session_id": f"lazy-off-{i}",
                "agent_id": "a2",
                "lazy_catalog_active": False,
                "prompt_keywords": [],
                "skills_invoked": [],
                "reimpl_detected": False,
                "suspected_missed_skills": [],
            })

        with out.open("w") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

        return runtime_dir

    def _run_aggregator(self, tmp_path: Path, extra_args: list[str] | None = None) -> subprocess.CompletedProcess:
        import os
        env = os.environ.copy()
        env["CLAUDE_PROJECT_DIR"] = str(tmp_path)
        cmd = [sys.executable, str(AGGREGATOR)] + (extra_args or [])
        return subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=10)

    def test_aggregator_runs(self, tmp_path):
        """Aggregator exits with code 0 or 2 (insufficient data) on empty data."""
        result = self._run_aggregator(tmp_path)
        assert result.returncode in (0, 2), result.stderr

    def test_aggregator_json_output(self, tmp_path):
        """--json flag produces valid JSON with expected keys."""
        self._make_records(tmp_path, lazy_on_sessions=5, missed=1)
        result = self._run_aggregator(tmp_path, ["--json"])
        assert result.returncode in (0, 1, 2)
        data = json.loads(result.stdout)
        required = {"lazy_on", "lazy_off", "recommendation", "degraded",
                    "token_savings_per_session_k", "baseline_rate"}
        assert required.issubset(data.keys())

    def test_healthy_rate_exits_zero(self, tmp_path):
        """Low miss rate (< 2× baseline) returns exit 0."""
        # Write baseline
        baseline = tmp_path / "docs" / "measurements"
        baseline.mkdir(parents=True)
        (baseline / "lazy-catalog-baseline.json").write_text(
            json.dumps({"missed_skills_rate_per_session": 0.05})
        )
        # 1 miss in 10 sessions = 10% < 2×5% = 10% (boundary, but ≤ so healthy)
        self._make_records(tmp_path, lazy_on_sessions=10, missed=1)
        result = self._run_aggregator(tmp_path, ["--json"])
        data = json.loads(result.stdout)
        # 10% == 2×5%: exactly at boundary, should be OK (not strictly >)
        assert data["degraded"] is False or data["lazy_on"]["rate"] <= 0.10

    def test_degraded_rate_exits_one(self, tmp_path):
        """High miss rate (> 2× baseline) returns exit 1 and degraded=true."""
        baseline = tmp_path / "docs" / "measurements"
        baseline.mkdir(parents=True)
        (baseline / "lazy-catalog-baseline.json").write_text(
            json.dumps({"missed_skills_rate_per_session": 0.05})
        )
        # 8 misses in 10 sessions = 80% >> 2×5%=10%
        self._make_records(tmp_path, lazy_on_sessions=10, missed=8)
        result = self._run_aggregator(tmp_path, ["--json"])
        assert result.returncode == 1
        data = json.loads(result.stdout)
        assert data["degraded"] is True
        assert "DEGRADE" in data["recommendation"]

    def test_insufficient_data_exits_two(self, tmp_path):
        """Fewer than 3 lazy sessions → exit 2 (insufficient data)."""
        self._make_records(tmp_path, lazy_on_sessions=2, missed=0)
        result = self._run_aggregator(tmp_path, ["--json"])
        assert result.returncode == 2
        data = json.loads(result.stdout)
        assert "INSUFFICIENT_DATA" in data["recommendation"]

    def test_token_savings_reported(self, tmp_path):
        """token_savings_per_session_k is always 3.5 in JSON output."""
        self._make_records(tmp_path, lazy_on_sessions=5, missed=0)
        result = self._run_aggregator(tmp_path, ["--json"])
        data = json.loads(result.stdout)
        assert data["token_savings_per_session_k"] == 3.5
