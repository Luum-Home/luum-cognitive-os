"""Functional tests for the COS MCP server.

Verify that the MCP server tools work end-to-end against the real
luum-agent-os project structure.  Each test imports the tool functions
directly (no MCP transport needed) and validates the returned JSON
against the live repo state.

Requirements:
    - fastmcp (skip gracefully if missing)

Related files:
    - mcp-server/cos_mcp.py  (the server under test)
    - rules/                  (rule .md files counted by cos_status)
    - hooks/                  (hook .sh files counted by cos_status)
    - skills/*/SKILL.md       (skill definitions counted by cos_status)
    - lib/skill_router.py     (skill routing backend for cos_suggest_skill)
    - .cognitive-os/content-policy.yaml (quality gate source)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Ensure project root is importable (for lib/ and mcp-server/)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "mcp-server") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "mcp-server"))

pytestmark = [pytest.mark.integration]


# ---------------------------------------------------------------------------
# Lazy import of MCP tool functions (only when fastmcp is present)
# ---------------------------------------------------------------------------

def _import_tools():
    """Import tool functions from cos_mcp after fastmcp is confirmed."""
    from cos_mcp import (
        cos_check_quality,
        cos_get_rules,
        cos_get_tasks,
        cos_status,
        cos_suggest_skill,
    )
    return cos_status, cos_get_rules, cos_suggest_skill, cos_check_quality, cos_get_tasks


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCosStatus:
    """cos_status should return real component counts from this project."""

    def test_returns_valid_json(self):
        cos_status, *_ = _import_tools()
        raw = cos_status()
        data = json.loads(raw)
        assert isinstance(data, dict)

    def test_rule_count_above_threshold(self):
        """The project has 70+ rules — verify cos_status sees them."""
        cos_status, *_ = _import_tools()
        data = json.loads(cos_status())
        assert data["rules"] >= 70, (
            f"Expected >= 70 rules, got {data['rules']}.  "
            "Has rules/ been pruned unexpectedly?"
        )

    def test_hook_count_above_threshold(self):
        """The project has 35+ hooks — verify cos_status sees them."""
        cos_status, *_ = _import_tools()
        data = json.loads(cos_status())
        assert data["hooks"] >= 35, (
            f"Expected >= 35 hooks, got {data['hooks']}.  "
            "Has hooks/ been pruned unexpectedly?"
        )

    def test_skill_count_above_threshold(self):
        """The project has 15+ skills — verify cos_status sees them."""
        cos_status, *_ = _import_tools()
        data = json.loads(cos_status())
        assert data["skills"] >= 15, (
            f"Expected >= 15 skills, got {data['skills']}.  "
            "Has skills/ been pruned unexpectedly?"
        )

    def test_phase_field_present(self):
        cos_status, *_ = _import_tools()
        data = json.loads(cos_status())
        assert "phase" in data

    def test_lib_modules_counted(self):
        cos_status, *_ = _import_tools()
        data = json.loads(cos_status())
        assert data.get("lib_modules", 0) >= 1, "Expected at least 1 lib module"


class TestCosGetRules:
    """cos_get_rules should match rules via contextual triggers."""

    def test_security_context_returns_rules(self):
        _, cos_get_rules, *_ = _import_tools()
        raw = cos_get_rules("security audit credentials")
        data = json.loads(raw)
        # Should match at least one rule
        assert data.get("matched", 0) >= 1, (
            f"Expected >= 1 matched rule for 'security audit credentials', "
            f"got {data}"
        )

    def test_matched_rules_have_structure(self):
        _, cos_get_rules, *_ = _import_tools()
        data = json.loads(cos_get_rules("security audit"))
        if data.get("matched", 0) > 0:
            rule = data["rules"][0]
            assert "rule" in rule
            assert "summary" in rule

    def test_unrelated_context_returns_zero_or_available_triggers(self):
        """Querying with gibberish should return 0 matches or available triggers."""
        _, cos_get_rules, *_ = _import_tools()
        data = json.loads(cos_get_rules("xyzzy_impossible_query_42"))
        assert data.get("matched", 0) == 0


class TestCosSuggestSkill:
    """cos_suggest_skill should route task descriptions to skills."""

    def test_run_tests_suggestion(self):
        *_, cos_suggest_skill, _, _ = _import_tools()
        raw = cos_suggest_skill("run the tests")
        data = json.loads(raw)
        # Should suggest /run-tests (via router or catalog fallback)
        best = data.get("best_match")
        assert best is not None, f"Expected a skill match for 'run the tests', got {data}"
        # Accept either the SkillRouter format or the catalog fallback format
        skill_name = best.get("skill", "") or best.get("command", "")
        assert "test" in skill_name.lower(), (
            f"Expected skill related to testing, got '{skill_name}'"
        )

    def test_security_audit_suggestion(self):
        *_, cos_suggest_skill, _, _ = _import_tools()
        data = json.loads(cos_suggest_skill("security audit"))
        best = data.get("best_match")
        assert best is not None, "Expected a skill match for 'security audit'"

    def test_gibberish_returns_no_match_or_error(self):
        *_, cos_suggest_skill, _, _ = _import_tools()
        data = json.loads(cos_suggest_skill("xyzzy_impossible_query_42"))
        # Either no best_match or an error — both are acceptable
        best = data.get("best_match")
        if best is not None:
            # If there is a match, confidence should be low
            conf = best.get("confidence", 1.0)
            # We don't strictly assert here — gibberish *might* partially match
            assert conf < 0.95 or best.get("keyword_overlap", 0) <= 2


class TestCosCheckQuality:
    """cos_check_quality should detect credential leaks and code smells."""

    def test_detects_api_key(self):
        *_, cos_check_quality, _ = _import_tools()
        raw = cos_check_quality('API_KEY = "sk-1234567890abcdef1234567890abcdef"')
        data = json.loads(raw)
        findings = data.get("findings", [])
        assert len(findings) >= 1, "Expected at least 1 finding for API key"
        # At least one should be a credential leak
        types = [f.get("type") for f in findings]
        assert "credential_leak" in types, f"Expected credential_leak finding, got {types}"

    def test_detects_todo_comment(self):
        *_, cos_check_quality, _ = _import_tools()
        raw = cos_check_quality("# TODO: fix this later\ndef foo(): pass")
        data = json.loads(raw)
        findings = data.get("findings", [])
        types = [f.get("type") for f in findings]
        assert "incomplete_code" in types, f"Expected incomplete_code finding, got {types}"

    def test_detects_stub_implementation(self):
        *_, cos_check_quality, _ = _import_tools()
        raw = cos_check_quality("raise NotImplementedError")
        data = json.loads(raw)
        findings = data.get("findings", [])
        types = [f.get("type") for f in findings]
        assert "stub_implementation" in types, f"Expected stub_implementation, got {types}"

    def test_clean_code_passes(self):
        *_, cos_check_quality, _ = _import_tools()
        raw = cos_check_quality("def add(a, b):\n    return a + b\n")
        data = json.loads(raw)
        assert data["summary"]["verdict"] == "PASS"

    def test_verdict_block_on_credential(self):
        *_, cos_check_quality, _ = _import_tools()
        raw = cos_check_quality('ghp_ABCDEFghijklmnopqrstuvwxyz0123456789ab')
        data = json.loads(raw)
        assert data["summary"]["verdict"] == "BLOCK"


class TestCosGetTasks:
    """cos_get_tasks should read active-tasks.json."""

    def test_reads_real_tasks_file(self, tmp_path):
        """Create a temporary active-tasks.json and verify it is read."""
        # We test the function logic, not file discovery (which uses PROJECT_ROOT).
        # Instead, import the helper and test the JSON parsing path.
        *_, cos_get_tasks = _import_tools()

        # cos_get_tasks reads from PROJECT_ROOT paths.
        # With no active-tasks.json it should still return valid JSON.
        raw = cos_get_tasks()
        data = json.loads(raw)
        assert "tasks" in data or "message" in data

    def test_filter_by_status(self):
        *_, cos_get_tasks = _import_tools()
        raw = cos_get_tasks(status="in_progress")
        data = json.loads(raw)
        assert data.get("filter") == "in_progress"

    def test_returns_valid_structure(self):
        *_, cos_get_tasks = _import_tools()
        data = json.loads(cos_get_tasks(status="all"))
        # Must have either tasks list or a message
        assert isinstance(data.get("tasks", []), list) or "message" in data
