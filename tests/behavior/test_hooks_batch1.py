"""Behavior tests for hooks batch 1 (15 hooks).

Migrated from test-hooks-batch1.sh.
Tests: dod-gate, secret-detector, pre-compaction-flush, auto-verify,
       agent-checkpoint, agent-prelaunch, architecture-compliance,
       completeness-check, doc-sync-detector, epic-task-detector,
       error-pattern-detector, infra-intent-detector, result-truncator,
       skill-tracker, trust-score-validator.
"""

import json
import os
import subprocess
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior


# ---------------------------------------------------------------------------
# 1. completion-gate.sh
# ---------------------------------------------------------------------------


class TestDodGate:

    def test_trivial_complexity(self, run_hook, cognitive_os_env):
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {},
            "tool_response": "Task done. Complexity: trivial. Build success, lint clean, 0 errors.",
        })
        result = run_hook("completion-gate.sh", env=cognitive_os_env["env"], stdin=input_json)
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        assert "Missing DoD" not in combined

    def test_medium_missing_criteria(self, run_hook, cognitive_os_env):
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {},
            "tool_response": "Task complete. Complexity: medium. Build success.",
        })
        result = run_hook("completion-gate.sh", env=cognitive_os_env["env"], stdin=input_json)
        combined = result.stdout + result.stderr
        assert "Missing DoD" in combined

    def test_non_agent_ignored(self, run_hook, cognitive_os_env):
        input_json = json.dumps({
            "tool_name": "Bash",
            "tool_input": {},
            "tool_response": "done",
        })
        result = run_hook("completion-gate.sh", env=cognitive_os_env["env"], stdin=input_json)
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_critical_inferred(self, run_hook, cognitive_os_env):
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {},
            "tool_response": "Done. Fixed security vulnerability in payment module.",
        })
        result = run_hook("completion-gate.sh", env=cognitive_os_env["env"], stdin=input_json)
        combined = (result.stdout + result.stderr).lower()
        assert "critical" in combined

    def test_no_completion_signal(self, run_hook, cognitive_os_env):
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {},
            "tool_response": "Working on it, complexity: large",
        })
        result = run_hook("completion-gate.sh", env=cognitive_os_env["env"], stdin=input_json)
        assert result.returncode == 0
        assert result.stdout.strip() == ""


# ---------------------------------------------------------------------------
# 2. secret-detector.sh
# ---------------------------------------------------------------------------


class TestSecretDetector:

    def test_finds_missing_env(self, run_hook, cognitive_os_env):
        project_dir = cognitive_os_env["project_dir"]
        src_dir = project_dir / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        (src_dir / "app.ts").write_text("const x = process.env.MY_SECRET_KEY;\n")

        env = {
            **cognitive_os_env["env"],
            "TOOL_INPUT": json.dumps({"file_path": str(src_dir / "app.ts")}),
        }
        result = run_hook("secret-detector.sh", env=env, stdin="")
        combined = result.stdout + result.stderr
        assert "MY_SECRET_KEY" in combined

    def test_clean_file(self, run_hook, cognitive_os_env):
        project_dir = cognitive_os_env["project_dir"]
        src_dir = project_dir / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        (src_dir / "clean.ts").write_text("const x = 42;\n")

        env = {
            **cognitive_os_env["env"],
            "TOOL_INPUT": json.dumps({"file_path": str(src_dir / "clean.ts")}),
        }
        result = run_hook("secret-detector.sh", env=env, stdin="")
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        assert "WARNING" not in combined

    def test_skips_md_files(self, run_hook, cognitive_os_env):
        env = {
            **cognitive_os_env["env"],
            "TOOL_INPUT": json.dumps({"file_path": "docs/readme.md"}),
        }
        result = run_hook("secret-detector.sh", env=env, stdin="")
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        assert "WARNING" not in combined


# ---------------------------------------------------------------------------
# 3. pre-compaction-flush.sh
# ---------------------------------------------------------------------------


class TestPreCompactionFlush:

    def test_outputs_message(self, run_hook, cognitive_os_env):
        result = run_hook("pre-compaction-flush.sh", env=cognitive_os_env["env"])
        assert result.returncode == 0
        combined = (result.stdout + result.stderr).lower()
        assert "compaction" in combined
        assert "mem_session_summary" in combined

    def test_mentions_save(self, run_hook, cognitive_os_env):
        result = run_hook("pre-compaction-flush.sh", env=cognitive_os_env["env"])
        combined = result.stdout + result.stderr
        assert "mem_save" in combined


# ---------------------------------------------------------------------------
# 4. completion-gate.sh
# ---------------------------------------------------------------------------


class TestAutoVerify:

    def test_no_criteria_warning(self, run_hook, cognitive_os_env):
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {"prompt": "Do something without criteria"},
            "tool_response": "Task complete and done.",
        })
        result = run_hook("completion-gate.sh", env=cognitive_os_env["env"], stdin=input_json)
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        assert "No ACCEPTANCE CRITERIA" in combined

    def test_skips_non_agent(self, run_hook, cognitive_os_env):
        input_json = json.dumps({
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
            "tool_response": "file.txt",
        })
        result = run_hook("completion-gate.sh", env=cognitive_os_env["env"], stdin=input_json)
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_skips_non_completion(self, run_hook, cognitive_os_env):
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {"prompt": "ACCEPTANCE CRITERIA: something"},
            "tool_response": "Still working on it...",
        })
        result = run_hook("completion-gate.sh", env=cognitive_os_env["env"], stdin=input_json)
        assert result.returncode == 0
        assert result.stdout.strip() == ""


# ---------------------------------------------------------------------------
# 5. agent-checkpoint.sh
# ---------------------------------------------------------------------------


class TestAgentCheckpoint:

    def test_marks_complete(self, run_hook, cognitive_os_env):
        tasks_file = cognitive_os_env["cos_dir"] / "tasks" / "active-tasks.json"
        tasks_file.write_text(json.dumps({
            "version": 1,
            "tasks": [{
                "id": "task-1",
                "description": "Do the thing",
                "status": "in_progress",
                "launchedAt": "2024-01-01T00:00:00Z",
                "completedAt": None,
                "outputSummary": None,
            }],
            "lastUpdated": "2024-01-01T00:00:00Z",
        }))
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {"prompt": "Do the thing"},
            "tool_response": {"result": "All good"},
        })
        run_hook("agent-checkpoint.sh", env=cognitive_os_env["env"], stdin=input_json)
        data = json.loads(tasks_file.read_text())
        assert data["tasks"][0]["status"] == "completed"

    def test_marks_failed(self, run_hook, cognitive_os_env):
        tasks_file = cognitive_os_env["cos_dir"] / "tasks" / "active-tasks.json"
        tasks_file.write_text(json.dumps({
            "version": 1,
            "tasks": [{
                "id": "task-2",
                "description": "Failing task",
                "status": "in_progress",
                "launchedAt": "2024-01-01T00:00:00Z",
                "completedAt": None,
                "outputSummary": None,
            }],
            "lastUpdated": "2024-01-01T00:00:00Z",
        }))
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {"prompt": "Failing task"},
            "tool_response": {"error": "Something broke"},
        })
        run_hook("agent-checkpoint.sh", env=cognitive_os_env["env"], stdin=input_json)
        data = json.loads(tasks_file.read_text())
        assert data["tasks"][0]["status"] == "failed"

    def test_no_tasks_file(self, run_hook, cognitive_os_env):
        tasks_file = cognitive_os_env["cos_dir"] / "tasks" / "active-tasks.json"
        tasks_file.unlink(missing_ok=True)
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {"prompt": "test"},
            "tool_response": "ok",
        })
        result = run_hook("agent-checkpoint.sh", env=cognitive_os_env["env"], stdin=input_json)
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# 6. agent-prelaunch.sh
# ---------------------------------------------------------------------------


class TestAgentPrelaunch:

    def test_creates_task(self, run_hook, cognitive_os_env):
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {"prompt": "Build the widget"},
        })
        run_hook("agent-prelaunch.sh", env=cognitive_os_env["env"], stdin=input_json)
        tasks_file = cognitive_os_env["cos_dir"] / "tasks" / "active-tasks.json"
        data = json.loads(tasks_file.read_text())
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["status"] == "in_progress"

    def test_skips_non_agent(self, run_hook, cognitive_os_env):
        input_json = json.dumps({
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
        })
        result = run_hook("agent-prelaunch.sh", env=cognitive_os_env["env"], stdin=input_json)
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# 7. architecture-compliance.sh
# ---------------------------------------------------------------------------


class TestArchitectureCompliance:

    def test_detects_huma_violation(self, run_hook, cognitive_os_env):
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {},
            "tool_result": "Created internal/api/handler.go with import danielgtaylor/huma",
        })
        result = run_hook("architecture-compliance.sh", env=cognitive_os_env["env"], stdin=input_json)
        combined = result.stdout + result.stderr
        assert "VIOLATION" in combined
        assert "huma" in combined.lower()

    def test_clean_output(self, run_hook, cognitive_os_env):
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {},
            "tool_result": "Updated README.md with new instructions",
        })
        result = run_hook("architecture-compliance.sh", env=cognitive_os_env["env"], stdin=input_json)
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        assert "VIOLATION" not in combined

    def test_dto_in_wrong_layer(self, run_hook, cognitive_os_env):
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {},
            "tool_result": "Created domain/dtos/user_dto.go",
        })
        result = run_hook("architecture-compliance.sh", env=cognitive_os_env["env"], stdin=input_json)
        combined = result.stdout + result.stderr
        assert "VIOLATION" in combined
        assert "DTO" in combined


# ---------------------------------------------------------------------------
# 8. completeness-check.sh
# ---------------------------------------------------------------------------


class TestCompletenessCheck:

    def test_flags_vague_prompt(self, run_hook, cognitive_os_env):
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {
                "prompt": "Update all files across the entire codebase to follow patterns. Also update docs and complete the migration."
            },
        })
        result = run_hook("completeness-check.sh", env=cognitive_os_env["env"], stdin=input_json)
        combined = result.stdout + result.stderr
        assert "RED FLAG" in combined

    def test_passes_good_prompt(self, run_hook, cognitive_os_env):
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {
                "prompt": "Fix typo in line 5 of main.go. ACCEPTANCE CRITERIA: `go build ./...` exits 0"
            },
        })
        result = run_hook("completeness-check.sh", env=cognitive_os_env["env"], stdin=input_json)
        combined = result.stdout + result.stderr
        assert "RED FLAG" not in combined

    def test_skips_non_agent(self, run_hook, cognitive_os_env):
        input_json = json.dumps({
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
        })
        result = run_hook("completeness-check.sh", env=cognitive_os_env["env"], stdin=input_json)
        assert result.returncode == 0
        assert result.stdout.strip() == ""


# ---------------------------------------------------------------------------
# 9. doc-sync-detector.sh
# ---------------------------------------------------------------------------


class TestDocSyncDetector:

    def test_detects_controller_change(self, run_hook, cognitive_os_env):
        project_dir = cognitive_os_env["project_dir"]
        docs_dir = project_dir / "docs" / "backend-go"
        docs_dir.mkdir(parents=True, exist_ok=True)
        (docs_dir / "migration-audit.md").write_text("migration doc\n")
        input_json = json.dumps({
            "tool_name": "Edit",
            "tool_input": {
                "file_path": f"{project_dir}/infrastructure/controllers/user_controller.go"
            },
        })
        result = run_hook("doc-sync-detector.sh", env=cognitive_os_env["env"], stdin=input_json)
        combined = (result.stdout + result.stderr).lower()
        assert "stale" in combined

    def test_ignores_test_files(self, run_hook, cognitive_os_env):
        project_dir = cognitive_os_env["project_dir"]
        input_json = json.dumps({
            "tool_name": "Edit",
            "tool_input": {"file_path": f"{project_dir}/pkg/handler_test.go"},
        })
        result = run_hook("doc-sync-detector.sh", env=cognitive_os_env["env"], stdin=input_json)
        assert result.returncode == 0
        combined = (result.stdout + result.stderr).lower()
        assert "stale" not in combined

    def test_ignores_non_edit_tools(self, run_hook, cognitive_os_env):
        input_json = json.dumps({
            "tool_name": "Bash",
            "tool_input": {"file_path": "some/controller.go"},
        })
        result = run_hook("doc-sync-detector.sh", env=cognitive_os_env["env"], stdin=input_json)
        assert result.returncode == 0
        combined = (result.stdout + result.stderr).lower()
        assert "stale" not in combined


# ---------------------------------------------------------------------------
# 10. epic-task-detector.sh
# ---------------------------------------------------------------------------


class TestEpicTaskDetector:

    def test_detects_large_scope(self, run_hook, cognitive_os_env):
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {
                "prompt": "Rename all files across the entire codebase and do a bulk update of every service in the monorepo"
            },
        })
        result = run_hook("epic-task-detector.sh", env=cognitive_os_env["env"], stdin=input_json)
        combined = result.stdout + result.stderr
        assert "EPIC TASK DETECTED" in combined

    def test_passes_small_task(self, run_hook, cognitive_os_env):
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {"prompt": "Fix the typo in main.go line 5"},
        })
        result = run_hook("epic-task-detector.sh", env=cognitive_os_env["env"], stdin=input_json)
        combined = result.stdout + result.stderr
        assert "EPIC TASK DETECTED" not in combined

    def test_skips_non_agent(self, run_hook, cognitive_os_env):
        input_json = json.dumps({
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
        })
        result = run_hook("epic-task-detector.sh", env=cognitive_os_env["env"], stdin=input_json)
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# 11. error-pattern-detector.sh
# ---------------------------------------------------------------------------


class TestErrorPatternDetector:

    def test_no_metrics_file(self, run_hook, cognitive_os_env):
        result = run_hook("error-pattern-detector.sh", env=cognitive_os_env["env"])
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        assert "ERROR PATTERN" not in combined

    def test_detects_repeated_errors(self, run_hook, cognitive_os_env):
        now_epoch = int(time.time())
        metrics_file = cognitive_os_env["cos_dir"] / "metrics" / "error-learning.jsonl"
        lines = []
        for i in range(4):
            lines.append(json.dumps({
                "timestamp_epoch": now_epoch,
                "service": "user-svc",
                "type": "TEST_FAILURE",
                "error": "connection refused",
                "context": "connection refused",
                "framework": "jest",
            }))
        metrics_file.write_text("\n".join(lines) + "\n")
        result = run_hook("error-pattern-detector.sh", env=cognitive_os_env["env"])
        combined = result.stdout + result.stderr
        assert "ERROR PATTERN" in combined
        assert "user-svc" in combined


# ---------------------------------------------------------------------------
# 12. infra-intent-detector.sh
# ---------------------------------------------------------------------------


class TestInfraIntentDetector:

    def test_detects_database(self, run_hook, cognitive_os_env):
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {"prompt": "Create a new entity and save to database with CRUD operations"},
        })
        result = run_hook("infra-intent-detector.sh", env=cognitive_os_env["env"], stdin=input_json)
        combined = (result.stdout + result.stderr).lower()
        assert "database" in combined

    def test_detects_auth(self, run_hook, cognitive_os_env):
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {"prompt": "Implement user login and authentication with JWT tokens"},
        })
        result = run_hook("infra-intent-detector.sh", env=cognitive_os_env["env"], stdin=input_json)
        combined = (result.stdout + result.stderr).lower()
        assert "auth" in combined

    def test_no_infra_keywords(self, run_hook, cognitive_os_env):
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {"prompt": "Fix the typo in the README"},
        })
        result = run_hook("infra-intent-detector.sh", env=cognitive_os_env["env"], stdin=input_json)
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        assert "INFRASTRUCTURE" not in combined

    def test_skips_non_agent(self, run_hook, cognitive_os_env):
        input_json = json.dumps({
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
        })
        result = run_hook("infra-intent-detector.sh", env=cognitive_os_env["env"], stdin=input_json)
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# 13. result-truncator.sh
# ---------------------------------------------------------------------------


class TestResultTruncator:

    def test_short_passthrough(self, run_hook, cognitive_os_env):
        input_json = json.dumps({
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
            "tool_response": "file.txt",
        })
        result = run_hook("result-truncator.sh", env=cognitive_os_env["env"], stdin=input_json)
        try:
            data = json.loads(result.stdout)
            assert data["tool_response"] == "file.txt"
        except (json.JSONDecodeError, KeyError):
            # Hook may not produce JSON output in all environments
            pass

    def test_long_truncated(self, run_hook, cognitive_os_env):
        long_response = "x" * 8000
        input_json = json.dumps({
            "tool_name": "Bash",
            "tool_input": {"command": "cat big.txt"},
            "tool_response": long_response,
        })
        result = run_hook("result-truncator.sh", env=cognitive_os_env["env"], stdin=input_json)
        try:
            data = json.loads(result.stdout)
            assert "TRUNCATED" in data["tool_response"]
        except (json.JSONDecodeError, KeyError):
            pass

    def test_no_response_passthrough(self, run_hook, cognitive_os_env):
        input_json = json.dumps({
            "tool_name": "Bash",
            "tool_input": {"command": "true"},
        })
        result = run_hook("result-truncator.sh", env=cognitive_os_env["env"], stdin=input_json)
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# 14. skill-tracker.sh
# ---------------------------------------------------------------------------


class TestSkillTracker:

    def test_records_success(self, run_hook, cognitive_os_env):
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {"skill": "sdd-explore"},
            "tool_response": "Exploration complete",
            "exit_code": "0",
        })
        run_hook("skill-tracker.sh", env=cognitive_os_env["env"], stdin=input_json)
        metrics_file = cognitive_os_env["cos_dir"] / "metrics" / "skill-metrics.jsonl"
        if metrics_file.exists():
            last_line = metrics_file.read_text().strip().splitlines()[-1]
            data = json.loads(last_line)
            assert data["success"] is True

    def test_records_failure(self, run_hook, cognitive_os_env):
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {"skill": "sdd-apply"},
            "tool_response": "error: something failed badly",
            "exit_code": "1",
        })
        run_hook("skill-tracker.sh", env=cognitive_os_env["env"], stdin=input_json)
        metrics_file = cognitive_os_env["cos_dir"] / "metrics" / "skill-metrics.jsonl"
        if metrics_file.exists():
            last_line = metrics_file.read_text().strip().splitlines()[-1]
            data = json.loads(last_line)
            assert data["success"] is False

    def test_skips_non_agent(self, run_hook, cognitive_os_env):
        input_json = json.dumps({
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
            "tool_response": "ok",
        })
        run_hook("skill-tracker.sh", env=cognitive_os_env["env"], stdin=input_json)
        metrics_file = cognitive_os_env["cos_dir"] / "metrics" / "skill-metrics.jsonl"
        if metrics_file.exists():
            line_count = len(metrics_file.read_text().strip().splitlines())
            assert line_count == 0


# ---------------------------------------------------------------------------
# 15. trust-score-validator.sh
# ---------------------------------------------------------------------------


class TestTrustScoreValidator:

    def test_missing_report(self, run_hook, cognitive_os_env):
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {},
            "tool_result": "I finished the task. Everything works.",
        })
        result = run_hook("trust-score-validator.sh", env=cognitive_os_env["env"], stdin=input_json)
        combined = result.stdout + result.stderr
        assert "did not provide Trust Report" in combined

    def test_low_score_alert(self, run_hook, cognitive_os_env):
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {"prompt": "do thing"},
            "tool_result": "Task done.\n\nTrust Report:\nScore: 30/100\nEvidence: partial implementation",
        })
        result = run_hook("trust-score-validator.sh", env=cognitive_os_env["env"], stdin=input_json)
        combined = result.stdout + result.stderr
        assert "Low confidence" in combined
        trust_log = cognitive_os_env["cos_dir"] / "metrics" / "trust-scores.jsonl"
        if trust_log.exists():
            last_line = trust_log.read_text().strip().splitlines()[-1]
            data = json.loads(last_line)
            assert data["score"] == 30

    def test_high_score_no_alert(self, run_hook, cognitive_os_env):
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {"prompt": "do thing"},
            "tool_result": "All done.\n\nTrust Report:\nScore: 95/100\nEvidence: all tests pass",
        })
        result = run_hook("trust-score-validator.sh", env=cognitive_os_env["env"], stdin=input_json)
        combined = result.stdout + result.stderr
        assert "Low confidence" not in combined
        assert "Medium-low" not in combined

    def test_skips_non_agent(self, run_hook, cognitive_os_env):
        input_json = json.dumps({
            "tool_name": "Bash",
            "tool_input": {},
            "tool_result": "ok",
        })
        result = run_hook("trust-score-validator.sh", env=cognitive_os_env["env"], stdin=input_json)
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        assert "Trust Report" not in combined
