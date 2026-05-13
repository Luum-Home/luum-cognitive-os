"""Unit tests for lib/agent_context_injector.py."""

import pytest
from unittest.mock import patch

from lib.agent_context_injector import AgentContextInjector


@pytest.fixture
def injector():
    return AgentContextInjector(project_root=".")


# ── Search permission by task type ──────────────────────────────────────────

def test_implementation_no_search_permission(injector):
    ctx = injector.prepare_context("Implement login endpoint in lib/auth.py", "implementation")
    assert ctx["search_permission"] is False


def test_research_has_search_permission(injector):
    ctx = injector.prepare_context("Research best libraries for JWT", "research")
    assert ctx["search_permission"] is True


def test_debugging_has_search_permission(injector):
    ctx = injector.prepare_context("Fix auth bug in lib/auth.py", "debugging")
    assert ctx["search_permission"] is True


def test_review_no_search_permission(injector):
    ctx = injector.prepare_context("Review lib/auth.py for security issues", "review")
    assert ctx["search_permission"] is False


def test_documentation_no_search_permission(injector):
    ctx = injector.prepare_context("Document lib/auth.py", "documentation")
    assert ctx["search_permission"] is False


# ── Token budget by task type ────────────────────────────────────────────────

def test_token_budget_by_type(injector):
    cases = [
        ("implementation", 500),
        ("research", 200),
        ("debugging", 1000),
        ("review", 300),
        ("documentation", 300),
    ]
    for task_type, expected_budget in cases:
        ctx = injector.prepare_context("some task", task_type)
        assert ctx["token_budget"] == expected_budget, f"{task_type} budget mismatch"


def test_unknown_task_type_uses_default(injector):
    ctx = injector.prepare_context("some task", "unknown_type")
    assert ctx["token_budget"] == 300
    assert ctx["search_permission"] is False


# ── format_context_block structure ──────────────────────────────────────────

def test_format_context_block_structure(injector):
    ctx = {
        "engram_results": [],
        "file_hints": ["lib/auth.py"],
        "decisions": [{"title": "Use JWT", "type": "decision", "summary": "stateless auth"}],
        "token_budget": 500,
        "search_permission": False,
    }
    block = injector.format_context_block(ctx)
    assert "CONTEXT (from orchestrator):" in block
    assert "SEARCH PERMISSION:" in block
    assert "lib/auth.py" in block
    assert "Use JWT" in block


def test_format_context_block_search_yes(injector):
    ctx = {
        "engram_results": [],
        "file_hints": [],
        "decisions": [],
        "token_budget": 200,
        "search_permission": True,
    }
    block = injector.format_context_block(ctx)
    assert "SEARCH PERMISSION: yes" in block


def test_format_context_block_search_no(injector):
    ctx = {
        "engram_results": [],
        "file_hints": [],
        "decisions": [],
        "token_budget": 500,
        "search_permission": False,
    }
    block = injector.format_context_block(ctx)
    assert "SEARCH PERMISSION: no" in block


def test_format_empty_context(injector):
    ctx = {
        "engram_results": [],
        "file_hints": [],
        "decisions": [],
        "token_budget": 300,
        "search_permission": False,
    }
    block = injector.format_context_block(ctx)
    assert "CONTEXT (from orchestrator):" in block
    assert "SEARCH PERMISSION:" in block
    assert "(none)" in block


# ── Token estimation ─────────────────────────────────────────────────────────

def test_estimate_tokens(injector):
    text = "a" * 400
    estimate = injector.estimate_context_tokens(text)
    assert estimate == 100


def test_estimate_tokens_minimum(injector):
    assert injector.estimate_context_tokens("") >= 1


# ── Observation truncation ───────────────────────────────────────────────────

def test_context_truncation(injector):
    long_content = "x" * 1000
    with patch.object(injector, "_search_engram", return_value=[
        {"title": "big obs", "type": "discovery", "summary": long_content[:400]}
    ]):
        ctx = injector.prepare_context("some task", "debugging")
    for obs in ctx["engram_results"]:
        assert len(obs.get("summary", "")) <= 400


# ── File hint extraction ──────────────────────────────────────────────────────

def test_file_hints_extracted(injector):
    with patch.object(injector, "_search_engram", return_value=[]):
        ctx = injector.prepare_context("Fix auth bug in lib/auth.py and update tests/auth_test.py", "implementation")
    assert "lib/auth.py" in ctx["file_hints"]
    assert "tests/auth_test.py" in ctx["file_hints"]


def test_file_hints_no_duplicates(injector):
    with patch.object(injector, "_search_engram", return_value=[]):
        ctx = injector.prepare_context("Edit lib/auth.py then review lib/auth.py again", "review")
    assert ctx["file_hints"].count("lib/auth.py") == 1


def test_file_hints_empty_when_no_paths(injector):
    with patch.object(injector, "_search_engram", return_value=[]):
        ctx = injector.prepare_context("Research JWT best practices", "research")
    assert ctx["file_hints"] == []


# ── Resilience when Engram is unavailable ───────────────────────────────────

def test_prepare_context_resilient(injector):
    """Should not crash if Engram is unavailable."""
    with patch.object(injector, "_search_engram", return_value=[]):
        ctx = injector.prepare_context("Fix auth bug in lib/auth.py", "debugging")
    assert "search_permission" in ctx
    assert "token_budget" in ctx
    assert "file_hints" in ctx
    assert "engram_results" in ctx
    assert ctx["search_permission"] is True


def test_search_engram_returns_empty_on_subprocess_failure(injector):
    """_search_engram must return [] rather than raising."""
    with patch("subprocess.check_output", side_effect=Exception("engram down")):
        result = injector._search_engram("some query")
    assert result == []
