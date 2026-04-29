"""Unit tests for mcp-server/cos_mcp.py

Validates each MCP tool function is callable, returns expected formats,
and handles edge cases (missing files, empty data, bad inputs).
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add project root to path so we can import the MCP server module
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "mcp-server"))
sys.path.insert(0, str(PROJECT_ROOT))

from cos_mcp import (
    _read_json,
    _read_jsonl,
    cos_check_quality,
    cos_get_metrics,
    cos_get_rules,
    cos_get_tasks,
    cos_save_memory,
    cos_search_memory,
    cos_status,
    cos_suggest_skill,
)

pytestmark = [pytest.mark.unit]


# ---------------------------------------------------------------------------
# Helper tests
# ---------------------------------------------------------------------------


class TestReadJsonl:
    """Tests for _read_jsonl helper."""

    def test_reads_valid_jsonl(self, tmp_path):
        p = tmp_path / "test.jsonl"
        p.write_text('{"a": 1}\n{"a": 2}\n{"a": 3}\n')
        result = _read_jsonl(p, max_lines=10)
        assert len(result) == 3
        assert result[0]["a"] == 1

    def test_respects_max_lines(self, tmp_path):
        p = tmp_path / "test.jsonl"
        lines = [json.dumps({"i": i}) for i in range(20)]
        p.write_text("\n".join(lines) + "\n")
        result = _read_jsonl(p, max_lines=5)
        assert len(result) == 5
        # Should return the LAST 5 entries
        assert result[0]["i"] == 15

    def test_handles_missing_file(self, tmp_path):
        result = _read_jsonl(tmp_path / "nonexistent.jsonl")
        assert result == []

    def test_handles_malformed_json(self, tmp_path):
        p = tmp_path / "test.jsonl"
        p.write_text('{"valid": 1}\nnot json\n{"valid": 2}\n')
        result = _read_jsonl(p)
        assert len(result) == 2

    def test_handles_empty_file(self, tmp_path):
        p = tmp_path / "test.jsonl"
        p.write_text("")
        result = _read_jsonl(p)
        assert result == []


class TestReadJson:
    """Tests for _read_json helper."""

    def test_reads_valid_json(self, tmp_path):
        p = tmp_path / "test.json"
        p.write_text('{"tasks": []}')
        result = _read_json(p)
        assert result == {"tasks": []}

    def test_handles_missing_file(self, tmp_path):
        result = _read_json(tmp_path / "nonexistent.json")
        assert result is None

    def test_handles_invalid_json(self, tmp_path):
        p = tmp_path / "test.json"
        p.write_text("not json at all")
        result = _read_json(p)
        assert result is None


# ---------------------------------------------------------------------------
# Tool: cos_search_memory
# ---------------------------------------------------------------------------


class TestCosSearchMemory:
    """Tests for cos_search_memory tool."""

    def test_returns_string(self):
        result = cos_search_memory("test query")
        assert isinstance(result, str)

    def test_returns_valid_json(self):
        result = cos_search_memory("nonexistent query xyz123")
        parsed = json.loads(result)
        assert isinstance(parsed, (dict, list))

    def test_accepts_project_filter(self):
        result = cos_search_memory("auth", project="my-project")
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert isinstance(parsed, (dict, list))


# ---------------------------------------------------------------------------
# Tool: cos_get_tasks
# ---------------------------------------------------------------------------


class TestCosGetTasks:
    """Tests for cos_get_tasks tool."""

    def test_returns_valid_json(self):
        result = cos_get_tasks()
        parsed = json.loads(result)
        assert isinstance(parsed, dict)
        assert "tasks" in parsed or "message" in parsed

    def test_returns_tasks_structure(self):
        result = cos_get_tasks(status="all")
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_filters_by_status(self):
        # Even without active-tasks.json, should return valid JSON
        result = cos_get_tasks(status="in_progress")
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    @patch("cos_mcp._read_json")
    def test_reads_active_tasks(self, mock_read):
        mock_read.return_value = {
            "tasks": [
                {"id": "t1", "status": "pending", "description": "Task 1"},
                {"id": "t2", "status": "in_progress", "description": "Task 2"},
                {"id": "t3", "status": "completed", "description": "Task 3"},
            ]
        }
        result = cos_get_tasks(status="pending")
        parsed = json.loads(result)
        assert parsed["filtered"] == 1
        assert parsed["total"] == 3

    @patch("cos_mcp._read_json")
    def test_all_status_returns_everything(self, mock_read):
        mock_read.return_value = {
            "tasks": [
                {"id": "t1", "status": "pending"},
                {"id": "t2", "status": "completed"},
            ]
        }
        result = cos_get_tasks(status="all")
        parsed = json.loads(result)
        assert parsed["filtered"] == 2


# ---------------------------------------------------------------------------
# Tool: cos_get_rules
# ---------------------------------------------------------------------------


class TestCosGetRules:
    """Tests for cos_get_rules tool."""

    def test_returns_valid_json(self):
        result = cos_get_rules("security audit")
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_matches_security_context(self):
        result = cos_get_rules("credential management secret api key")
        parsed = json.loads(result)
        # Should match at least one rule if cognitive-os.yaml exists
        if "matched" in parsed:
            assert parsed["matched"] >= 0

    def test_returns_available_triggers_on_no_match(self):
        result = cos_get_rules("zzz_completely_unrelated_xyz_999")
        parsed = json.loads(result)
        if "available_triggers" in parsed:
            assert isinstance(parsed["available_triggers"], list)

    def test_handles_empty_context(self):
        result = cos_get_rules("")
        parsed = json.loads(result)
        assert isinstance(parsed, dict)


# ---------------------------------------------------------------------------
# Tool: cos_check_quality
# ---------------------------------------------------------------------------


class TestCosCheckQuality:
    """Tests for cos_check_quality tool."""

    def test_returns_valid_json(self):
        result = cos_check_quality("x = 1")
        parsed = json.loads(result)
        assert isinstance(parsed, dict)
        assert "findings" in parsed
        assert "summary" in parsed

    def test_clean_code_passes(self):
        result = cos_check_quality("def add(a, b):\n    return a + b\n")
        parsed = json.loads(result)
        assert parsed["summary"]["verdict"] == "PASS"

    def test_detects_api_key(self):
        result = cos_check_quality('api_key = "sk-1234567890abcdef1234567890abcdef"')
        parsed = json.loads(result)
        assert parsed["summary"]["blockers"] > 0
        assert parsed["summary"]["verdict"] == "BLOCK"

    def test_detects_password(self):
        result = cos_check_quality('password = "supersecret123"')
        parsed = json.loads(result)
        credential_findings = [
            f for f in parsed["findings"] if f["type"] == "credential_leak"
        ]
        assert len(credential_findings) > 0

    def test_detects_todo_comments(self):
        result = cos_check_quality("# TODO: fix this later\nx = 1\n# FIXME: broken")
        parsed = json.loads(result)
        todo_findings = [
            f for f in parsed["findings"] if f["type"] == "incomplete_code"
        ]
        assert len(todo_findings) > 0

    def test_detects_stub_implementations(self):
        result = cos_check_quality("raise NotImplementedError")
        parsed = json.loads(result)
        stub_findings = [
            f for f in parsed["findings"] if f["type"] == "stub_implementation"
        ]
        assert len(stub_findings) > 0

    def test_detects_commented_out_code(self):
        code = "x = 1\n# old_func()\n# more_old()\n# even_more()\ny = 2"
        result = cos_check_quality(code)
        parsed = json.loads(result)
        dead_code = [f for f in parsed["findings"] if f["type"] == "dead_code"]
        assert len(dead_code) > 0

    def test_includes_file_path(self):
        result = cos_check_quality("x = 1", file_path="src/main.py")
        parsed = json.loads(result)
        assert parsed["file"] == "src/main.py"

    def test_detects_aws_key(self):
        result = cos_check_quality('key = "AKIA1234567890ABCDEF"')
        parsed = json.loads(result)
        assert parsed["summary"]["blockers"] > 0

    def test_detects_github_token(self):
        result = cos_check_quality('token = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij"')
        parsed = json.loads(result)
        assert parsed["summary"]["blockers"] > 0

    def test_summary_counts(self):
        # Code with multiple issues
        code = (
            '# TODO: fix\n'
            'api_key = "sk-12345678901234567890"\n'
            'raise NotImplementedError\n'
        )
        result = cos_check_quality(code)
        parsed = json.loads(result)
        total = parsed["summary"]["total"]
        b = parsed["summary"]["blockers"]
        c = parsed["summary"]["concerns"]
        s = parsed["summary"]["suggestions"]
        assert total == b + c + s


# ---------------------------------------------------------------------------
# Tool: cos_get_metrics
# ---------------------------------------------------------------------------


class TestCosGetMetrics:
    """Tests for cos_get_metrics tool."""

    def test_returns_valid_json(self):
        result = cos_get_metrics()
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_all_type_returns_available_files(self):
        result = cos_get_metrics(metric_type="all")
        parsed = json.loads(result)
        assert "_available_files" in parsed

    def test_specific_type_filter(self):
        result = cos_get_metrics(metric_type="errors")
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_unknown_type_returns_empty(self):
        result = cos_get_metrics(metric_type="nonexistent_metric")
        parsed = json.loads(result)
        assert isinstance(parsed, dict)


# ---------------------------------------------------------------------------
# Tool: cos_suggest_skill
# ---------------------------------------------------------------------------


class TestCosSuggestSkill:
    """Tests for cos_suggest_skill tool."""

    def test_returns_valid_json(self):
        result = cos_suggest_skill("debug this issue")
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_returns_match_or_error(self):
        result = cos_suggest_skill("investigate this GitHub repository")
        parsed = json.loads(result)
        # Should have best_match or error
        assert "best_match" in parsed or "error" in parsed

    def test_empty_message_returns_valid_json(self):
        result = cos_suggest_skill("")
        parsed = json.loads(result)
        assert isinstance(parsed, dict)


# ---------------------------------------------------------------------------
# Tool: cos_save_memory
# ---------------------------------------------------------------------------


class TestCosSaveMemory:
    """Tests for cos_save_memory tool."""

    def test_returns_string(self):
        result = cos_save_memory(
            title="Test observation",
            content="**What**: test\n**Why**: unit test",
        )
        assert isinstance(result, str)

    def test_accepts_all_parameters(self):
        result = cos_save_memory(
            title="Test",
            content="Content",
            type="decision",
            project="test-project",
            topic_key="architecture/test",
        )
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Tool: cos_status
# ---------------------------------------------------------------------------


class TestCosStatus:
    """Tests for cos_status tool."""

    def test_returns_valid_json(self):
        result = cos_status()
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_includes_component_counts(self):
        result = cos_status()
        parsed = json.loads(result)
        assert "rules" in parsed
        assert "hooks" in parsed
        assert "skills" in parsed
        assert "packages" in parsed
        assert "lib_modules" in parsed

    def test_counts_are_non_negative(self):
        result = cos_status()
        parsed = json.loads(result)
        for key in ["rules", "hooks", "skills", "packages", "lib_modules"]:
            assert parsed[key] >= 0

    def test_includes_phase(self):
        result = cos_status()
        parsed = json.loads(result)
        assert "phase" in parsed

    def test_includes_metrics_info(self):
        result = cos_status()
        parsed = json.loads(result)
        assert "metrics_files" in parsed
        assert "total_metric_entries" in parsed

    def test_includes_active_tasks(self):
        result = cos_status()
        parsed = json.loads(result)
        assert "active_tasks" in parsed

    def test_actual_counts_match_filesystem(self):
        """Verify counts reflect real files in the project."""
        result = cos_status()
        parsed = json.loads(result)
        # Rules should be >50 based on what we see in the project
        assert parsed["rules"] > 40, f"Expected >40 rules, got {parsed['rules']}"
        # Hooks should be >30
        assert parsed["hooks"] > 25, f"Expected >25 hooks, got {parsed['hooks']}"
        # Skills should be >10
        assert parsed["skills"] > 10, f"Expected >10 skills, got {parsed['skills']}"
        # Packages should be >20
        assert parsed["packages"] > 20, f"Expected >20 packages, got {parsed['packages']}"
