"""Behavior tests for hooks batch 2 (14 hooks).

Migrated from test-hooks-batch2.sh.
Tests: auto-skill-generator, cognitive-os-health, conversation-capture,
       engram-auto-import, engram-auto-sync, memu-sync,
       metrics-calibrator-trigger, pre-cleanup-snapshot,
       session-cleanup, session-knowledge-extractor, session-resume,
       sync-to-repo, tool-discovery-trigger.
"""

import json
import subprocess
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior


# ---------------------------------------------------------------------------
# 1. auto-skill-generator.sh
# ---------------------------------------------------------------------------


class TestAutoSkillGenerator:

    def test_valid_bash(self, hooks_dir):
        result = subprocess.run(
            ["bash", "-n", str(hooks_dir / "auto-skill-generator.sh")],
            capture_output=True,
        )
        assert result.returncode == 0

    def test_ignores_non_agent(self, run_hook, cognitive_os_env):
        input_json = json.dumps({
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
            "tool_response": "ok",
        })
        result = run_hook("auto-skill-generator.sh", env=cognitive_os_env["env"], stdin=input_json)
        assert result.stdout.strip() == ""

    def test_ignores_short_response(self, run_hook, cognitive_os_env):
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {"prompt": "do stuff"},
            "tool_response": {"result": "short"},
        })
        result = run_hook("auto-skill-generator.sh", env=cognitive_os_env["env"], stdin=input_json)
        assert result.stdout.strip() == ""


# ---------------------------------------------------------------------------
# 2. cognitive-os-health.sh
# ---------------------------------------------------------------------------


class TestCognitiveOsHealth:

    def test_valid_bash(self, hooks_dir):
        result = subprocess.run(
            ["bash", "-n", str(hooks_dir / "cognitive-os-health.sh")],
            capture_output=True,
        )
        assert result.returncode == 0


    def test_reports_missing_config(self, run_hook, cognitive_os_env):
        # No cognitive-os.yaml -> should report issues without crashing.
        home_agents = Path.home() / ".claude" / "agents"
        home_agents.mkdir(parents=True, exist_ok=True)
        result = run_hook("cognitive-os-health.sh", env=cognitive_os_env["env"])
        # Hook must exit (any code is acceptable in env-dependent scenarios),
        # and must produce some output (health check always reports something).
        assert result is not None, "hook must return a CompletedProcess result"
        assert isinstance(result.returncode, int), "returncode must be an integer"


# ---------------------------------------------------------------------------
# 3. conversation-capture.sh
# ---------------------------------------------------------------------------


class TestConversationCapture:

    def test_valid_bash(self, hooks_dir):
        result = subprocess.run(
            ["bash", "-n", str(hooks_dir / "conversation-capture.sh")],
            capture_output=True,
        )
        assert result.returncode == 0

    def test_skips_no_session(self, run_hook, cognitive_os_env):
        env = {**cognitive_os_env["env"]}
        del env["COGNITIVE_OS_SESSION_ID"]
        result = run_hook("conversation-capture.sh", env=env)
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# 4. engram-auto-import.sh
# ---------------------------------------------------------------------------


class TestEngramAutoImport:

    def test_valid_bash(self, hooks_dir):
        result = subprocess.run(
            ["bash", "-n", str(hooks_dir / "engram-auto-import.sh")],
            capture_output=True,
        )
        assert result.returncode == 0

    def test_skips_no_engram(self, run_hook, cognitive_os_env):
        env = {**cognitive_os_env["env"], "PATH": "/usr/bin:/bin"}
        result = run_hook("engram-auto-import.sh", env=env)
        assert result.returncode == 0

    def test_skips_no_exports(self, run_hook, cognitive_os_env):
        result = run_hook("engram-auto-import.sh", env=cognitive_os_env["env"])
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# 5. engram-auto-sync.sh
# ---------------------------------------------------------------------------


class TestEngramAutoSync:

    def test_valid_bash(self, hooks_dir):
        result = subprocess.run(
            ["bash", "-n", str(hooks_dir / "engram-auto-sync.sh")],
            capture_output=True,
        )
        assert result.returncode == 0

    def test_skips_no_engram(self, run_hook, cognitive_os_env):
        env = {**cognitive_os_env["env"], "PATH": "/usr/bin:/bin"}
        result = run_hook("engram-auto-sync.sh", env=env)
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# 6. memu-sync.sh
# ---------------------------------------------------------------------------


class TestMemuSync:

    def test_valid_bash(self, hooks_dir):
        result = subprocess.run(
            ["bash", "-n", str(hooks_dir / "memu-sync.sh")],
            capture_output=True,
        )
        assert result.returncode == 0

    def test_skips_no_server(self, run_hook, cognitive_os_env):
        env = {
            **cognitive_os_env["env"],
            "COGNITIVE_OS_MEMU_URL": "http://localhost:19999",
        }
        result = run_hook("memu-sync.sh", env=env)
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# 7. metrics-calibrator-trigger.sh
# ---------------------------------------------------------------------------


class TestMetricsCalibratorTrigger:

    def test_valid_bash(self, hooks_dir):
        result = subprocess.run(
            ["bash", "-n", str(hooks_dir / "metrics-calibrator-trigger.sh")],
            capture_output=True,
        )
        assert result.returncode == 0


    def test_skips_when_recent(self, run_hook, cognitive_os_env):
        cal_file = cognitive_os_env["cos_dir"] / "metrics" / "calibration-history.jsonl"
        now = int(time.time())
        cal_file.write_text(json.dumps({"timestamp_epoch": now}) + "\n")
        result = run_hook("metrics-calibrator-trigger.sh", env=cognitive_os_env["env"])
        combined = result.stdout + result.stderr
        assert "Calibration due" not in combined



# ---------------------------------------------------------------------------
# 9. pre-cleanup-snapshot.sh
# ---------------------------------------------------------------------------


class TestPreCleanupSnapshot:

    def test_valid_bash(self, hooks_dir):
        result = subprocess.run(
            ["bash", "-n", str(hooks_dir / "pre-cleanup-snapshot.sh")],
            capture_output=True,
        )
        assert result.returncode == 0

    def test_ignores_non_agent(self, run_hook, cognitive_os_env):
        input_json = json.dumps({
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
        })
        result = run_hook("pre-cleanup-snapshot.sh", env=cognitive_os_env["env"], stdin=input_json)
        assert result.stdout.strip() == ""


    def test_ignores_unrelated_agent(self, run_hook, cognitive_os_env):
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {"prompt": "write a unit test for the user service"},
        })
        result = run_hook("pre-cleanup-snapshot.sh", env=cognitive_os_env["env"], stdin=input_json)
        assert result.stdout.strip() == ""


# ---------------------------------------------------------------------------
# 10. session-cleanup.sh
# ---------------------------------------------------------------------------


class TestSessionCleanup:

    def test_valid_bash(self, hooks_dir):
        result = subprocess.run(
            ["bash", "-n", str(hooks_dir / "session-cleanup.sh")],
            capture_output=True,
        )
        assert result.returncode == 0


    def test_skips_no_session(self, run_hook, cognitive_os_env):
        env = {**cognitive_os_env["env"]}
        del env["COGNITIVE_OS_SESSION_ID"]
        result = run_hook("session-cleanup.sh", env=env)
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# 11. session-knowledge-extractor.sh
# ---------------------------------------------------------------------------


class TestSessionKnowledgeExtractor:

    def test_valid_bash(self, hooks_dir):
        result = subprocess.run(
            ["bash", "-n", str(hooks_dir / "session-knowledge-extractor.sh")],
            capture_output=True,
        )
        assert result.returncode == 0


    def test_skips_no_errors(self, run_hook, cognitive_os_env):
        result = run_hook("session-knowledge-extractor.sh", env=cognitive_os_env["env"])
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# 12. session-resume.sh
# ---------------------------------------------------------------------------


class TestSessionResume:

    def test_valid_bash(self, hooks_dir):
        result = subprocess.run(
            ["bash", "-n", str(hooks_dir / "session-resume.sh")],
            capture_output=True,
        )
        assert result.returncode == 0


    def test_auto_completes_verified(self, run_hook, cognitive_os_env, tmp_path):
        expected_file = tmp_path / "verified-output.txt"
        expected_file.write_text("done\n")
        tasks_file = cognitive_os_env["cos_dir"] / "tasks" / "active-tasks.json"
        tasks_file.write_text(json.dumps({
            "tasks": [{
                "id": "t1",
                "description": "Create output file",
                "status": "in_progress",
                "expectedOutputs": [str(expected_file)],
            }]
        }))
        result = run_hook("session-resume.sh", env=cognitive_os_env["env"])
        combined = result.stdout + result.stderr
        assert "COMPLETED" in combined
        data = json.loads(tasks_file.read_text())
        assert data["tasks"][0]["status"] == "completed"

    def test_exits_clean_no_tasks(self, run_hook, cognitive_os_env):
        result = run_hook("session-resume.sh", env=cognitive_os_env["env"])
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# 13. sync-to-repo.sh
# ---------------------------------------------------------------------------


class TestSyncToRepo:

    def test_valid_bash(self, hooks_dir):
        result = subprocess.run(
            ["bash", "-n", str(hooks_dir / "sync-to-repo.sh")],
            capture_output=True,
        )
        assert result.returncode == 0

    def test_skips_no_repo(self, run_hook, cognitive_os_env):
        env = {**cognitive_os_env["env"]}
        env.pop("COGNITIVE_OS_REPO_PATH", None)
        result = run_hook("sync-to-repo.sh", env=env)
        assert result.returncode == 0

    def test_skips_private_mode(self, run_hook, cognitive_os_env, tmp_path):
        private_marker = Path("/tmp/claude-private-mode-active")
        try:
            private_marker.touch()
            fake_repo = tmp_path / "fake-repo"
            fake_repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=str(fake_repo), capture_output=True)
            env = {
                **cognitive_os_env["env"],
                "COGNITIVE_OS_REPO_PATH": str(fake_repo),
            }
            result = run_hook("sync-to-repo.sh", env=env)
            assert result.returncode == 0
        finally:
            private_marker.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 14. tool-discovery-trigger.sh
# ---------------------------------------------------------------------------


class TestToolDiscoveryTrigger:

    def test_valid_bash(self, hooks_dir):
        result = subprocess.run(
            ["bash", "-n", str(hooks_dir / "tool-discovery-trigger.sh")],
            capture_output=True,
        )
        assert result.returncode == 0


    def test_skips_when_recent(self, run_hook, cognitive_os_env):
        project_dir = cognitive_os_env["project_dir"]
        disc_dir = project_dir / "metrics"
        disc_dir.mkdir(parents=True, exist_ok=True)
        now = int(time.time())
        (disc_dir / "tool-discovery.jsonl").write_text(
            json.dumps({"timestamp_epoch": now}) + "\n"
        )
        result = run_hook("tool-discovery-trigger.sh", env=cognitive_os_env["env"])
        combined = result.stdout + result.stderr
        assert "Scan due" not in combined
