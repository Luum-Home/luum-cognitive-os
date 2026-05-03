"""Characterization tests for lib.engram_client.

These tests lock in the CURRENT observable behavior of the module so that any
upcoming refactor (e.g. having safe_engram.safe_save delegate here) breaks
loudly if it changes return shapes, error semantics, or CLI argument layout.

Covers:
  - search_observations: happy path, list/dict-with-results parsing, limit slice,
    empty stdout, non-zero exit, FileNotFoundError, TimeoutExpired,
    JSONDecodeError, generic Exception, optional CLI args.
  - get_observation: happy path, non-dict JSON returns None, error paths.
  - save_observation: happy path, CLI arg construction, optional flags, error
    paths.
  - ENGRAM_BIN environment variable override is honored at import time.
  - --json flag is always present (semantic contract).
"""

from __future__ import annotations

import importlib
import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from lib import engram_client

pytestmark = pytest.mark.unit


def _mock_proc(stdout: str = "", returncode: int = 0, stderr: str = "") -> MagicMock:
    proc = MagicMock()
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


# ---------------------------------------------------------------------------
# search_observations
# ---------------------------------------------------------------------------


class TestSearchObservationsHappyPath:
    def test_returns_list_from_json_array(self):
        payload = [{"id": 1, "title": "a"}, {"id": 2, "title": "b"}]
        with patch("subprocess.run", return_value=_mock_proc(json.dumps(payload))):
            result = engram_client.search_observations("query")
        assert result == payload

    def test_returns_results_field_from_dict(self):
        payload = {"results": [{"id": 7, "title": "wrap"}]}
        with patch("subprocess.run", return_value=_mock_proc(json.dumps(payload))):
            result = engram_client.search_observations("query")
        assert result == [{"id": 7, "title": "wrap"}]

    def test_dict_without_results_returns_empty_list(self):
        with patch("subprocess.run", return_value=_mock_proc(json.dumps({"foo": 1}))):
            result = engram_client.search_observations("query")
        assert result == []

    def test_limit_slices_results(self):
        payload = [{"id": i} for i in range(10)]
        with patch("subprocess.run", return_value=_mock_proc(json.dumps(payload))):
            result = engram_client.search_observations("q", limit=3)
        assert result == payload[:3]

    def test_limit_slices_dict_results(self):
        payload = {"results": [{"id": i} for i in range(10)]}
        with patch("subprocess.run", return_value=_mock_proc(json.dumps(payload))):
            result = engram_client.search_observations("q", limit=2)
        assert result == payload["results"][:2]


class TestSearchObservationsCli:
    def test_default_cli_args(self):
        with patch("subprocess.run", return_value=_mock_proc("[]")) as run:
            engram_client.search_observations("hello world")
        cmd = run.call_args[0][0]
        # Order matters: binary, "search", "--json", "--limit", "<n>", query
        assert cmd[0] == engram_client._ENGRAM_BIN
        assert cmd[1] == "search"
        assert "--json" in cmd
        assert "--limit" in cmd
        assert "5" in cmd  # default limit
        assert "hello world" in cmd
        # Optional filters absent by default
        assert "--type" not in cmd
        assert "--project" not in cmd

    def test_type_filter_appended(self):
        with patch("subprocess.run", return_value=_mock_proc("[]")) as run:
            engram_client.search_observations("q", type_filter="discovery")
        cmd = run.call_args[0][0]
        assert "--type" in cmd
        assert "discovery" in cmd

    def test_project_filter_appended(self):
        with patch("subprocess.run", return_value=_mock_proc("[]")) as run:
            engram_client.search_observations("q", project="my-proj")
        cmd = run.call_args[0][0]
        assert "--project" in cmd
        assert "my-proj" in cmd

    def test_empty_optional_filters_omitted(self):
        with patch("subprocess.run", return_value=_mock_proc("[]")) as run:
            engram_client.search_observations("q", type_filter="", project="")
        cmd = run.call_args[0][0]
        assert "--type" not in cmd
        assert "--project" not in cmd

    def test_timeout_forwarded_to_subprocess(self):
        with patch("subprocess.run", return_value=_mock_proc("[]")) as run:
            engram_client.search_observations("q", timeout=42)
        assert run.call_args.kwargs["timeout"] == 42

    def test_subprocess_called_with_capture_and_text(self):
        with patch("subprocess.run", return_value=_mock_proc("[]")) as run:
            engram_client.search_observations("q")
        kwargs = run.call_args.kwargs
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True


class TestSearchObservationsErrorPaths:
    def test_file_not_found_returns_empty_list(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            assert engram_client.search_observations("q") == []

    def test_timeout_returns_empty_list(self):
        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="engram", timeout=5),
        ):
            assert engram_client.search_observations("q") == []

    def test_non_zero_exit_returns_empty_list(self):
        with patch("subprocess.run", return_value=_mock_proc("garbage", returncode=1)):
            assert engram_client.search_observations("q") == []

    def test_invalid_json_returns_empty_list(self):
        with patch("subprocess.run", return_value=_mock_proc("not json {")):
            assert engram_client.search_observations("q") == []

    def test_empty_stdout_returns_empty_list(self):
        with patch("subprocess.run", return_value=_mock_proc("   \n")):
            assert engram_client.search_observations("q") == []

    def test_generic_exception_returns_empty_list(self):
        # Locks in the bare `except Exception` catch-all behavior.
        with patch("subprocess.run", side_effect=RuntimeError("boom")):
            assert engram_client.search_observations("q") == []


# ---------------------------------------------------------------------------
# get_observation
# ---------------------------------------------------------------------------


class TestGetObservation:
    def test_happy_path_returns_dict(self):
        payload = {"id": 42, "title": "found"}
        with patch("subprocess.run", return_value=_mock_proc(json.dumps(payload))):
            assert engram_client.get_observation(42) == payload

    def test_cli_args_include_json_and_id(self):
        with patch("subprocess.run", return_value=_mock_proc("{}")) as run:
            engram_client.get_observation(123)
        cmd = run.call_args[0][0]
        assert cmd[0] == engram_client._ENGRAM_BIN
        assert cmd[1] == "get"
        assert "--json" in cmd
        # ID coerced to string
        assert "123" in cmd

    def test_string_id_passed_through(self):
        with patch("subprocess.run", return_value=_mock_proc("{}")) as run:
            engram_client.get_observation("abc-id")
        cmd = run.call_args[0][0]
        assert "abc-id" in cmd

    def test_non_dict_json_returns_none(self):
        with patch("subprocess.run", return_value=_mock_proc("[1, 2, 3]")):
            assert engram_client.get_observation(1) is None

    def test_empty_stdout_returns_none(self):
        with patch("subprocess.run", return_value=_mock_proc("")):
            assert engram_client.get_observation(1) is None

    def test_non_zero_exit_returns_none(self):
        with patch("subprocess.run", return_value=_mock_proc("anything", returncode=2)):
            assert engram_client.get_observation(1) is None

    def test_file_not_found_returns_none(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            assert engram_client.get_observation(1) is None

    def test_timeout_returns_none(self):
        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="engram", timeout=5),
        ):
            assert engram_client.get_observation(1) is None

    def test_invalid_json_returns_none(self):
        with patch("subprocess.run", return_value=_mock_proc("{not json")):
            assert engram_client.get_observation(1) is None

    def test_generic_exception_returns_none(self):
        with patch("subprocess.run", side_effect=RuntimeError("boom")):
            assert engram_client.get_observation(1) is None


# ---------------------------------------------------------------------------
# save_observation
# ---------------------------------------------------------------------------


class TestSaveObservation:
    def test_happy_path_returns_dict(self):
        payload = {"id": 99, "title": "saved"}
        with patch("subprocess.run", return_value=_mock_proc(json.dumps(payload))):
            assert engram_client.save_observation("t", "c") == payload

    def test_default_cli_args(self):
        with patch("subprocess.run", return_value=_mock_proc("{}")) as run:
            engram_client.save_observation("My Title", "Body content")
        cmd = run.call_args[0][0]
        assert cmd[0] == engram_client._ENGRAM_BIN
        assert cmd[1] == "save"
        assert "--json" in cmd
        assert "--title" in cmd
        assert "My Title" in cmd
        assert "--content" in cmd
        assert "Body content" in cmd
        assert "--type" in cmd
        assert "manual" in cmd  # default type_
        # Optional flags omitted by default
        assert "--topic-key" not in cmd
        assert "--project" not in cmd

    def test_optional_topic_key_appended(self):
        with patch("subprocess.run", return_value=_mock_proc("{}")) as run:
            engram_client.save_observation("t", "c", topic_key="arch/x")
        cmd = run.call_args[0][0]
        assert "--topic-key" in cmd
        assert "arch/x" in cmd

    def test_optional_project_appended(self):
        with patch("subprocess.run", return_value=_mock_proc("{}")) as run:
            engram_client.save_observation("t", "c", project="proj")
        cmd = run.call_args[0][0]
        assert "--project" in cmd
        assert "proj" in cmd

    def test_custom_type_forwarded(self):
        with patch("subprocess.run", return_value=_mock_proc("{}")) as run:
            engram_client.save_observation("t", "c", type_="decision")
        cmd = run.call_args[0][0]
        assert "decision" in cmd
        assert "manual" not in cmd

    def test_default_timeout_is_ten(self):
        with patch("subprocess.run", return_value=_mock_proc("{}")) as run:
            engram_client.save_observation("t", "c")
        assert run.call_args.kwargs["timeout"] == 10

    def test_custom_timeout_forwarded(self):
        with patch("subprocess.run", return_value=_mock_proc("{}")) as run:
            engram_client.save_observation("t", "c", timeout=30)
        assert run.call_args.kwargs["timeout"] == 30

    def test_non_dict_json_returns_none(self):
        with patch("subprocess.run", return_value=_mock_proc('"just a string"')):
            assert engram_client.save_observation("t", "c") is None

    def test_empty_stdout_returns_none(self):
        with patch("subprocess.run", return_value=_mock_proc("")):
            assert engram_client.save_observation("t", "c") is None

    def test_non_zero_exit_returns_none(self):
        with patch("subprocess.run", return_value=_mock_proc("ok", returncode=1)):
            assert engram_client.save_observation("t", "c") is None

    def test_file_not_found_returns_none(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            assert engram_client.save_observation("t", "c") is None

    def test_timeout_returns_none(self):
        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="engram", timeout=10),
        ):
            assert engram_client.save_observation("t", "c") is None

    def test_invalid_json_returns_none(self):
        with patch("subprocess.run", return_value=_mock_proc("not json")):
            assert engram_client.save_observation("t", "c") is None

    def test_generic_exception_returns_none(self):
        # Locks in the bare `except Exception` catch-all behavior at line 168.
        with patch("subprocess.run", side_effect=RuntimeError("boom")):
            assert engram_client.save_observation("t", "c") is None

    def test_topic_key_save_updates_existing_observation_instead_of_appending(self):
        existing = {"id": 42, "topic_key": "architecture/x", "project": "proj"}
        with patch("lib.engram_client.search_observations", return_value=[existing]) as search, \
             patch("lib.engram_client.engram_http_client.update_observation", return_value={"id": 42, "updated": True}) as update, \
             patch("subprocess.run") as run:
            result = engram_client.save_observation(
                "New title",
                "New body",
                type_="decision",
                topic_key="architecture/x",
                project="proj",
            )

        assert result == {"id": 42, "updated": True}
        search.assert_called_once()
        update.assert_called_once_with(
            42,
            title="New title",
            content="New body",
            type_="decision",
            topic_key="architecture/x",
            timeout=10,
        )
        run.assert_not_called()

    def test_topic_key_save_returns_none_when_existing_match_cannot_update(self):
        existing = {"id": 42, "topic_key": "architecture/x", "project": "proj"}
        with patch("lib.engram_client.search_observations", return_value=[existing]), \
             patch("lib.engram_client.engram_http_client.update_observation", return_value=None), \
             patch("subprocess.run") as run:
            result = engram_client.save_observation("t", "c", topic_key="architecture/x", project="proj")

        assert result is None
        run.assert_not_called()

    def test_topic_key_save_requires_exact_project_match_before_update(self):
        existing = {"id": 42, "topic_key": "architecture/x", "project": "other"}
        payload = {"id": 99, "topic_key": "architecture/x", "project": "proj"}
        with patch("lib.engram_client.search_observations", return_value=[existing]), \
             patch("lib.engram_client.engram_http_client.update_observation") as update, \
             patch("subprocess.run", return_value=_mock_proc(json.dumps(payload))) as run:
            result = engram_client.save_observation("t", "c", topic_key="architecture/x", project="proj")

        assert result == payload
        update.assert_not_called()
        assert run.called


# ---------------------------------------------------------------------------
# ENGRAM_BIN env-var override
# ---------------------------------------------------------------------------


class TestEngramBinOverride:
    def test_env_var_honored_at_import(self, monkeypatch):
        # _ENGRAM_BIN is captured at module import time. Reloading the module
        # with the env var set is the only way to observe the override.
        monkeypatch.setenv("ENGRAM_BIN", "/custom/path/to/engram")
        reloaded = importlib.reload(engram_client)
        try:
            assert reloaded._ENGRAM_BIN == "/custom/path/to/engram"
            with patch("subprocess.run", return_value=_mock_proc("[]")) as run:
                reloaded.search_observations("q")
            assert run.call_args[0][0][0] == "/custom/path/to/engram"
        finally:
            # Restore default state for any subsequent test runs.
            monkeypatch.delenv("ENGRAM_BIN", raising=False)
            importlib.reload(engram_client)

    def test_default_binary_is_engram(self, monkeypatch):
        monkeypatch.delenv("ENGRAM_BIN", raising=False)
        reloaded = importlib.reload(engram_client)
        try:
            assert reloaded._ENGRAM_BIN == "engram"
        finally:
            importlib.reload(engram_client)


# ---------------------------------------------------------------------------
# --json flag semantic contract (must survive any refactor)
# ---------------------------------------------------------------------------


class TestJsonFlagContract:
    def test_search_passes_json_flag(self):
        with patch("subprocess.run", return_value=_mock_proc("[]")) as run:
            engram_client.search_observations("q")
        assert "--json" in run.call_args[0][0]

    def test_get_passes_json_flag(self):
        with patch("subprocess.run", return_value=_mock_proc("{}")) as run:
            engram_client.get_observation(1)
        assert "--json" in run.call_args[0][0]

    def test_save_passes_json_flag(self):
        with patch("subprocess.run", return_value=_mock_proc("{}")) as run:
            engram_client.save_observation("t", "c")
        assert "--json" in run.call_args[0][0]
