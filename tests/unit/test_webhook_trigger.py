"""Unit tests for lib/webhook_trigger.py

Validates HMAC signature verification, trigger keyword detection,
issue classification from labels and body, bot loop prevention,
and event filtering.
"""
import hashlib
import hmac
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_LIB_DIR = str(Path(__file__).resolve().parent.parent.parent / "lib")
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

# webhook_trigger imports FastAPI + uvicorn and lib.claude_executor with
# a different interface (ExecutionResult). We need to mock those before import.
# The module also uses `from lib.claude_executor import ClaudeExecutor, ExecutionResult`
# which will fail. We mock that at import time.

import importlib
import unittest.mock

# Create mock modules for imports that may fail
_mock_fastapi = unittest.mock.MagicMock()
_mock_uvicorn = unittest.mock.MagicMock()

# We need to handle the import carefully since webhook_trigger.py imports
# from lib.claude_executor using a path that may not work in test context,
# and uses ExecutionResult which doesn't exist in the actual module.
# We'll mock the specific problematic imports and test the pure functions.

with patch.dict("sys.modules", {
    "fastapi": _mock_fastapi,
    "uvicorn": _mock_uvicorn,
}):
    # Also patch the import of ExecutionResult which doesn't exist
    # We need to make lib.claude_executor available with ExecutionResult
    _mock_ce_module = unittest.mock.MagicMock()
    _mock_ce_module.ClaudeExecutor = unittest.mock.MagicMock
    _mock_ce_module.ExecutionResult = unittest.mock.MagicMock

    with patch.dict("sys.modules", {
        "lib": unittest.mock.MagicMock(),
        "lib.claude_executor": _mock_ce_module,
    }):
        import webhook_trigger as _wt_module
        from webhook_trigger import (
            BOT_IDENTIFIER,
            IssueClass,
            TRIGGER_KEYWORDS,
            _has_trigger,
            _is_bot_comment,
            _make_change_name,
            _verify_signature,
            classify_issue,
        )

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# HMAC signature verification
# ---------------------------------------------------------------------------


class TestVerifySignature:
    def test_no_secret_allows_all(self):
        with patch.object(_wt_module, "WEBHOOK_SECRET", ""):
            assert _verify_signature(b"any payload", "") is True

    def test_valid_signature(self):
        secret = "test-secret"
        payload = b'{"action": "opened"}'
        mac = hmac.new(secret.encode(), msg=payload, digestmod=hashlib.sha256)
        sig = f"sha256={mac.hexdigest()}"

        with patch.object(_wt_module, "WEBHOOK_SECRET", secret):
            assert _verify_signature(payload, sig) is True

    def test_invalid_signature(self):
        secret = "test-secret"
        payload = b'{"action": "opened"}'

        with patch.object(_wt_module, "WEBHOOK_SECRET", secret):
            assert _verify_signature(payload, "sha256=invalid") is False

    def test_missing_signature_header(self):
        with patch.object(_wt_module, "WEBHOOK_SECRET", "secret"):
            assert _verify_signature(b"payload", "") is False

    def test_wrong_prefix(self):
        with patch.object(_wt_module, "WEBHOOK_SECRET", "secret"):
            assert _verify_signature(b"payload", "sha1=abc") is False

    def test_tampered_payload(self):
        secret = "test-secret"
        original = b'{"action": "opened"}'
        mac = hmac.new(secret.encode(), msg=original, digestmod=hashlib.sha256)
        sig = f"sha256={mac.hexdigest()}"

        tampered = b'{"action": "closed"}'
        with patch.object(_wt_module, "WEBHOOK_SECRET", secret):
            assert _verify_signature(tampered, sig) is False


# ---------------------------------------------------------------------------
# Trigger keyword detection
# ---------------------------------------------------------------------------


class TestHasTrigger:
    def test_sdd_auto_keyword(self):
        assert _has_trigger("Please run [sdd-auto] on this issue") is True

    def test_ai_workflow_keyword(self):
        assert _has_trigger("Use [ai-workflow] to process") is True

    def test_luum_bot_mention(self):
        assert _has_trigger("Hey @luum-bot please handle this") is True

    def test_no_trigger(self):
        assert _has_trigger("Just a regular issue description") is False

    def test_case_insensitive(self):
        assert _has_trigger("[SDD-AUTO] please") is True
        assert _has_trigger("@LUUM-BOT help") is True

    def test_empty_string(self):
        assert _has_trigger("") is False

    def test_trigger_keywords_list(self):
        assert "[sdd-auto]" in TRIGGER_KEYWORDS
        assert "[ai-workflow]" in TRIGGER_KEYWORDS
        assert "@luum-bot" in TRIGGER_KEYWORDS


# ---------------------------------------------------------------------------
# Bot loop prevention
# ---------------------------------------------------------------------------


class TestIsBotComment:
    def test_bot_comment_detected(self):
        text = f"{BOT_IDENTIFIER}\nSome status update"
        assert _is_bot_comment(text) is True

    def test_regular_comment(self):
        assert _is_bot_comment("This is a human comment") is False

    def test_bot_identifier_value(self):
        assert BOT_IDENTIFIER == "<!-- luum-bot -->"

    def test_empty_string(self):
        assert _is_bot_comment("") is False

    def test_partial_match(self):
        # Must contain exact identifier
        assert _is_bot_comment("<!-- luum -->") is False


# ---------------------------------------------------------------------------
# Issue classification
# ---------------------------------------------------------------------------


class TestClassifyIssue:
    def test_bug_label(self):
        assert classify_issue(["bug"], "title", "") == IssueClass.BUG

    def test_fix_label(self):
        assert classify_issue(["fix"], "title", "") == IssueClass.BUG

    def test_hotfix_label(self):
        assert classify_issue(["hotfix"], "title", "") == IssueClass.BUG

    def test_feature_label(self):
        assert classify_issue(["feature"], "title", "") == IssueClass.FEATURE

    def test_enhancement_label(self):
        assert classify_issue(["enhancement"], "title", "") == IssueClass.FEATURE

    def test_chore_label(self):
        assert classify_issue(["chore"], "title", "") == IssueClass.CHORE

    def test_maintenance_label(self):
        assert classify_issue(["maintenance"], "title", "") == IssueClass.CHORE

    def test_refactor_label(self):
        assert classify_issue(["refactor"], "title", "") == IssueClass.CHORE

    def test_docs_label(self):
        assert classify_issue(["docs"], "title", "") == IssueClass.CHORE

    def test_ci_label(self):
        assert classify_issue(["ci"], "title", "") == IssueClass.CHORE

    def test_label_case_insensitive(self):
        assert classify_issue(["BUG"], "title", "") == IssueClass.BUG
        assert classify_issue(["Feature"], "title", "") == IssueClass.FEATURE

    def test_classify_command_in_body(self):
        body = "Some description\n/classify_issue bug\nMore text"
        assert classify_issue([], "title", body) == IssueClass.BUG

    def test_classify_command_feature(self):
        body = "/classify_issue feature"
        assert classify_issue([], "title", body) == IssueClass.FEATURE

    def test_classify_command_chore(self):
        body = "/classify_issue chore"
        assert classify_issue([], "title", body) == IssueClass.CHORE

    def test_title_heuristic_bug(self):
        assert classify_issue([], "Fix crash on startup", "") == IssueClass.BUG
        assert classify_issue([], "Bug in login flow", "") == IssueClass.BUG
        assert classify_issue([], "Error handling broken", "") == IssueClass.BUG

    def test_title_heuristic_chore(self):
        assert classify_issue([], "Refactor auth module", "") == IssueClass.CHORE
        assert classify_issue([], "Cleanup old code", "") == IssueClass.CHORE
        assert classify_issue([], "Update CI pipeline", "") == IssueClass.CHORE

    def test_default_feature(self):
        assert classify_issue([], "Add new dashboard", "") == IssueClass.FEATURE

    def test_first_label_wins(self):
        # bug appears first, so it should win
        assert classify_issue(["bug", "enhancement"], "title", "") == IssueClass.BUG

    def test_label_priority_over_body(self):
        body = "/classify_issue chore"
        assert classify_issue(["bug"], "title", body) == IssueClass.BUG

    def test_issue_class_values(self):
        assert IssueClass.FEATURE.value == "feature"
        assert IssueClass.BUG.value == "bug"
        assert IssueClass.CHORE.value == "chore"


# ---------------------------------------------------------------------------
# Change name generation
# ---------------------------------------------------------------------------


class TestMakeChangeName:
    def test_basic(self):
        name = _make_change_name(42, "Add OAuth Flow")
        assert name == "issue-42-add-oauth-flow"

    def test_special_chars_stripped(self):
        name = _make_change_name(1, "Fix: Bug #123 (urgent!)")
        assert "#" not in name
        assert "!" not in name
        assert "(" not in name

    def test_max_length(self):
        name = _make_change_name(1, "A" * 200)
        # The slug part is limited to 60 chars
        slug_part = name.replace("issue-1-", "")
        assert len(slug_part) <= 60

    def test_empty_title(self):
        name = _make_change_name(42, "")
        assert name == "issue-42"

    def test_whitespace_title(self):
        name = _make_change_name(42, "   ")
        assert name == "issue-42"
