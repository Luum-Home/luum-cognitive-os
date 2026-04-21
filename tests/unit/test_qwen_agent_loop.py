# SCOPE: both
"""Unit tests for lib/qwen_agent_loop (ADR-051 Phase 1).

All tests mock the openai-compatible client via types.SimpleNamespace — no
real Qwen API calls. The client is passed via `run_agent(..., client=...)`
to bypass qwen_provider._get_openai_client() entirely.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Iterable, List

import pytest

from lib import qwen_agent_loop as qal


# ---------------------------------------------------------------------------
# Helpers to build mock OpenAI-SDK-shaped responses.
# ---------------------------------------------------------------------------


def _mk_tool_call(call_id: str, name: str, arguments: Dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(
        id=call_id,
        type="function",
        function=SimpleNamespace(name=name, arguments=json.dumps(arguments)),
    )


def _mk_response(
    content: str = "",
    tool_calls: List[SimpleNamespace] | None = None,
    prompt_tokens: int = 100,
    completion_tokens: int = 50,
) -> SimpleNamespace:
    msg = SimpleNamespace(content=content, tool_calls=tool_calls or [])
    return SimpleNamespace(
        choices=[SimpleNamespace(message=msg)],
        usage=SimpleNamespace(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens),
    )


class _FakeClient:
    """Client that replays a scripted sequence of responses."""

    def __init__(self, responses: Iterable[SimpleNamespace]):
        self._responses = list(responses)
        self._calls = 0
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self._create)
        )

    def _create(self, **kwargs: Any) -> SimpleNamespace:
        if self._calls >= len(self._responses):
            # Default to "finished, no tools" if exhausted — keeps loops safe.
            return _mk_response(content="(exhausted scripted responses)")
        resp = self._responses[self._calls]
        self._calls += 1
        return resp


# ---------------------------------------------------------------------------
# 1. Simple task, no tools.
# ---------------------------------------------------------------------------


def test_simple_task_no_tools():
    client = _FakeClient([_mk_response(content="Hello, world!")])
    result = qal.run_agent("say hi", client=client)

    assert result.success is True
    assert result.stop_reason == "finished"
    assert result.text == "Hello, world!"
    assert result.tool_calls_made == 0
    assert result.iterations == 1
    assert result.tokens_in == 100
    assert result.tokens_out == 50


# ---------------------------------------------------------------------------
# 2. read_file tool round-trip.
# ---------------------------------------------------------------------------


def test_read_file_tool(tmp_path: Path):
    target = tmp_path / "hello.txt"
    target.write_text("contents of hello")

    client = _FakeClient([
        _mk_response(tool_calls=[
            _mk_tool_call("c1", "read_file", {"path": str(target)})
        ]),
        _mk_response(content="The file says: contents of hello"),
    ])
    result = qal.run_agent(f"read {target} and summarize", client=client)

    assert result.success is True
    assert result.tool_calls_made == 1
    assert result.iterations == 2
    assert result.text == "The file says: contents of hello"
    # Verify the tool result was fed back into messages as role=tool.
    roles = [m["role"] for m in result.messages_history]
    assert "tool" in roles
    tool_msg = next(m for m in result.messages_history if m["role"] == "tool")
    assert "contents of hello" in tool_msg["content"]


# ---------------------------------------------------------------------------
# 3. edit_file tool: happy path + missing file error.
# ---------------------------------------------------------------------------


def test_edit_file_tool_happy_path(tmp_path: Path):
    target = tmp_path / "note.txt"
    target.write_text("the quick brown fox")

    client = _FakeClient([
        _mk_response(tool_calls=[
            _mk_tool_call("c1", "edit_file", {
                "path": str(target),
                "old_string": "quick brown",
                "new_string": "slow purple",
            })
        ]),
        _mk_response(content="done"),
    ])
    result = qal.run_agent("rename the fox color", client=client)

    assert result.success is True
    assert target.read_text() == "the slow purple fox"
    assert result.tool_log[0]["name"] == "edit_file"
    assert "OK: replaced" in result.tool_log[0]["result_preview"]


def test_edit_file_nonexistent_file_reports_error(tmp_path: Path):
    missing = tmp_path / "nope.txt"

    client = _FakeClient([
        _mk_response(tool_calls=[
            _mk_tool_call("c1", "edit_file", {
                "path": str(missing),
                "old_string": "a",
                "new_string": "b",
            })
        ]),
        _mk_response(content="I could not edit it"),
    ])
    result = qal.run_agent("try to edit missing file", client=client)

    # Loop continues — the error is surfaced to the model, not raised.
    assert result.success is True
    tool_msg = next(m for m in result.messages_history if m["role"] == "tool")
    assert "does not exist" in tool_msg["content"]


# ---------------------------------------------------------------------------
# 4. run_bash: happy path + blocklist rejection.
# ---------------------------------------------------------------------------


def test_run_bash_tool_happy_path():
    client = _FakeClient([
        _mk_response(tool_calls=[
            _mk_tool_call("c1", "run_bash", {"command": "echo hello-from-bash"})
        ]),
        _mk_response(content="observed hello-from-bash"),
    ])
    result = qal.run_agent("run echo", client=client)

    assert result.success is True
    tool_msg = next(m for m in result.messages_history if m["role"] == "tool")
    assert "hello-from-bash" in tool_msg["content"]
    assert "exit_code: 0" in tool_msg["content"]


def test_run_bash_blocklist_rejects_rm_rf():
    client = _FakeClient([
        _mk_response(tool_calls=[
            _mk_tool_call("c1", "run_bash", {"command": "rm -rf /tmp/something"})
        ]),
        _mk_response(content="could not run it"),
    ])
    result = qal.run_agent("try destructive", client=client)

    assert result.success is True  # loop itself doesn't fail
    tool_msg = next(m for m in result.messages_history if m["role"] == "tool")
    assert "rejected by blocklist" in tool_msg["content"]
    assert "rm -rf" in tool_msg["content"]


# ---------------------------------------------------------------------------
# 5. max_iterations cap.
# ---------------------------------------------------------------------------


def test_max_iterations_cap():
    # Every response asks for another read_file — the loop must bail.
    def infinite_responses():
        i = 0
        while True:
            i += 1
            yield _mk_response(tool_calls=[
                _mk_tool_call(f"c{i}", "read_file", {"path": "/nonexistent"})
            ])

    gen = infinite_responses()
    client = _FakeClient([next(gen) for _ in range(25)])

    result = qal.run_agent("loop forever", max_iterations=5, client=client)

    assert result.success is False
    assert result.stop_reason == "max_iterations"
    assert result.iterations == 5
    assert "max_iterations" in result.error


# ---------------------------------------------------------------------------
# 6. Token budget cap.
# ---------------------------------------------------------------------------


def test_token_budget_cap():
    # Each response reports 60K prompt + 60K completion = 120K → blows a 100K budget on first turn.
    client = _FakeClient([
        _mk_response(
            content="I'm working...",
            tool_calls=[_mk_tool_call("c1", "read_file", {"path": "/nowhere"})],
            prompt_tokens=60_000,
            completion_tokens=60_000,
        ),
    ])
    result = qal.run_agent("expensive task", token_budget=100_000, client=client)

    assert result.success is False
    assert result.stop_reason == "budget"
    assert "token budget" in result.error


# ---------------------------------------------------------------------------
# 7. tools_allowed filter rejects disallowed tool.
# ---------------------------------------------------------------------------


def test_tools_allowed_filter_rejects_disallowed():
    client = _FakeClient([
        _mk_response(tool_calls=[
            _mk_tool_call("c1", "edit_file", {
                "path": "/tmp/x", "old_string": "a", "new_string": "b",
            })
        ]),
        _mk_response(content="gave up"),
    ])
    result = qal.run_agent(
        "try to edit",
        tools_allowed=["read_file"],
        client=client,
    )

    assert result.success is True
    tool_msg = next(m for m in result.messages_history if m["role"] == "tool")
    assert "not in the allowed list" in tool_msg["content"]
    assert "edit_file" in tool_msg["content"]


def test_tools_allowed_rejects_unknown_name_upfront():
    # Unknown tool names are caught BEFORE any API call.
    client = _FakeClient([])
    result = qal.run_agent(
        "task",
        tools_allowed=["read_file", "does_not_exist"],
        client=client,
    )
    assert result.success is False
    assert result.stop_reason == "error"
    assert "unknown tool" in result.error


# ---------------------------------------------------------------------------
# 8. Tool execution error is captured, loop continues.
# ---------------------------------------------------------------------------


def test_tool_call_execution_error_captured(monkeypatch: pytest.MonkeyPatch):
    def boom(_args: Dict[str, Any]) -> str:
        raise RuntimeError("simulated tool crash")

    # Swap the read_file impl for one that raises internally... but tools are
    # expected to return errors as strings, not raise. Test via a JSON-arg
    # error instead (model sends malformed arguments).
    client = _FakeClient([
        # Malformed JSON in arguments:
        _mk_response(tool_calls=[
            SimpleNamespace(
                id="c1",
                type="function",
                function=SimpleNamespace(name="read_file", arguments="{not json"),
            )
        ]),
        _mk_response(content="saw the error, moving on"),
    ])
    result = qal.run_agent("test error handling", client=client)

    assert result.success is True
    tool_msg = next(m for m in result.messages_history if m["role"] == "tool")
    assert "invalid JSON" in tool_msg["content"]


def test_tool_impl_raises_surfaces_as_error(monkeypatch: pytest.MonkeyPatch):
    # If an impl (hypothetically) raises anyway, the dispatch catches at the
    # impl layer — read_file uses a try/except BLE001 wrapper. Verify by
    # passing a path that triggers an OS-level exception.
    client = _FakeClient([
        _mk_response(tool_calls=[
            _mk_tool_call("c1", "read_file", {"path": "/dev/null/impossible"})
        ]),
        _mk_response(content="done"),
    ])
    result = qal.run_agent("read impossible path", client=client)

    assert result.success is True
    tool_msg = next(m for m in result.messages_history if m["role"] == "tool")
    # Either "does not exist", "not a regular file", or an OSError — all ERROR-prefixed.
    assert tool_msg["content"].startswith("ERROR")


# ---------------------------------------------------------------------------
# 9. Tool schemas are valid OpenAI function-calling JSON.
# ---------------------------------------------------------------------------


def test_full_api_schema_valid():
    # Every schema must be JSON-serializable, have the correct top-level
    # shape, and declare a JSON-Schema-ish `parameters` object.
    serialized = json.dumps(qal.TOOL_SCHEMAS)
    reloaded = json.loads(serialized)
    assert reloaded == qal.TOOL_SCHEMAS

    for schema in qal.TOOL_SCHEMAS:
        assert schema["type"] == "function"
        fn = schema["function"]
        assert isinstance(fn["name"], str) and fn["name"]
        assert isinstance(fn["description"], str) and fn["description"]

        params = fn["parameters"]
        assert params["type"] == "object"
        assert isinstance(params["properties"], dict) and params["properties"]
        assert isinstance(params["required"], list) and params["required"]
        # Every required param must be declared in properties.
        for req in params["required"]:
            assert req in params["properties"], f"missing property for required={req}"

    # Tool names must match the dispatch table exactly.
    schema_names = {s["function"]["name"] for s in qal.TOOL_SCHEMAS}
    assert schema_names == set(qal.TOOL_IMPLS.keys())
    assert schema_names == qal.ALL_TOOL_NAMES


# ---------------------------------------------------------------------------
# 10. Phase 2 tools — web_fetch, grep_files, glob_files + refactored read_file/run_bash.
# ---------------------------------------------------------------------------


def test_phase2_all_tools_registered():
    """The six tools of Phase 2 must all be present with matching impls."""
    expected = {"read_file", "edit_file", "run_bash", "web_fetch", "grep_files", "glob_files"}
    assert expected == set(qal.TOOL_IMPLS.keys())
    assert expected == qal.ALL_TOOL_NAMES


def test_read_file_uses_smart_reader(tmp_path, monkeypatch):
    """read_file should delegate to SmartReader (ADR-044 reuse)."""
    target = tmp_path / "hello.txt"
    target.write_text("hello world")

    called = {"count": 0}

    class _StubReader:
        def read_file(self, path):
            called["count"] += 1
            return SimpleNamespace(content=f"STUB:{path}")

    import lib.smart_reader as sr
    monkeypatch.setattr(sr, "SmartReader", _StubReader)

    out = qal._tool_read_file({"path": str(target)})
    assert called["count"] == 1
    assert out == f"STUB:{target}"


def test_read_file_fallback_when_smart_reader_raises(tmp_path, monkeypatch):
    """If SmartReader throws, fall back to direct read."""
    target = tmp_path / "hi.txt"
    target.write_text("raw content")

    class _BrokenReader:
        def read_file(self, path):
            raise RuntimeError("smart reader broken")

    import lib.smart_reader as sr
    monkeypatch.setattr(sr, "SmartReader", _BrokenReader)

    out = qal._tool_read_file({"path": str(target)})
    assert out == "raw content"


def test_read_file_missing_path():
    out = qal._tool_read_file({"path": "/nonexistent/path/abc.xyz"})
    assert out.startswith("ERROR:")
    assert "does not exist" in out


def test_run_bash_truncates_large_output(tmp_path):
    # Generate >5000 chars of output via printf
    result = qal._tool_run_bash({"command": "python3 -c 'print(\"x\"*6000)'", "timeout_s": 10})
    assert "exit_code: 0" in result
    # smart_truncate should have bounded it
    assert len(result) < 7000  # well below 6000+header if no truncation


def test_run_bash_blocklist_rm_rf():
    result = qal._tool_run_bash({"command": "echo hi && rm -rf /tmp/foo"})
    assert result.startswith("ERROR:")
    assert "blocklist" in result


def test_web_fetch_delegates_to_crawler(monkeypatch):
    """web_fetch must call lib.web_crawler.fetch_markdown_sync."""
    calls = {"url": None, "timeout": None}

    def _fake_fetch(url, timeout=30):
        calls["url"] = url
        calls["timeout"] = timeout
        return "# Markdown\ncontent here"

    import lib.web_crawler as wc
    monkeypatch.setattr(wc, "fetch_markdown_sync", _fake_fetch)

    out = qal._tool_web_fetch({"url": "https://example.com", "timeout_s": 15})
    assert calls["url"] == "https://example.com"
    assert calls["timeout"] == 15
    assert "# Markdown" in out


def test_web_fetch_missing_url():
    out = qal._tool_web_fetch({})
    assert out.startswith("ERROR:")
    assert "url" in out


def test_web_fetch_surfaces_crawler_error(monkeypatch):
    def _fake_fetch(url, timeout=30):
        raise ValueError("invalid URL scheme")

    import lib.web_crawler as wc
    monkeypatch.setattr(wc, "fetch_markdown_sync", _fake_fetch)

    out = qal._tool_web_fetch({"url": "ftp://nope"})
    assert out.startswith("ERROR: fetch failed")
    assert "ValueError" in out


def test_grep_files_finds_matches(tmp_path):
    f = tmp_path / "sample.py"
    f.write_text("def foo():\n    pass\n\ndef bar():\n    return foo()\n")

    out = qal._tool_grep_files({"pattern": "def foo", "path": str(tmp_path)})
    assert "def foo" in out
    assert "sample.py" in out


def test_grep_files_no_matches(tmp_path):
    f = tmp_path / "sample.py"
    f.write_text("nothing here\n")

    out = qal._tool_grep_files({"pattern": "zzz_never_found", "path": str(tmp_path)})
    assert out == "no matches"


def test_grep_files_missing_pattern():
    out = qal._tool_grep_files({"path": "."})
    assert out.startswith("ERROR:")
    assert "pattern" in out


def test_glob_files_finds_files(tmp_path):
    (tmp_path / "a.py").write_text("")
    (tmp_path / "b.py").write_text("")
    (tmp_path / "c.txt").write_text("")

    out = qal._tool_glob_files({"pattern": "*.py", "path": str(tmp_path)})
    assert "a.py" in out
    assert "b.py" in out
    assert "c.txt" not in out


def test_glob_files_no_matches(tmp_path):
    out = qal._tool_glob_files({"pattern": "*.nonexistent", "path": str(tmp_path)})
    assert out == "no matches"


def test_glob_files_missing_pattern():
    out = qal._tool_glob_files({"path": "."})
    assert out.startswith("ERROR:")
    assert "pattern" in out


def test_glob_files_bad_root():
    out = qal._tool_glob_files({"pattern": "*.py", "path": "/definitely/does/not/exist/xyz123"})
    assert out.startswith("ERROR:")
    assert "does not exist" in out
