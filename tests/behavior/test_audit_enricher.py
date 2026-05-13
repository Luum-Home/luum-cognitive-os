"""Behavior tests for audit-id-enricher.sh PostToolUse hook."""

import json

import pytest

pytestmark = pytest.mark.behavior


class TestAuditIdEnricher:

    def test_enriches_cost_events_with_session_id(self, run_hook, cognitive_os_env):
        """F1: Hook adds session_id to last line of cost-events.jsonl."""
        cos_dir = cognitive_os_env["cos_dir"]
        session_id = cognitive_os_env["session_id"]

        # Create cost-events.jsonl with one unenriched entry
        metrics_dir = cos_dir / "metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)
        cost_file = metrics_dir / "cost-events.jsonl"
        entry = {"timestamp": "2026-04-10", "agent": "test", "cost_usd": 0.5}
        cost_file.write_text(json.dumps(entry) + "\n")

        # PostToolUse stdin JSON
        stdin_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {"prompt": "test"},
            "tool_response": {"result": "done"},
        })

        result = run_hook(
            "audit-id-enricher.sh",
            env=cognitive_os_env["env"],
            stdin=stdin_json,
        )

        assert result.returncode == 0, f"Hook failed: {result.stderr}"

        lines = [l for l in cost_file.read_text().splitlines() if l.strip()]
        assert len(lines) == 1
        enriched = json.loads(lines[0])
        assert "session_id" in enriched, "session_id not added to cost-events.jsonl"
        assert enriched["session_id"] == session_id

    def test_no_sprint_still_adds_session_and_branch(self, run_hook, cognitive_os_env):
        """F2: Without sprint-status.yaml, session_id present, sprint_id empty, branch present."""
        cos_dir = cognitive_os_env["cos_dir"]

        # Ensure no sprint file exists
        sprint_file = cos_dir / "workflows" / "state" / "sprint-status.yaml"
        sprint_file.unlink(missing_ok=True)

        # Create cost-events.jsonl
        metrics_dir = cos_dir / "metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)
        cost_file = metrics_dir / "cost-events.jsonl"
        entry = {"timestamp": "2026-04-10", "agent": "test", "cost_usd": 0.1}
        cost_file.write_text(json.dumps(entry) + "\n")

        stdin_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {"prompt": "do something"},
            "tool_response": {"result": "ok"},
        })

        result = run_hook(
            "audit-id-enricher.sh",
            env=cognitive_os_env["env"],
            stdin=stdin_json,
        )

        assert result.returncode == 0, f"Hook failed: {result.stderr}"

        enriched = json.loads(cost_file.read_text().strip())
        assert "session_id" in enriched
        assert enriched["session_id"] == cognitive_os_env["session_id"]
        assert "sprint_id" in enriched
        assert enriched["sprint_id"] == ""  # no sprint file
        assert "branch" in enriched

    def test_skips_non_agent_bash_tools(self, run_hook, cognitive_os_env):
        """Hook does nothing for non-Agent/Bash tool names."""
        cos_dir = cognitive_os_env["cos_dir"]
        metrics_dir = cos_dir / "metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)
        cost_file = metrics_dir / "cost-events.jsonl"
        entry = {"timestamp": "2026-04-10", "agent": "test", "cost_usd": 0.1}
        cost_file.write_text(json.dumps(entry) + "\n")
        original_content = cost_file.read_text()

        stdin_json = json.dumps({
            "tool_name": "Edit",
            "tool_input": {"file_path": "foo.py"},
            "tool_response": {},
        })

        result = run_hook(
            "audit-id-enricher.sh",
            env=cognitive_os_env["env"],
            stdin=stdin_json,
        )

        assert result.returncode == 0
        # File should be unchanged (hook skipped)
        assert cost_file.read_text() == original_content

    def test_does_not_double_enrich(self, run_hook, cognitive_os_env):
        """Hook does not overwrite session_id if already present."""
        cos_dir = cognitive_os_env["cos_dir"]
        metrics_dir = cos_dir / "metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)
        cost_file = metrics_dir / "cost-events.jsonl"

        # Entry already has session_id
        entry = {
            "timestamp": "2026-04-10",
            "agent": "test",
            "cost_usd": 0.1,
            "session_id": "already-set-session",
        }
        cost_file.write_text(json.dumps(entry) + "\n")

        stdin_json = json.dumps({
            "tool_name": "Bash",
            "tool_input": {"command": "echo hi"},
            "tool_response": {"output": "hi"},
        })

        result = run_hook(
            "audit-id-enricher.sh",
            env=cognitive_os_env["env"],
            stdin=stdin_json,
        )

        assert result.returncode == 0
        enriched = json.loads(cost_file.read_text().strip())
        # session_id must not be overwritten
        assert enriched["session_id"] == "already-set-session"

    def test_handles_missing_cost_file_gracefully(self, run_hook, cognitive_os_env):
        """Hook exits 0 when cost-events.jsonl does not exist."""
        # Ensure the file does not exist
        cost_file = cognitive_os_env["cos_dir"] / "metrics" / "cost-events.jsonl"
        cost_file.unlink(missing_ok=True)

        stdin_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {"prompt": "test"},
            "tool_response": {"result": "done"},
        })

        result = run_hook(
            "audit-id-enricher.sh",
            env=cognitive_os_env["env"],
            stdin=stdin_json,
        )
        assert result.returncode == 0
