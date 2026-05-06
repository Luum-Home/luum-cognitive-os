"""Tests for lib/hook_types.py (ADR-178).

Verifies ShellHookDefinition (backward-compat), HttpHookDefinition,
and PromptHookDefinition construction, serialisation, and factory dispatch.
"""

from __future__ import annotations

import pytest

from lib.hook_types import (
    HttpHookDefinition,
    PromptHookDefinition,
    ShellHookDefinition,
    hook_from_dict,
)


# ---------------------------------------------------------------------------
# ShellHookDefinition
# ---------------------------------------------------------------------------


class TestShellHookDefinition:
    def test_defaults(self):
        h = ShellHookDefinition(command="echo hi")
        assert h.hook_type() == "command"
        assert h.timeout_seconds == 30
        assert h.block_on_failure is False
        assert h.matcher is None

    def test_from_dict_full(self):
        h = ShellHookDefinition.from_dict({
            "command": "scripts/my-hook.sh",
            "timeout_seconds": 60,
            "block_on_failure": True,
            "matcher": "PostToolUse",
        })
        assert h.command == "scripts/my-hook.sh"
        assert h.timeout_seconds == 60
        assert h.block_on_failure is True
        assert h.matcher == "PostToolUse"

    def test_from_dict_minimal(self):
        h = ShellHookDefinition.from_dict({"command": "ls"})
        assert h.command == "ls"
        assert h.timeout_seconds == 30


# ---------------------------------------------------------------------------
# HttpHookDefinition
# ---------------------------------------------------------------------------


class TestHttpHookDefinition:
    def test_defaults(self):
        h = HttpHookDefinition(url="https://example.com/webhook")
        assert h.hook_type() == "http"
        assert h.method == "POST"
        assert h.timeout_ms == 5000
        assert h.timeout_seconds == 5
        assert h.block_on_failure is False
        assert 200 in h.expected_status
        assert 204 in h.expected_status

    def test_render_body_default(self):
        h = HttpHookDefinition(url="https://x.com")
        rendered = h.render_body('{"event": "Stop"}')
        assert rendered == '{"event": "Stop"}'

    def test_render_body_custom_template(self):
        h = HttpHookDefinition(url="https://x.com", body_template='{"data": $payload}')
        rendered = h.render_body('"hello"')
        assert rendered == '{"data": "hello"}'

    def test_from_dict_full(self):
        h = HttpHookDefinition.from_dict({
            "type": "http",
            "url": "https://hooks.slack.com/trigger/abc",
            "method": "post",
            "headers": {"Authorization": "Bearer tok"},
            "timeout_ms": 3000,
            "body_template": "$payload",
            "expected_status": [200, 201],
            "block_on_failure": True,
            "matcher": "Stop",
        })
        assert h.url == "https://hooks.slack.com/trigger/abc"
        assert h.method == "POST"
        assert h.headers == {"Authorization": "Bearer tok"}
        assert h.timeout_ms == 3000
        assert h.timeout_seconds == 3
        assert h.block_on_failure is True
        assert h.matcher == "Stop"
        assert 200 in h.expected_status
        assert 204 not in h.expected_status

    def test_from_dict_timeout_seconds_compat(self):
        # upstream uses timeout_seconds; COS converts to ms
        h = HttpHookDefinition.from_dict({"url": "http://a.b", "timeout_seconds": 10})
        assert h.timeout_ms == 10_000
        assert h.timeout_seconds == 10

    def test_from_dict_expected_status_scalar(self):
        h = HttpHookDefinition.from_dict({"url": "http://a.b", "expected_status": 200})
        assert 200 in h.expected_status

    def test_headers_default_empty(self):
        h = HttpHookDefinition.from_dict({"url": "http://a.b"})
        assert h.headers == {}


# ---------------------------------------------------------------------------
# PromptHookDefinition
# ---------------------------------------------------------------------------


class TestPromptHookDefinition:
    def test_defaults(self):
        h = PromptHookDefinition(prompt_template="Is this safe?")
        assert h.hook_type() == "prompt"
        assert h.model_hint == "haiku"
        assert h.max_tokens == 256
        assert h.timeout_seconds == 30
        assert h.block_on_failure is True  # conservative default

    def test_prompt_alias(self):
        h = PromptHookDefinition(prompt_template="Check this.")
        assert h.prompt == "Check this."

    def test_render_prompt(self):
        h = PromptHookDefinition(prompt_template="Event: $event_json. Is it safe?")
        rendered = h.render_prompt('{"type": "Stop"}')
        assert rendered == 'Event: {"type": "Stop"}. Is it safe?'

    def test_from_dict_full(self):
        h = PromptHookDefinition.from_dict({
            "type": "prompt",
            "prompt_template": "Validate: $event_json",
            "model_hint": "sonnet",
            "inline_agent_subagent_type": "fast",
            "max_tokens": 512,
            "timeout_seconds": 45,
            "block_on_failure": False,
            "matcher": "PreToolUse",
        })
        assert h.prompt_template == "Validate: $event_json"
        assert h.model_hint == "sonnet"
        assert h.inline_agent_subagent_type == "fast"
        assert h.max_tokens == 512
        assert h.timeout_seconds == 45
        assert h.block_on_failure is False
        assert h.matcher == "PreToolUse"

    def test_from_dict_upstream_prompt_compat(self):
        # upstream uses 'prompt'; we accept that too
        h = PromptHookDefinition.from_dict({"prompt": "Is this ok?", "model": "opus"})
        assert h.prompt_template == "Is this ok?"
        assert h.model_hint == "opus"

    def test_model_hint_invalid_falls_back_to_haiku(self):
        h = PromptHookDefinition.from_dict({"prompt": "x", "model_hint": "gpt-5"})
        assert h.model_hint == "haiku"


# ---------------------------------------------------------------------------
# hook_from_dict factory
# ---------------------------------------------------------------------------


class TestHookFromDict:
    def test_dispatch_command(self):
        h = hook_from_dict({"type": "command", "command": "echo"})
        assert isinstance(h, ShellHookDefinition)

    def test_dispatch_shell_alias(self):
        h = hook_from_dict({"type": "shell", "command": "echo"})
        assert isinstance(h, ShellHookDefinition)

    def test_dispatch_legacy_no_type(self):
        # backward compat: no 'type' key but has 'command'
        h = hook_from_dict({"command": "scripts/foo.sh"})
        assert isinstance(h, ShellHookDefinition)

    def test_dispatch_http(self):
        h = hook_from_dict({"type": "http", "url": "https://a.b"})
        assert isinstance(h, HttpHookDefinition)

    def test_dispatch_prompt(self):
        h = hook_from_dict({"type": "prompt", "prompt_template": "Check."})
        assert isinstance(h, PromptHookDefinition)

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown hook type"):
            hook_from_dict({"type": "agent", "prompt": "x"})
