"""Unit tests for lib/notifications.py

Validates provider detection, Telegram/Slack/webhook formatting,
graceful no-op when provider is 'none', phase event messages,
pipeline complete, and batch summary messages.
"""
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_LIB_DIR = str(Path(__file__).resolve().parent.parent.parent / "lib")
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from notifications import (
    _dispatch,
    _fmt_duration,
    _get_provider,
    _slack_format,
    _telegram_format,
    _webhook_format,
    notify_batch_summary,
    notify_phase_complete,
    notify_phase_fail,
    notify_phase_start,
    notify_pipeline_complete,
    send_raw,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Provider detection
# ---------------------------------------------------------------------------


class TestGetProvider:
    def test_default_none(self):
        with patch.dict(os.environ, {}, clear=True):
            assert _get_provider() == "none"

    def test_telegram(self):
        with patch.dict(os.environ, {"NOTIFY_PROVIDER": "telegram"}, clear=True):
            assert _get_provider() == "telegram"

    def test_slack(self):
        with patch.dict(os.environ, {"NOTIFY_PROVIDER": "slack"}, clear=True):
            assert _get_provider() == "slack"

    def test_webhook(self):
        with patch.dict(os.environ, {"NOTIFY_PROVIDER": "webhook"}, clear=True):
            assert _get_provider() == "webhook"

    def test_unknown_falls_back_none(self):
        with patch.dict(os.environ, {"NOTIFY_PROVIDER": "discord"}, clear=True):
            assert _get_provider() == "none"

    def test_case_insensitive(self):
        with patch.dict(os.environ, {"NOTIFY_PROVIDER": "TELEGRAM"}, clear=True):
            assert _get_provider() == "telegram"

    def test_strips_whitespace(self):
        with patch.dict(os.environ, {"NOTIFY_PROVIDER": "  slack  "}, clear=True):
            assert _get_provider() == "slack"


# ---------------------------------------------------------------------------
# Duration formatting
# ---------------------------------------------------------------------------


class TestFmtDuration:
    def test_none(self):
        assert _fmt_duration(None) == ""

    def test_seconds(self):
        assert _fmt_duration(30.5) == "30.5s"

    def test_minutes(self):
        result = _fmt_duration(120.0)
        assert "2.0min" == result


# ---------------------------------------------------------------------------
# Telegram formatting
# ---------------------------------------------------------------------------


class TestTelegramFormat:
    def test_phase_start(self):
        text = _telegram_format("phase_start", "Phase starting: apply", {
            "change": "add-auth",
            "phase": "apply",
        })
        assert "Phase starting: apply" in text
        assert "`add-auth`" in text
        assert "*APPLY*" in text

    def test_phase_fail_with_error(self):
        text = _telegram_format("phase_fail", "Phase FAILED: verify", {
            "change": "add-auth",
            "phase": "verify",
            "error": "Build failed",
            "resume_cmd": "/sdd-continue add-auth",
            "duration_s": 42.0,
        })
        assert "[FAIL]" in text
        assert "`Build failed`" in text
        assert "`/sdd-continue add-auth`" in text
        assert "42.0s" in text

    def test_batch_results(self):
        text = _telegram_format("batch_summary", "Batch complete: b1", {
            "results": [
                {"name": "c1", "success": True, "elapsed_s": 10.0},
                {"name": "c2", "success": False, "elapsed_s": 5.0, "resume_cmd": "/retry c2"},
            ],
            "total_duration_s": 15.0,
        })
        assert "Total: 2 | OK: 1 | FAIL: 1" in text
        assert "`[OK]` c1" in text
        assert "`[FAIL]` c2" in text
        assert "`/retry c2`" in text

    def test_unknown_event_emoji(self):
        text = _telegram_format("unknown_event", "Test", {})
        assert "[-]" in text


# ---------------------------------------------------------------------------
# Slack formatting
# ---------------------------------------------------------------------------


class TestSlackFormat:
    def test_returns_fallback_and_blocks(self):
        fallback, blocks = _slack_format("phase_complete", "Phase complete: apply", {
            "change": "add-auth",
            "phase": "apply",
        })
        assert "[OK]" in fallback
        assert isinstance(blocks, list)
        assert len(blocks) >= 1
        assert blocks[0]["type"] == "header"

    def test_fields_included(self):
        fallback, blocks = _slack_format("phase_fail", "Phase FAILED", {
            "change": "fix-bug",
            "phase": "verify",
            "duration_s": 30.0,
            "error": "Test failed",
        })
        # Should have header + section with fields
        assert len(blocks) >= 2
        fields_block = blocks[1]
        assert fields_block["type"] == "section"
        field_texts = [f["text"] for f in fields_block["fields"]]
        assert any("fix-bug" in t for t in field_texts)

    def test_resume_cmd_block(self):
        _, blocks = _slack_format("phase_fail", "Failed", {
            "resume_cmd": "/resume cmd",
        })
        resume_blocks = [b for b in blocks if b.get("text", {}).get("text", "").startswith("*Resume:*")]
        assert len(resume_blocks) == 1

    def test_batch_results_blocks(self):
        _, blocks = _slack_format("batch_summary", "Batch", {
            "results": [
                {"name": "c1", "success": True},
                {"name": "c2", "success": False},
            ],
            "total_duration_s": 20.0,
        })
        # Should have header + summary section + per-change section
        assert len(blocks) >= 3


# ---------------------------------------------------------------------------
# Webhook formatting
# ---------------------------------------------------------------------------


class TestWebhookFormat:
    def test_basic_format(self):
        payload = _webhook_format("phase_start", "Phase starting", {
            "change": "add-auth",
        })
        assert payload["event"] == "phase_start"
        assert payload["title"] == "Phase starting"
        assert payload["change"] == "add-auth"
        assert "timestamp" in payload

    def test_details_merged(self):
        payload = _webhook_format("phase_complete", "Done", {
            "custom_field": "value",
        })
        assert payload["custom_field"] == "value"


# ---------------------------------------------------------------------------
# No-op when provider is "none"
# ---------------------------------------------------------------------------


class TestNoneProvider:
    def test_dispatch_returns_false(self):
        with patch.dict(os.environ, {"NOTIFY_PROVIDER": "none"}, clear=True):
            assert _dispatch("phase_start", "Test", {}) is False

    def test_notify_phase_start_noop(self):
        with patch.dict(os.environ, {"NOTIFY_PROVIDER": "none"}, clear=True):
            assert notify_phase_start("change", "apply") is False

    def test_send_raw_noop(self):
        with patch.dict(os.environ, {"NOTIFY_PROVIDER": "none"}, clear=True):
            assert send_raw("hello") is False


# ---------------------------------------------------------------------------
# Phase event messages (integration with dispatch)
# ---------------------------------------------------------------------------


class TestPhaseEvents:
    @patch("notifications._telegram_send", return_value=True)
    def test_phase_start(self, mock_send):
        with patch.dict(os.environ, {"NOTIFY_PROVIDER": "telegram"}, clear=True):
            result = notify_phase_start("add-auth", "apply")
            assert result is True
            mock_send.assert_called_once()
            call_text = mock_send.call_args[0][0]
            assert "apply" in call_text.lower()

    @patch("notifications._telegram_send", return_value=True)
    def test_phase_complete(self, mock_send):
        with patch.dict(os.environ, {"NOTIFY_PROVIDER": "telegram"}, clear=True):
            result = notify_phase_complete("add-auth", "apply", duration_s=30.0)
            assert result is True

    @patch("notifications._telegram_send", return_value=True)
    def test_phase_fail(self, mock_send):
        with patch.dict(os.environ, {"NOTIFY_PROVIDER": "telegram"}, clear=True):
            result = notify_phase_fail(
                "add-auth", "verify", error="Build failed",
            )
            assert result is True

    @patch("notifications._telegram_send", return_value=True)
    def test_phase_fail_default_resume_cmd(self, mock_send):
        with patch.dict(os.environ, {"NOTIFY_PROVIDER": "telegram"}, clear=True):
            notify_phase_fail("add-auth", "verify")
            call_text = mock_send.call_args[0][0]
            assert "/sdd-continue add-auth" in call_text


# ---------------------------------------------------------------------------
# Pipeline complete
# ---------------------------------------------------------------------------


class TestPipelineComplete:
    @patch("notifications._telegram_send", return_value=True)
    def test_pipeline_complete(self, mock_send):
        with patch.dict(os.environ, {"NOTIFY_PROVIDER": "telegram"}, clear=True):
            result = notify_pipeline_complete(
                "add-auth",
                phases_completed=["apply", "verify"],
                total_duration_s=120.0,
            )
            assert result is True


# ---------------------------------------------------------------------------
# Batch summary
# ---------------------------------------------------------------------------


class TestBatchSummary:
    @patch("notifications._telegram_send", return_value=True)
    def test_batch_summary(self, mock_send):
        with patch.dict(os.environ, {"NOTIFY_PROVIDER": "telegram"}, clear=True):
            results = [
                {"name": "c1", "success": True, "elapsed_s": 10.0},
                {"name": "c2", "success": False, "elapsed_s": 5.0},
            ]
            result = notify_batch_summary("batch-1", results, total_duration_s=15.0)
            assert result is True
            call_text = mock_send.call_args[0][0]
            assert "c1" in call_text
            assert "c2" in call_text


# ---------------------------------------------------------------------------
# send_raw via different providers
# ---------------------------------------------------------------------------


class TestSendRaw:
    @patch("notifications._telegram_send", return_value=True)
    def test_raw_telegram(self, mock_send):
        with patch.dict(os.environ, {"NOTIFY_PROVIDER": "telegram"}, clear=True):
            result = send_raw("hello world")
            assert result is True
            mock_send.assert_called_once_with("hello world")

    @patch("notifications._slack_send", return_value=True)
    def test_raw_slack(self, mock_send):
        with patch.dict(os.environ, {"NOTIFY_PROVIDER": "slack"}, clear=True):
            result = send_raw("hello world")
            assert result is True
            mock_send.assert_called_once_with("hello world")

    @patch("notifications._webhook_send", return_value=True)
    def test_raw_webhook(self, mock_send):
        with patch.dict(os.environ, {"NOTIFY_PROVIDER": "webhook"}, clear=True):
            result = send_raw("hello world")
            assert result is True
            payload = mock_send.call_args[0][0]
            assert payload["event"] == "raw"
            assert payload["text"] == "hello world"
