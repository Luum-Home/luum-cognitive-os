"""Unit tests for lib/claude_executor.py

Validates ClaudeResult dataclass, ClaudeExecutor initialization, model name
resolution, safe env filtering, cost calculation, retry code classification,
command building, subprocess execution (mocked), and JSONL stream parsing.
"""
import json
import os
import subprocess
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

import sys
from pathlib import Path

# Ensure lib/ is importable
_LIB_DIR = str(Path(__file__).resolve().parent.parent.parent / "lib")
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from claude_executor import (
    ClaudeExecutor,
    ClaudeResult,
    RetryCode,
    ToolCall,
    MODEL_MAP,
    MODEL_COSTS,
    ENV_ALLOWLIST,
    _classify_error,
    _estimate_cost,
    _get_safe_env,
    _model_family,
    _resolve_model,
    _tool_summary,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# ClaudeResult dataclass
# ---------------------------------------------------------------------------


class TestClaudeResult:
    def test_default_creation(self):
        r = ClaudeResult(success=True, result_text="hello")
        assert r.success is True
        assert r.result_text == "hello"
        assert r.tokens_in == 0
        assert r.tokens_out == 0
        assert r.cost_usd == 0.0
        assert r.duration_secs == 0.0
        assert r.tool_calls == []
        assert r.model_used == ""
        assert r.session_id == ""
        assert r.retry_code == RetryCode.NONE
        assert r.error_message == ""
        assert r.exit_code == 0

    def test_full_creation(self):
        tc = ToolCall(name="Read", input_summary="/some/file", tool_use_id="t1")
        r = ClaudeResult(
            success=False,
            result_text="error output",
            tokens_in=1000,
            tokens_out=500,
            cost_usd=0.123,
            duration_secs=42.5,
            tool_calls=[tc],
            model_used="claude-opus-4-20250514",
            session_id="sess-abc",
            retry_code=RetryCode.RATE_LIMIT,
            error_message="rate limited",
            exit_code=1,
        )
        assert r.success is False
        assert r.tokens_in == 1000
        assert r.tokens_out == 500
        assert len(r.tool_calls) == 1
        assert r.tool_calls[0].name == "Read"
        assert r.retry_code == RetryCode.RATE_LIMIT
        assert r.exit_code == 1


class TestToolCall:
    def test_creation(self):
        tc = ToolCall(name="Bash", input_summary="ls -la")
        assert tc.name == "Bash"
        assert tc.input_summary == "ls -la"
        assert tc.tool_use_id == ""


# ---------------------------------------------------------------------------
# Model name resolution
# ---------------------------------------------------------------------------


class TestResolveModel:
    def test_opus(self):
        assert _resolve_model("opus") == "claude-opus-4-20250514"

    def test_sonnet(self):
        assert _resolve_model("sonnet") == "claude-sonnet-4-20250514"

    def test_haiku(self):
        assert _resolve_model("haiku") == "claude-haiku-3-5-20241022"

    def test_full_id_passthrough(self):
        full_id = "claude-opus-4-20250514"
        assert _resolve_model(full_id) == full_id

    def test_none_returns_none(self):
        assert _resolve_model(None) is None

    def test_unknown_passthrough(self):
        assert _resolve_model("custom-model-v2") == "custom-model-v2"


class TestModelFamily:
    def test_opus_family(self):
        assert _model_family("claude-opus-4-20250514") == "opus"

    def test_sonnet_family(self):
        assert _model_family("claude-sonnet-4-20250514") == "sonnet"

    def test_haiku_family(self):
        assert _model_family("claude-haiku-3-5-20241022") == "haiku"

    def test_unknown_defaults_sonnet(self):
        assert _model_family("unknown-model") == "sonnet"


# ---------------------------------------------------------------------------
# Safe env filtering
# ---------------------------------------------------------------------------


class TestGetSafeEnv:
    def test_allowlisted_vars_pass_through(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test", "HOME": "/home/user"}, clear=True):
            env = _get_safe_env()
            assert env["ANTHROPIC_API_KEY"] == "sk-test"
            assert env["HOME"] == "/home/user"

    def test_non_allowlisted_vars_filtered(self):
        with patch.dict(os.environ, {"SECRET_KEY": "bad", "HOME": "/home"}, clear=True):
            env = _get_safe_env()
            assert "SECRET_KEY" not in env
            assert "HOME" in env

    def test_always_includes_pythonunbuffered_and_pwd(self):
        with patch.dict(os.environ, {}, clear=True):
            env = _get_safe_env()
            assert env["PYTHONUNBUFFERED"] == "1"
            assert "PWD" in env

    def test_github_pat_maps_to_gh_token(self):
        with patch.dict(os.environ, {"GITHUB_PAT": "ghp-123"}, clear=True):
            env = _get_safe_env()
            assert env["GH_TOKEN"] == "ghp-123"

    def test_gh_token_takes_priority_over_pat(self):
        with patch.dict(
            os.environ,
            {"GH_TOKEN": "gh-orig", "GITHUB_PAT": "ghp-123"},
            clear=True,
        ):
            env = _get_safe_env()
            assert env["GH_TOKEN"] == "gh-orig"

    def test_extra_env_merged(self):
        with patch.dict(os.environ, {}, clear=True):
            env = _get_safe_env(extra_env={"CUSTOM_VAR": "value"})
            assert env["CUSTOM_VAR"] == "value"


# ---------------------------------------------------------------------------
# Cost calculation
# ---------------------------------------------------------------------------


class TestEstimateCost:
    def test_opus_cost(self):
        # 1M input tokens at $15, 1M output tokens at $75 = $90
        cost = _estimate_cost(1_000_000, 1_000_000, "opus")
        assert abs(cost - 90.0) < 0.01

    def test_sonnet_cost(self):
        # 1M input at $3, 1M output at $15 = $18
        cost = _estimate_cost(1_000_000, 1_000_000, "sonnet")
        assert abs(cost - 18.0) < 0.01

    def test_haiku_cost(self):
        # 1M input at $0.25, 1M output at $1.25 = $1.50
        cost = _estimate_cost(1_000_000, 1_000_000, "haiku")
        assert abs(cost - 1.50) < 0.01

    def test_zero_tokens(self):
        assert _estimate_cost(0, 0, "opus") == 0.0

    def test_unknown_model_defaults_sonnet(self):
        cost = _estimate_cost(1_000_000, 0, "unknown")
        expected = _estimate_cost(1_000_000, 0, "sonnet")
        assert cost == expected

    def test_small_token_count(self):
        # 10K input at opus ($15/1M) = $0.15
        cost = _estimate_cost(10_000, 0, "opus")
        assert abs(cost - 0.15) < 0.001


# ---------------------------------------------------------------------------
# Retry code classification
# ---------------------------------------------------------------------------


class TestClassifyError:
    def test_rate_limit_from_stderr(self):
        assert _classify_error(1, "rate limit exceeded") == RetryCode.RATE_LIMIT

    def test_429_in_stderr(self):
        assert _classify_error(1, "HTTP 429 Too Many Requests") == RetryCode.RATE_LIMIT

    def test_auth_error(self):
        assert _classify_error(1, "auth failed") == RetryCode.AUTH_ERROR

    def test_401_in_stderr(self):
        assert _classify_error(1, "HTTP 401") == RetryCode.AUTH_ERROR

    def test_api_key_error(self):
        assert _classify_error(1, "invalid api key") == RetryCode.AUTH_ERROR

    def test_generic_nonzero_exit(self):
        assert _classify_error(1, "something failed") == RetryCode.CLAUDE_CODE_ERROR

    def test_zero_exit_no_error(self):
        assert _classify_error(0, "") == RetryCode.NONE

    def test_retryable_codes(self):
        from claude_executor import _RETRYABLE_CODES, _NON_RETRYABLE_CODES
        assert RetryCode.RATE_LIMIT in _RETRYABLE_CODES
        assert RetryCode.TIMEOUT_ERROR in _RETRYABLE_CODES
        assert RetryCode.CLAUDE_CODE_ERROR in _RETRYABLE_CODES
        assert RetryCode.AUTH_ERROR in _NON_RETRYABLE_CODES


# ---------------------------------------------------------------------------
# Tool summary
# ---------------------------------------------------------------------------


class TestToolSummary:
    def test_read(self):
        s = _tool_summary("Read", {"file_path": "/very/long/path/to/file.py"})
        assert "file.py" in s

    def test_bash(self):
        s = _tool_summary("Bash", {"command": "ls -la"})
        assert s == "ls -la"

    def test_grep(self):
        s = _tool_summary("Grep", {"pattern": "TODO", "path": "src/"})
        assert "TODO" in s
        assert "src/" in s

    def test_unknown_tool(self):
        s = _tool_summary("UnknownTool", {"foo": "bar"})
        assert s == ""


# ---------------------------------------------------------------------------
# ClaudeExecutor initialization
# ---------------------------------------------------------------------------


class TestClaudeExecutorInit:
    def test_defaults(self):
        with patch.dict(os.environ, {}, clear=False):
            executor = ClaudeExecutor()
            assert executor.working_dir == os.getcwd()
            assert executor.default_timeout == 600
            assert executor.default_model is None
            assert executor.allowed_tools is None
            assert executor.verbose is False

    def test_custom_params(self):
        executor = ClaudeExecutor(
            working_dir="/tmp/test",
            claude_path="/usr/local/bin/claude",
            default_model="opus",
            default_timeout=300,
            allowed_tools=["Read", "Write"],
            verbose=True,
        )
        assert executor.working_dir == "/tmp/test"
        assert executor.claude_path == "/usr/local/bin/claude"
        assert executor.default_model == "opus"
        assert executor.default_timeout == 300
        assert executor.allowed_tools == ["Read", "Write"]
        assert executor.verbose is True

    def test_claude_path_from_env(self):
        with patch.dict(os.environ, {"CLAUDE_CODE_PATH": "/custom/claude"}):
            executor = ClaudeExecutor()
            assert executor.claude_path == "/custom/claude"


# ---------------------------------------------------------------------------
# Command building
# ---------------------------------------------------------------------------


class TestBuildCommand:
    def test_basic_prompt(self):
        executor = ClaudeExecutor(claude_path="claude")
        cmd = executor._build_command("hello world")
        assert cmd[0] == "claude"
        assert "-p" in cmd
        assert "hello world" in cmd
        assert "--output-format" in cmd
        assert "stream-json" in cmd
        assert "--verbose" in cmd

    def test_with_model(self):
        executor = ClaudeExecutor(claude_path="claude")
        cmd = executor._build_command("test", model="opus")
        assert "--model" in cmd
        model_idx = cmd.index("--model")
        assert cmd[model_idx + 1] == "claude-opus-4-20250514"

    def test_with_default_model(self):
        executor = ClaudeExecutor(claude_path="claude", default_model="haiku")
        cmd = executor._build_command("test")
        assert "--model" in cmd
        model_idx = cmd.index("--model")
        assert cmd[model_idx + 1] == "claude-haiku-3-5-20241022"

    def test_model_override(self):
        executor = ClaudeExecutor(claude_path="claude", default_model="haiku")
        cmd = executor._build_command("test", model="opus")
        model_idx = cmd.index("--model")
        assert cmd[model_idx + 1] == "claude-opus-4-20250514"

    def test_with_allowed_tools(self):
        executor = ClaudeExecutor(claude_path="claude")
        cmd = executor._build_command("test", allowed_tools=["Read", "Write"])
        assert cmd.count("--allowedTools") == 2
        # Verify tools follow their flags
        indices = [i for i, v in enumerate(cmd) if v == "--allowedTools"]
        assert cmd[indices[0] + 1] == "Read"
        assert cmd[indices[1] + 1] == "Write"

    def test_instance_allowed_tools(self):
        executor = ClaudeExecutor(claude_path="claude", allowed_tools=["Bash"])
        cmd = executor._build_command("test")
        assert "--allowedTools" in cmd
        idx = cmd.index("--allowedTools")
        assert cmd[idx + 1] == "Bash"

    def test_no_model_no_flag(self):
        executor = ClaudeExecutor(claude_path="claude")
        cmd = executor._build_command("test")
        assert "--model" not in cmd


# ---------------------------------------------------------------------------
# Stream parsing
# ---------------------------------------------------------------------------


class TestParseStream:
    def _make_executor(self):
        return ClaudeExecutor(claude_path="claude")

    def test_parse_result_message(self):
        executor = self._make_executor()
        messages = [
            {
                "type": "result",
                "result": "Final answer here",
                "session_id": "sess-123",
                "is_error": False,
            }
        ]
        text, tools, t_in, t_out, model, sess = executor._parse_stream(messages)
        assert text == "Final answer here"
        assert sess == "sess-123"
        assert tools == []
        assert t_in == 0
        assert t_out == 0

    def test_parse_assistant_text(self):
        executor = self._make_executor()
        messages = [
            {
                "type": "assistant",
                "message": {
                    "content": [{"type": "text", "text": "Some output"}],
                    "usage": {"input_tokens": 100, "output_tokens": 50},
                    "model": "claude-sonnet-4-20250514",
                },
            }
        ]
        text, tools, t_in, t_out, model, sess = executor._parse_stream(messages)
        assert text == "Some output"  # fallback since no result message
        assert t_in == 100
        assert t_out == 50
        assert model == "claude-sonnet-4-20250514"

    def test_parse_tool_use(self):
        executor = self._make_executor()
        messages = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Read",
                            "input": {"file_path": "/test/file.py"},
                            "id": "tu-1",
                        }
                    ],
                    "usage": {},
                },
            }
        ]
        text, tools, t_in, t_out, model, sess = executor._parse_stream(messages)
        assert len(tools) == 1
        assert tools[0].name == "Read"
        assert tools[0].tool_use_id == "tu-1"

    def test_parse_error_result(self):
        executor = self._make_executor()
        messages = [
            {
                "type": "result",
                "result": "",
                "is_error": True,
                "error": "Something went wrong",
                "session_id": "s1",
            }
        ]
        text, tools, t_in, t_out, model, sess = executor._parse_stream(messages)
        assert "[error]" in text
        assert "Something went wrong" in text

    def test_tokens_accumulated(self):
        executor = self._make_executor()
        messages = [
            {
                "type": "assistant",
                "message": {
                    "content": [],
                    "usage": {"input_tokens": 100, "output_tokens": 50},
                },
            },
            {
                "type": "assistant",
                "message": {
                    "content": [],
                    "usage": {"input_tokens": 200, "output_tokens": 100},
                },
            },
            {
                "type": "result",
                "result": "done",
                "session_id": "s1",
                "usage": {"input_tokens": 50, "output_tokens": 25},
            },
        ]
        text, tools, t_in, t_out, model, sess = executor._parse_stream(messages)
        assert t_in == 350  # 100 + 200 + 50
        assert t_out == 175  # 50 + 100 + 25


# ---------------------------------------------------------------------------
# run() — mocked subprocess
# ---------------------------------------------------------------------------


class TestRun:
    def _mock_process(self, stdout_lines, returncode=0, stderr=""):
        """Create a mock Popen object."""
        process = MagicMock()
        process.stdout = iter(stdout_lines)
        process.stderr = MagicMock()
        process.stderr.read.return_value = stderr
        process.returncode = returncode
        process.pid = 12345
        process.wait.return_value = None
        return process

    @patch("claude_executor.subprocess.Popen")
    def test_successful_run(self, mock_popen):
        result_msg = json.dumps({
            "type": "result",
            "result": "All done",
            "session_id": "s1",
            "is_error": False,
        })
        process = self._mock_process([result_msg + "\n"], returncode=0)
        mock_popen.return_value = process

        executor = ClaudeExecutor(claude_path="claude")
        result = executor.run("test prompt")

        assert result.success is True
        assert result.result_text == "All done"
        assert result.exit_code == 0
        assert result.retry_code == RetryCode.NONE

    @patch("claude_executor.subprocess.Popen")
    def test_failed_run(self, mock_popen):
        process = self._mock_process([], returncode=1, stderr="something failed")
        mock_popen.return_value = process

        executor = ClaudeExecutor(claude_path="claude")
        result = executor.run("test prompt")

        assert result.success is False
        assert result.exit_code == 1
        assert result.retry_code == RetryCode.CLAUDE_CODE_ERROR

    @patch("claude_executor.subprocess.Popen")
    def test_timeout_run(self, mock_popen):
        process = self._mock_process([], returncode=0)
        process.wait.side_effect = subprocess.TimeoutExpired(cmd="claude", timeout=10)
        mock_popen.return_value = process

        with patch("claude_executor._kill_process_group"):
            executor = ClaudeExecutor(claude_path="claude", default_timeout=10)
            result = executor.run("test prompt")

        assert result.success is False
        assert result.retry_code == RetryCode.TIMEOUT_ERROR
        assert "Timeout" in result.result_text

    @patch("claude_executor.subprocess.Popen")
    def test_exception_during_run(self, mock_popen):
        mock_popen.side_effect = OSError("No such file")

        executor = ClaudeExecutor(claude_path="nonexistent")
        result = executor.run("test prompt")

        assert result.success is False
        assert result.retry_code == RetryCode.EXECUTION_ERROR
        assert "No such file" in result.error_message

    @patch("claude_executor.subprocess.Popen")
    def test_is_error_in_result_message(self, mock_popen):
        result_msg = json.dumps({
            "type": "result",
            "result": "Task failed",
            "session_id": "s1",
            "is_error": True,
        })
        process = self._mock_process([result_msg + "\n"], returncode=0)
        mock_popen.return_value = process

        executor = ClaudeExecutor(claude_path="claude")
        result = executor.run("test prompt")

        # Exit code 0 but is_error=True in result
        assert result.success is False


# ---------------------------------------------------------------------------
# slash() command
# ---------------------------------------------------------------------------


class TestSlash:
    @patch.object(ClaudeExecutor, "run")
    def test_slash_prepends_slash(self, mock_run):
        mock_run.return_value = ClaudeResult(success=True, result_text="ok")
        executor = ClaudeExecutor()
        executor.slash("plan-feature", args="my-feature")
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[1]["prompt"] == "/plan-feature my-feature"

    @patch.object(ClaudeExecutor, "run")
    def test_slash_already_has_slash(self, mock_run):
        mock_run.return_value = ClaudeResult(success=True, result_text="ok")
        executor = ClaudeExecutor()
        executor.slash("/plan-feature")
        call_args = mock_run.call_args
        assert call_args[1]["prompt"] == "/plan-feature"
