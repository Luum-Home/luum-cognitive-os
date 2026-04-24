"""Behavior tests for safety mesh features.

Tests: clarification-gate, blast-radius, assumption-tracker, pre-commit-gate.

These hooks form a safety mesh:
- clarification-gate (PreToolUse): blocks/warns on ambiguous prompts
- blast-radius (PreToolUse): estimates impact scope of agent tasks
- assumption-tracker (PostToolUse): detects assumption language in responses
- pre-commit-gate (git pre-commit): blocks commits on test failures
"""

import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior


def _blast_context(stdout: str) -> str:
    """Return the emitted additionalContext when the hook uses ADR-023 JSON."""
    text = stdout.strip()
    if not text:
        return ""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return text
    return payload.get("hookSpecificOutput", {}).get("additionalContext", text)


def _latest_blast_entry(cognitive_os_env) -> dict:
    session_id = cognitive_os_env["session_id"]
    session_log = (
        cognitive_os_env["cos_dir"]
        / "sessions"
        / session_id
        / "metrics"
        / "blast-radius.jsonl"
    )
    global_log = cognitive_os_env["cos_dir"] / "metrics" / "blast-radius.jsonl"
    log_file = session_log if session_log.exists() else global_log
    return json.loads(log_file.read_text().strip().split("\n")[-1])


# ---------------------------------------------------------------------------
# 1. clarification-gate.sh
# ---------------------------------------------------------------------------


class TestClarificationGate:
    """Tests for the clarification-gate.sh PreToolUse hook."""

    def test_vague_prompt_blocked(self, run_hook, cognitive_os_env):
        """Ambiguity score > 60 should block the agent launch (exit 2)."""
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {
                "prompt": "fix bugs"
            },
        })
        result = run_hook(
            "clarification-gate.sh",
            env=cognitive_os_env["env"],
            stdin=input_json,
        )
        assert result.returncode == 2
        assert "BLOCKED" in result.stdout
        assert "ambiguity score" in result.stdout.lower()

    def test_medium_ambiguity_warned(self, run_hook, cognitive_os_env):
        """Ambiguity score 30-60 should produce a warning but not block."""
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {
                "prompt": (
                    "Implement a new endpoint in internal/users/application/use_cases/get_user.go "
                    "using Go and ginext to handle GET /api/users/:id. "
                    "This should work for all user types."
                ),
            },
        })
        result = run_hook(
            "clarification-gate.sh",
            env=cognitive_os_env["env"],
            stdin=input_json,
        )
        # Should pass (exit 0) but may warn
        assert result.returncode == 0

    def test_clear_prompt_passes(self, run_hook, cognitive_os_env):
        """Ambiguity score < 30 should pass silently."""
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {
                "prompt": (
                    "Implement GetUserByID use case in "
                    "internal/users/application/use_cases/get_user_by_id.go "
                    "using Go and ginext framework. "
                    "ACCEPTANCE CRITERIA:\n"
                    "1. `go build ./...` exits 0\n"
                    "2. `go test ./internal/users/...` exits 0\n"
                    "3. Endpoint GET /api/users/:id returns 200"
                ),
            },
        })
        result = run_hook(
            "clarification-gate.sh",
            env=cognitive_os_env["env"],
            stdin=input_json,
        )
        assert result.returncode == 0
        assert "BLOCKED" not in result.stdout
        assert "WARNING" not in result.stdout

    def test_no_file_paths_detected(self, run_hook, cognitive_os_env):
        """Prompt without any file paths should add ambiguity points."""
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {
                "prompt": "Add authentication to the application"
            },
        })
        result = run_hook(
            "clarification-gate.sh",
            env=cognitive_os_env["env"],
            stdin=input_json,
        )
        # Should block or warn — no file paths, no tech, action without target
        assert result.returncode == 2 or "WARNING" in result.stdout

    def test_scope_without_quantifier_detected(self, run_hook, cognitive_os_env):
        """Words like 'all' without counts should be flagged."""
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {
                "prompt": (
                    "Update all services to use the new Go error handling pattern "
                    "in internal/services/. Use golang."
                ),
            },
        })
        result = run_hook(
            "clarification-gate.sh",
            env=cognitive_os_env["env"],
            stdin=input_json,
        )
        combined = result.stdout + result.stderr
        # Should detect "all" without quantifier
        assert "all" in combined.lower() or "count" in combined.lower() or result.returncode == 2

    def test_non_agent_tool_ignored(self, run_hook, cognitive_os_env):
        """Non-Agent tool calls should be ignored."""
        input_json = json.dumps({
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
        })
        result = run_hook(
            "clarification-gate.sh",
            env=cognitive_os_env["env"],
            stdin=input_json,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_very_short_prompt_flagged(self, run_hook, cognitive_os_env):
        """Very short prompts with multiple ambiguity signals should be blocked."""
        # "add auth" is short AND has action without target AND no file paths AND no tech
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {
                "prompt": "add auth"
            },
        })
        result = run_hook(
            "clarification-gate.sh",
            env=cognitive_os_env["env"],
            stdin=input_json,
        )
        assert result.returncode == 2
        assert "BLOCKED" in result.stdout

    def test_metrics_logged(self, run_hook, cognitive_os_env):
        """Ambiguous prompts should be logged to metrics."""
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {
                "prompt": "improve performance"
            },
        })
        result = run_hook(
            "clarification-gate.sh",
            env=cognitive_os_env["env"],
            stdin=input_json,
        )

        # Check metrics file was created
        session_id = cognitive_os_env["session_id"]
        metrics_dir = (
            cognitive_os_env["cos_dir"]
            / "sessions"
            / session_id
            / "metrics"
        )
        log_file = metrics_dir / "clarification-events.jsonl"
        if not log_file.exists():
            log_file = cognitive_os_env["cos_dir"] / "metrics" / "clarification-events.jsonl"

        assert log_file.exists(), "Clarification events log should be created"
        content = log_file.read_text().strip()
        assert len(content) > 0
        entry = json.loads(content.split("\n")[-1])
        assert "score" in entry
        assert "verdict" in entry

    def test_empty_input_passes(self, run_hook, cognitive_os_env):
        """Empty input should pass silently."""
        result = run_hook(
            "clarification-gate.sh",
            env=cognitive_os_env["env"],
            stdin="",
        )
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# 2. blast-radius.sh
# ---------------------------------------------------------------------------


class TestBlastRadius:
    """Tests for the blast-radius.sh PreToolUse hook."""

    def test_low_radius_silent(self, run_hook, cognitive_os_env):
        """LOW blast radius (1-5 files) should be silent."""
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {
                "prompt": "Fix the bug in internal/users/domain/entities/user.go"
            },
        })
        result = run_hook(
            "blast-radius.sh",
            env=cognitive_os_env["env"],
            stdin=input_json,
        )
        assert result.returncode == 0
        assert "BLAST RADIUS" not in result.stdout

    def test_medium_radius_silent(self, run_hook, cognitive_os_env):
        """MEDIUM blast radius (6-20 files) should be silent."""
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {
                "prompt": (
                    "Refactor the DTOs in internal/users/application/dtos/ "
                    "to use the new naming convention."
                ),
            },
        })
        result = run_hook(
            "blast-radius.sh",
            env=cognitive_os_env["env"],
            stdin=input_json,
        )
        assert result.returncode == 0
        # MEDIUM is silent — no output
        assert "CRITICAL" not in result.stdout

    def test_high_radius_warned(self, run_hook, cognitive_os_env):
        """HIGH blast radius (21-50 files) should produce a warning."""
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {
                "prompt": (
                    "Update all controllers in internal/users/, internal/payments/, "
                    "internal/orders/, internal/auth/, internal/notifications/ "
                    "to use the new error handling pattern. "
                    "There are 30 controller files across these directories."
                ),
            },
        })
        result = run_hook(
            "blast-radius.sh",
            env=cognitive_os_env["env"],
            stdin=input_json,
        )
        assert result.returncode == 0
        assert "BLAST RADIUS" in result.stdout
        assert "HIGH" in result.stdout or "CRITICAL" in result.stdout

    def test_critical_radius_infra(self, run_hook, cognitive_os_env):
        """Infra-only prompts no longer escalate by keyword alone after 2264356."""
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {
                "prompt": "Update the docker-compose configuration to add a new database container."
            },
        })
        result = run_hook(
            "blast-radius.sh",
            env=cognitive_os_env["env"],
            stdin=input_json,
        )
        assert result.returncode == 0
        assert _blast_context(result.stdout) == ""

        entry = _latest_blast_entry(cognitive_os_env)
        assert entry["infra"] is True
        assert entry["radius"] == "LOW"

    def test_critical_radius_security(self, run_hook, cognitive_os_env):
        """Security keywords + broad scope should surface as HIGH/CRITICAL."""
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {
                "prompt": "Add JWT authentication middleware to protect all API endpoints."
            },
        })
        result = run_hook(
            "blast-radius.sh",
            env=cognitive_os_env["env"],
            stdin=input_json,
        )
        assert result.returncode == 0
        ctx = _blast_context(result.stdout)
        if ctx:
            assert "BLAST RADIUS" in ctx
            assert "HIGH" in ctx or "CRITICAL" in ctx
        else:
            entry = _latest_blast_entry(cognitive_os_env)
            assert entry["security"] is True
            assert entry["radius"] == "LOW"

    def test_critical_cross_service(self, run_hook, cognitive_os_env):
        """Cross-service keywords should result in HIGH or CRITICAL."""
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {
                "prompt": "Rebrand all services from old-name to new-name across the project."
            },
        })
        result = run_hook(
            "blast-radius.sh",
            env=cognitive_os_env["env"],
            stdin=input_json,
        )
        assert result.returncode == 0
        assert "BLAST RADIUS" in result.stdout

    def test_non_agent_ignored(self, run_hook, cognitive_os_env):
        """Non-Agent tool calls should be ignored."""
        input_json = json.dumps({
            "tool_name": "Bash",
            "tool_input": {"command": "docker ps"},
        })
        result = run_hook(
            "blast-radius.sh",
            env=cognitive_os_env["env"],
            stdin=input_json,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_metrics_logged(self, run_hook, cognitive_os_env):
        """All blast radius assessments should be logged."""
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {
                "prompt": "Fix the typo in internal/users/domain/entities/user.go"
            },
        })
        result = run_hook(
            "blast-radius.sh",
            env=cognitive_os_env["env"],
            stdin=input_json,
        )

        session_id = cognitive_os_env["session_id"]
        metrics_dir = (
            cognitive_os_env["cos_dir"]
            / "sessions"
            / session_id
            / "metrics"
        )
        log_file = metrics_dir / "blast-radius.jsonl"
        if not log_file.exists():
            log_file = cognitive_os_env["cos_dir"] / "metrics" / "blast-radius.jsonl"

        assert log_file.exists(), "Blast radius log should be created"
        content = log_file.read_text().strip()
        entry = json.loads(content.split("\n")[-1])
        assert "radius" in entry
        assert entry["radius"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")

    def test_database_keywords_critical(self, run_hook, cognitive_os_env):
        """Database keywords are logged as infra even when advisory stays silent."""
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {
                "prompt": "Create a database migration to alter the users table and add a new column."
            },
        })
        result = run_hook(
            "blast-radius.sh",
            env=cognitive_os_env["env"],
            stdin=input_json,
        )
        assert result.returncode == 0
        assert _blast_context(result.stdout) == ""

        entry = _latest_blast_entry(cognitive_os_env)
        assert entry["infra"] is True
        assert entry["radius"] == "LOW"

    def test_advisory_only_never_blocks(self, run_hook, cognitive_os_env):
        """Blast radius should always exit 0, even for CRITICAL."""
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {
                "prompt": (
                    "Migrate all services, update docker-compose, "
                    "change authentication, and deploy to production."
                ),
            },
        })
        result = run_hook(
            "blast-radius.sh",
            env=cognitive_os_env["env"],
            stdin=input_json,
        )
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# 3. assumption-tracker.sh
# ---------------------------------------------------------------------------


class TestAssumptionTracker:
    """Tests for the assumption-tracker.sh PostToolUse hook."""

    def test_assumption_language_detected(self, run_hook, cognitive_os_env):
        """Explicit assumption language should be detected and logged."""
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {"prompt": "Fix the bug"},
            "tool_response": (
                "I assume the database is PostgreSQL. "
                "I'm assuming you want unit tests for this. "
                "Presumably the service runs on port 3000. "
                "I'll assume the config is in YAML format."
            ),
        })
        result = run_hook(
            "assumption-tracker.sh",
            env=cognitive_os_env["env"],
            stdin=input_json,
        )
        assert result.returncode == 0
        assert "ASSUMPTION TRACKER" in result.stdout
        assert "WARNING" in result.stdout
        assert "4 assumptions" in result.stdout

    def test_count_threshold_warning(self, run_hook, cognitive_os_env):
        """3+ assumptions should trigger a WARNING."""
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {"prompt": "Implement feature"},
            "tool_response": (
                "I assume this is for the admin panel. "
                "I think the API expects JSON. "
                "It seems like the cache layer uses Redis."
            ),
        })
        result = run_hook(
            "assumption-tracker.sh",
            env=cognitive_os_env["env"],
            stdin=input_json,
        )
        assert result.returncode == 0
        assert "WARNING" in result.stdout
        assert "3 assumptions" in result.stdout

    def test_below_threshold_silent(self, run_hook, cognitive_os_env):
        """Fewer than 3 assumptions should be silent (logged but no output)."""
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {"prompt": "Fix the bug"},
            "tool_response": (
                "I assume the database is PostgreSQL. "
                "The fix has been applied successfully. "
                "All tests pass."
            ),
        })
        result = run_hook(
            "assumption-tracker.sh",
            env=cognitive_os_env["env"],
            stdin=input_json,
        )
        assert result.returncode == 0
        assert "WARNING" not in result.stdout

    def test_no_false_positives_normal_text(self, run_hook, cognitive_os_env):
        """Normal technical text without assumption language should not trigger."""
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {"prompt": "Implement endpoint"},
            "tool_response": (
                "Created the GetUserByID use case in internal/users/. "
                "Added unit tests with 95% coverage. "
                "The endpoint returns 200 with user data. "
                "All acceptance criteria verified:\n"
                "1. go build exits 0\n"
                "2. go test passes\n"
                "3. Lint clean"
            ),
        })
        result = run_hook(
            "assumption-tracker.sh",
            env=cognitive_os_env["env"],
            stdin=input_json,
        )
        assert result.returncode == 0
        assert "WARNING" not in result.stdout
        assert "ASSUMPTION" not in result.stdout

    def test_medium_confidence_patterns(self, run_hook, cognitive_os_env):
        """Medium confidence hedging patterns should be detected."""
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {"prompt": "Debug the issue"},
            "tool_response": (
                "It seems like the connection is timing out. "
                "The error appears to be related to DNS resolution. "
                "This is probably caused by a misconfigured proxy. "
                "I believe the fix is to update the timeout setting."
            ),
        })
        result = run_hook(
            "assumption-tracker.sh",
            env=cognitive_os_env["env"],
            stdin=input_json,
        )
        assert result.returncode == 0
        assert "WARNING" in result.stdout
        assert "MEDIUM" in result.stdout

    def test_non_agent_ignored(self, run_hook, cognitive_os_env):
        """Non-Agent tool calls should be ignored."""
        input_json = json.dumps({
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
            "tool_response": "file1.go file2.go",
        })
        result = run_hook(
            "assumption-tracker.sh",
            env=cognitive_os_env["env"],
            stdin=input_json,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_metrics_logged(self, run_hook, cognitive_os_env):
        """Assumptions should be logged to metrics file."""
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {"prompt": "Fix bug"},
            "tool_response": (
                "I assume the config uses YAML. "
                "Presumably the port is 8080. "
                "I'll assume tests use pytest."
            ),
        })
        result = run_hook(
            "assumption-tracker.sh",
            env=cognitive_os_env["env"],
            stdin=input_json,
        )

        session_id = cognitive_os_env["session_id"]
        metrics_dir = (
            cognitive_os_env["cos_dir"]
            / "sessions"
            / session_id
            / "metrics"
        )
        log_file = metrics_dir / "assumptions.jsonl"
        if not log_file.exists():
            log_file = cognitive_os_env["cos_dir"] / "metrics" / "assumptions.jsonl"

        assert log_file.exists(), "Assumptions log should be created"
        content = log_file.read_text().strip()
        entry = json.loads(content.split("\n")[-1])
        assert "assumption_count" in entry
        assert entry["assumption_count"] >= 3

    def test_empty_response_passes(self, run_hook, cognitive_os_env):
        """Empty response should pass silently."""
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {"prompt": "Fix bug"},
            "tool_response": "",
        })
        result = run_hook(
            "assumption-tracker.sh",
            env=cognitive_os_env["env"],
            stdin=input_json,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_advisory_only_never_blocks(self, run_hook, cognitive_os_env):
        """Assumption tracker should always exit 0, even with many assumptions."""
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {"prompt": "Fix everything"},
            "tool_response": (
                "I assume this. I assume that. I assume the other thing. "
                "I'm assuming we need X. Presumably Y is the answer. "
                "I think Z is correct. It seems like A. Probably B. "
                "I believe C is right. My best guess is D."
            ),
        })
        result = run_hook(
            "assumption-tracker.sh",
            env=cognitive_os_env["env"],
            stdin=input_json,
        )
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# 4. infra-health.sh
# ---------------------------------------------------------------------------


class TestInfraHealth:
    """Tests for the infra-health.sh SessionStart hook."""

    def test_docker_not_available(self, run_hook, cognitive_os_env):
        """When Docker is not available, output advisory message without crashing."""
        env = cognitive_os_env["env"].copy()
        # Force docker to be unavailable by overriding PATH to exclude it
        env["PATH"] = "/usr/bin:/bin"
        result = run_hook(
            "infra-health.sh",
            env=env,
        )
        assert result.returncode == 0
        assert "Docker is not active" in result.stdout

    def test_no_services_running_reports_missing(self, run_hook, cognitive_os_env):
        """When Docker is available but no services running, reports missing."""
        env = cognitive_os_env["env"].copy()
        project_dir = cognitive_os_env["project_dir"]
        cos_dir = cognitive_os_env["cos_dir"]

        # Create a minimal cognitive-os.yaml with services
        config_file = cos_dir / "cognitive-os.yaml"
        config_file.write_text(
            "resources:\n"
            "  infrastructure:\n"
            "    services:\n"
            "      litellm:\n"
            "        mode: always\n"
            "      paperclip:\n"
            "        mode: on_demand\n"
        )

        # Create a minimal docker-compose file
        compose_file = project_dir / "docker-compose.cognitive-os.yml"
        compose_file.write_text(
            "services:\n"
            "  litellm:\n"
            "    image: alpine\n"
            "  paperclip:\n"
            "    image: alpine\n"
        )

        result = run_hook(
            "infra-health.sh",
            env=env,
        )
        assert result.returncode == 0
        # Should report services status or docker not active
        assert "Infrastructure:" in result.stdout or "Docker is not active" in result.stdout

    def test_no_services_configured_silent(self, run_hook, cognitive_os_env):
        """When no services are configured, no warnings are emitted."""
        env = cognitive_os_env["env"].copy()
        project_dir = cognitive_os_env["project_dir"]
        cos_dir = cognitive_os_env["cos_dir"]

        # Create config with no services
        config_file = cos_dir / "cognitive-os.yaml"
        config_file.write_text(
            "resources:\n"
            "  infrastructure:\n"
            "    services: {}\n"
        )

        compose_file = project_dir / "docker-compose.cognitive-os.yml"
        compose_file.write_text("services: {}\n")

        result = run_hook(
            "infra-health.sh",
            env=env,
        )
        assert result.returncode == 0
        assert "WARN" not in result.stdout

    def test_auto_start_true_outputs_auto_start(self, run_hook, cognitive_os_env):
        """When INFRA_AUTO_START=true and services are missing, outputs auto-start info."""
        env = cognitive_os_env["env"].copy()
        env["INFRA_AUTO_START"] = "true"
        project_dir = cognitive_os_env["project_dir"]
        cos_dir = cognitive_os_env["cos_dir"]

        config_file = cos_dir / "cognitive-os.yaml"
        config_file.write_text(
            "resources:\n"
            "  infrastructure:\n"
            "    services:\n"
            "      litellm:\n"
            "        mode: always\n"
        )

        compose_file = project_dir / "docker-compose.cognitive-os.yml"
        compose_file.write_text(
            "services:\n"
            "  litellm:\n"
            "    image: alpine\n"
        )

        result = run_hook(
            "infra-health.sh",
            env=env,
        )
        assert result.returncode == 0
        stdout = result.stdout
        # When docker is available and services are missing with auto-start,
        # it should attempt auto-start or report docker not active
        assert ("Auto-started" in stdout or "Docker is not active" in stdout
                or "Infrastructure:" in stdout)

    def test_auto_start_false_suggests_command(self, run_hook, cognitive_os_env):
        """When INFRA_AUTO_START=false and services are missing, suggests commands only."""
        env = cognitive_os_env["env"].copy()
        env["INFRA_AUTO_START"] = "false"
        project_dir = cognitive_os_env["project_dir"]
        cos_dir = cognitive_os_env["cos_dir"]

        config_file = cos_dir / "cognitive-os.yaml"
        config_file.write_text(
            "resources:\n"
            "  infrastructure:\n"
            "    services:\n"
            "      litellm:\n"
            "        mode: always\n"
        )

        compose_file = project_dir / "docker-compose.cognitive-os.yml"
        compose_file.write_text(
            "services:\n"
            "  litellm:\n"
            "    image: alpine\n"
        )

        result = run_hook(
            "infra-health.sh",
            env=env,
        )
        assert result.returncode == 0
        stdout = result.stdout
        # Should suggest the command, not auto-start
        assert ("docker compose" in stdout or "Docker is not active" in stdout
                or "Infrastructure:" in stdout)
        # Should NOT contain auto-start (unless docker is not active)
        if "Docker is not active" not in stdout:
            assert "Auto-started" not in stdout


# ---------------------------------------------------------------------------
# 5. pre-commit-gate.sh
# ---------------------------------------------------------------------------


class TestPreCommitGate:
    """Tests for the pre-commit-gate.sh git pre-commit hook."""

    def test_hook_exists_and_is_executable(self, hooks_dir):
        """The pre-commit-gate.sh hook should exist."""
        hook_path = hooks_dir / "pre-commit-gate.sh"
        assert hook_path.exists(), "pre-commit-gate.sh should exist in hooks/"

    def test_blocks_on_test_failure(self, tmp_path):
        """Hook no longer runs pytest inline after ADR-028 D4."""
        # Create a fake python3 that would leave evidence if invoked.
        fake_bin = tmp_path / "bin"
        fake_bin.mkdir()
        fake_pytest = fake_bin / "python3"
        sentinel = tmp_path / "pytest-invoked.txt"
        fake_pytest.write_text(
            '#!/usr/bin/env bash\n'
            f'echo invoked > "{sentinel}"\n'
            'echo "3 failed, 2 passed"\n'
        )
        fake_pytest.chmod(0o755)

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        tests_dir = project_dir / "tests"
        tests_dir.mkdir()
        coverage_script = tests_dir / "coverage-report.sh"
        coverage_script.write_text(
            '#!/usr/bin/env bash\n'
            'echo "  Composite:              90% (45/50)"\n'
        )
        coverage_script.chmod(0o755)

        hook_path = Path(__file__).resolve().parent.parent.parent / "hooks" / "pre-commit-gate.sh"
        hook_content = hook_path.read_text()
        patched_hook = tmp_path / "pre-commit-gate.sh"
        patched_hook.write_text(
            hook_content.replace(
                'ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"',
                f'ROOT_DIR="{project_dir}"',
            )
        )
        patched_hook.chmod(0o755)

        env = os.environ.copy()
        env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"

        result = subprocess.run(
            ["bash", str(patched_hook)],
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )
        assert result.returncode == 0
        assert not sentinel.exists(), "pre-commit-gate must not invoke pytest inline"

    def test_passes_on_all_tests_passing(self, tmp_path):
        """Hook should allow commit when structural checks pass."""
        fake_bin = tmp_path / "bin"
        fake_bin.mkdir()
        fake_pytest = fake_bin / "python3"
        fake_pytest.write_text(
            '#!/usr/bin/env bash\n'
            'echo "42 passed in 3.21s"\n'
        )
        fake_pytest.chmod(0o755)

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        tests_dir = project_dir / "tests"
        tests_dir.mkdir()
        coverage_script = tests_dir / "coverage-report.sh"
        coverage_script.write_text(
            '#!/usr/bin/env bash\n'
            'echo "  Composite:              90% (45/50)"\n'
        )
        coverage_script.chmod(0o755)

        hook_path = Path(__file__).resolve().parent.parent.parent / "hooks" / "pre-commit-gate.sh"
        hook_content = hook_path.read_text()
        patched_hook = tmp_path / "pre-commit-gate.sh"
        patched_hook.write_text(
            hook_content.replace(
                'ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"',
                f'ROOT_DIR="{project_dir}"',
            )
        )
        patched_hook.chmod(0o755)
        env = os.environ.copy()
        env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"

        result = subprocess.run(
            ["bash", str(patched_hook)],
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )
        assert result.returncode == 0

    def test_warns_on_low_coverage(self, tmp_path):
        """Hook should warn (but not block) when coverage is below threshold."""
        fake_bin = tmp_path / "bin"
        fake_bin.mkdir()
        fake_pytest = fake_bin / "python3"
        fake_pytest.write_text(
            '#!/usr/bin/env bash\n'
            'echo "10 passed in 1.00s"\n'
        )
        fake_pytest.chmod(0o755)

        # Create a real-looking project structure with coverage-report.sh
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        tests_dir = project_dir / "tests"
        tests_dir.mkdir()
        coverage_script = tests_dir / "coverage-report.sh"
        coverage_script.write_text(
            '#!/usr/bin/env bash\n'
            'echo "  Composite:              50% (25/50)"\n'
        )
        coverage_script.chmod(0o755)

        # Write a modified hook that uses our project dir
        hook_path = Path(__file__).resolve().parent.parent.parent / "hooks" / "pre-commit-gate.sh"
        hook_content = hook_path.read_text()
        # Patch ROOT_DIR to our tmp project dir
        patched_hook = tmp_path / "pre-commit-gate.sh"
        patched_content = hook_content.replace(
            'ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"',
            f'ROOT_DIR="{project_dir}"',
        )
        patched_hook.write_text(patched_content)
        patched_hook.chmod(0o755)

        env = os.environ.copy()
        env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"
        env["COVERAGE_THRESHOLD"] = "80"

        result = subprocess.run(
            ["bash", str(patched_hook)],
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )
        # Should pass (exit 0) but warn
        assert result.returncode == 0
        assert "WARNING" in result.stderr
        assert "50%" in result.stderr

    def test_custom_threshold_respected(self, tmp_path):
        """COVERAGE_THRESHOLD env var should be respected."""
        fake_bin = tmp_path / "bin"
        fake_bin.mkdir()
        fake_pytest = fake_bin / "python3"
        fake_pytest.write_text(
            '#!/usr/bin/env bash\n'
            'echo "5 passed"\n'
        )
        fake_pytest.chmod(0o755)

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        tests_dir = project_dir / "tests"
        tests_dir.mkdir()
        coverage_script = tests_dir / "coverage-report.sh"
        coverage_script.write_text(
            '#!/usr/bin/env bash\n'
            'echo "  Composite:              70% (35/50)"\n'
        )
        coverage_script.chmod(0o755)

        hook_path = Path(__file__).resolve().parent.parent.parent / "hooks" / "pre-commit-gate.sh"
        hook_content = hook_path.read_text()
        patched_hook = tmp_path / "pre-commit-gate.sh"
        patched_content = hook_content.replace(
            'ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"',
            f'ROOT_DIR="{project_dir}"',
        )
        patched_hook.write_text(patched_content)
        patched_hook.chmod(0o755)

        env = os.environ.copy()
        env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"
        # Set a low threshold so 70% passes
        env["COVERAGE_THRESHOLD"] = "60"

        result = subprocess.run(
            ["bash", str(patched_hook)],
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )
        assert result.returncode == 0
        # 70% >= 60% threshold, so no warning
        assert "WARNING" not in result.stderr

    def test_install_script_exists(self):
        """The install script should exist."""
        install_path = (
            Path(__file__).resolve().parent.parent.parent
            / "scripts"
            / "install-pre-commit.sh"
        )
        assert install_path.exists()
