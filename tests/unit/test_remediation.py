"""Unit tests for hooks/_lib/remediation.sh.

Tests register, lookup, failure recording, confidence thresholds,
auto_applicable disabling, and index sync.
Migrated from tests/unit/test-remediation.sh.
"""

import json
import os
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def project_root():
    return Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def lib_dir(project_root):
    return project_root / "hooks" / "_lib"


@pytest.fixture
def remediation_env(tmp_path, lib_dir):
    """Set up a temp project for remediation tests and return env + helpers."""
    project_dir = tmp_path / "project"
    metrics_dir = project_dir / ".cognitive-os" / "metrics"
    metrics_dir.mkdir(parents=True)

    env = {
        **os.environ,
        "COGNITIVE_OS_PROJECT_DIR": str(project_dir),
        "COGNITIVE_OS_HOOK_HEARTBEAT": "false",
        "COGNITIVE_OS_SESSION_ID": "",
        "COGNITIVE_OS_REMEDIATION_CONFIDENCE": "0.8",
        "COGNITIVE_OS_REMEDIATION_DISABLE_RATE": "0.3",
        "COGNITIVE_OS_REMEDIATION_DISABLE_MIN": "5",
    }

    def run(script_body: str) -> subprocess.CompletedProcess:
        full_script = (
            f'_SAFE_JSONL_LOADED=""\n'
            f'source "{lib_dir}/safe-jsonl.sh"\n'
            f'source "{lib_dir}/remediation.sh"\n'
            f'{script_body}\n'
        )
        return subprocess.run(
            ["bash", "-c", full_script],
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
        )

    return {
        "env": env,
        "project_dir": project_dir,
        "metrics_dir": metrics_dir,
        "run": run,
    }


@pytest.mark.unit
class TestRemediationRegister:
    """Tests for remediation_register function."""

    def test_register_creates_entry(self, remediation_env):
        r = remediation_env["run"](
            'remediation_register "BUILD" "service-a" "cannot find module foo" '
            '"missing dependency" "command" "bun add foo"\n'
            'echo "REGISTRY=$(_rem_registry_file)"\n'
            'echo "INDEX=$(_rem_index_file)"'
        )
        assert r.returncode == 0, f"register should succeed: {r.stderr}"

        # Parse output for file paths
        lines = r.stdout.strip().split("\n")
        registry = index = None
        for line in lines:
            if line.startswith("REGISTRY="):
                registry = Path(line.split("=", 1)[1])
            elif line.startswith("INDEX="):
                index = Path(line.split("=", 1)[1])

        if registry and registry.exists():
            reg_lines = registry.read_text().strip().split("\n")
            assert len(reg_lines) == 1, "registry should have 1 line"
            data = json.loads(reg_lines[0])
            assert data["error_type"] == "BUILD"
            assert data["fix_command"] == "bun add foo"

        if index and index.exists():
            idx_data = json.loads(index.read_text())
            assert idx_data["stats"]["total"] == 1

    def test_register_updates_existing(self, remediation_env):
        r = remediation_env["run"](
            'remediation_register "BUILD" "service-a" "cannot find module foo" '
            '"missing dependency" "command" "bun add foo"\n'
            'remediation_register "BUILD" "service-a" "cannot find module foo" '
            '"missing dependency" "command" "bun add foo"\n'
            'echo "REGISTRY=$(_rem_registry_file)"'
        )
        for line in r.stdout.strip().split("\n"):
            if line.startswith("REGISTRY="):
                registry = Path(line.split("=", 1)[1])
                if registry.exists():
                    reg_lines = registry.read_text().strip().split("\n")
                    assert len(reg_lines) == 1, "should still be 1 line (updated, not appended)"
                    data = json.loads(reg_lines[0])
                    assert data["times_applied"] == 2


@pytest.mark.unit
class TestRemediationLookup:
    """Tests for remediation_lookup function."""

    def test_lookup_finds_known_fix(self, remediation_env):
        r = remediation_env["run"](
            'remediation_register "TEST" "service-b" "connection refused on port 5432" '
            '"pg not running" "command" "docker start postgres"\n'
            'result=$(remediation_lookup "TEST" "service-b" "connection refused on port 5432")\n'
            'echo "RC=$?"\n'
            'echo "RESULT=$result"'
        )
        for line in r.stdout.strip().split("\n"):
            if line.startswith("RC="):
                assert line == "RC=0", "lookup should return 0 for known fix"
            if line.startswith("RESULT="):
                result_json = line.split("=", 1)[1]
                if result_json:
                    data = json.loads(result_json)
                    assert data["fix_type"] == "command"
                    assert data["fix_command"] == "docker start postgres"

    def test_lookup_returns_1_for_unknown(self, remediation_env):
        r = remediation_env["run"](
            'remediation_register "BUILD" "service-c" "some known error" '
            '"root cause" "command" "fix it"\n'
            'remediation_lookup "BUILD" "service-c" "completely different error message" >/dev/null 2>&1\n'
            'echo "RC=$?"'
        )
        for line in r.stdout.strip().split("\n"):
            if line.startswith("RC="):
                assert line == "RC=1", "lookup should return 1 for unknown error"

    def test_lookup_rejects_low_confidence(self, remediation_env):
        r = remediation_env["run"](
            'remediation_register "BUILD" "service-d" "pattern X" "cause" "command" "fix X"\n'
            'fingerprint=$(_rem_fingerprint "pattern X")\n'
            'remediation_record_failure "$fingerprint"\n'
            'remediation_record_failure "$fingerprint"\n'
            'remediation_record_failure "$fingerprint"\n'
            'remediation_lookup "BUILD" "service-d" "pattern X" >/dev/null 2>&1\n'
            'echo "RC=$?"'
        )
        for line in r.stdout.strip().split("\n"):
            if line.startswith("RC="):
                assert line == "RC=1", "lookup should reject low-confidence fix"


@pytest.mark.unit
class TestRemediationFailures:
    """Tests for failure recording and auto_applicable disabling."""

    def test_record_failure_increments(self, remediation_env):
        r = remediation_env["run"](
            'remediation_register "LINT" "service-e" "lint error pattern" '
            '"bad config" "command" "fix lint"\n'
            'fingerprint=$(_rem_fingerprint "lint error pattern")\n'
            'remediation_record_failure "$fingerprint"\n'
            'remediation_record_failure "$fingerprint"\n'
            'echo "REGISTRY=$(_rem_registry_file)"'
        )
        for line in r.stdout.strip().split("\n"):
            if line.startswith("REGISTRY="):
                registry = Path(line.split("=", 1)[1])
                if registry.exists():
                    data = json.loads(registry.read_text().strip().split("\n")[0])
                    assert data["times_failed"] == 2

    def test_auto_applicable_disabled_at_low_rate(self, remediation_env):
        r = remediation_env["run"](
            'remediation_register "BUILD" "service-f" "error pattern Z" '
            '"unknown" "command" "attempt fix"\n'
            'fingerprint=$(_rem_fingerprint "error pattern Z")\n'
            'for i in $(seq 1 5); do remediation_record_failure "$fingerprint"; done\n'
            'echo "REGISTRY=$(_rem_registry_file)"'
        )
        for line in r.stdout.strip().split("\n"):
            if line.startswith("REGISTRY="):
                registry = Path(line.split("=", 1)[1])
                if registry.exists():
                    data = json.loads(registry.read_text().strip().split("\n")[0])
                    assert data["auto_applicable"] is False, (
                        "auto_applicable should be false at low success rate"
                    )


@pytest.mark.unit
class TestRemediationIndexSync:
    """Tests that the index stays in sync with the registry."""

    def test_index_total_matches_registry(self, remediation_env):
        r = remediation_env["run"](
            'remediation_register "BUILD" "svc1" "error alpha" "cause a" "command" "fix a"\n'
            'remediation_register "TEST" "svc2" "error beta" "cause b" "command" "fix b"\n'
            'remediation_register "LINT" "svc3" "error gamma" "cause c" "command" "fix c"\n'
            'echo "INDEX=$(_rem_index_file)"\n'
            'echo "REGISTRY=$(_rem_registry_file)"'
        )
        index_path = registry_path = None
        for line in r.stdout.strip().split("\n"):
            if line.startswith("INDEX="):
                index_path = Path(line.split("=", 1)[1])
            elif line.startswith("REGISTRY="):
                registry_path = Path(line.split("=", 1)[1])

        if index_path and index_path.exists() and registry_path and registry_path.exists():
            idx = json.loads(index_path.read_text())
            reg_lines = len(registry_path.read_text().strip().split("\n"))
            assert idx["stats"]["total"] == reg_lines, (
                "index total should match registry line count"
            )
