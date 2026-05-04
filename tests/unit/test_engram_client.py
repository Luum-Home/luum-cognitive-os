"""Characterization tests for lib.engram_client against the current Engram CLI.

Engram v1.15.x does not expose JSON flags for ``search``/``save``/``get``.
Structured reads go through ``lib.engram_http_client`` and saves use the
positional CLI shape: ``engram save <title> <content>``.
"""

from __future__ import annotations

import importlib
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


class TestSearchObservations:
    def test_delegates_to_http_client(self):
        payload = [{"id": 1}, {"id": 2}]
        with patch("lib.engram_client.engram_http_client.search_observations", return_value=payload) as search:
            result = engram_client.search_observations("query", limit=1, type_filter="decision", project="proj", timeout=9)

        assert result == payload[:1]
        search.assert_called_once_with("query", limit=1, type_filter="decision", project="proj", timeout=9)

    def test_http_error_returns_empty_list(self):
        with patch("lib.engram_client.engram_http_client.search_observations", side_effect=RuntimeError("boom")):
            assert engram_client.search_observations("q") == []


class TestGetObservation:
    def test_delegates_to_http_client(self):
        payload = {"id": 42, "title": "found"}
        with patch("lib.engram_client.engram_http_client.get_observation", return_value=payload) as get:
            assert engram_client.get_observation(42, timeout=7) == payload

        get.assert_called_once_with(42, timeout=7)

    def test_http_error_returns_none(self):
        with patch("lib.engram_client.engram_http_client.get_observation", side_effect=RuntimeError("boom")):
            assert engram_client.get_observation(1) is None


class TestSaveObservation:
    def test_positional_cli_args(self):
        with patch("subprocess.run", return_value=_mock_proc('Memory saved: #99 "My Title" (manual)')) as run:
            result = engram_client.save_observation("My Title", "Body content")

        cmd = run.call_args[0][0]
        assert cmd == [engram_client._ENGRAM_BIN, "save", "My Title", "Body content", "--type", "manual"]
        assert "--json" not in cmd
        assert "--title" not in cmd
        assert "--content" not in cmd
        assert result == {
            "id": 99,
            "title": "My Title",
            "content": "Body content",
            "type": "manual",
            "topic_key": "",
            "project": "",
        }

    def test_optional_topic_and_project_appended(self):
        with patch("subprocess.run", return_value=_mock_proc('Memory saved: #7 "t" (decision)')) as run:
            result = engram_client.save_observation("t", "c", type_="decision", topic_key="arch/x", project="proj")

        cmd = run.call_args[0][0]
        assert cmd == [engram_client._ENGRAM_BIN, "save", "t", "c", "--type", "decision", "--topic", "arch/x", "--project", "proj"]
        assert result is not None
        assert result["id"] == 7
        assert result["topic_key"] == "arch/x"
        assert result["project"] == "proj"

    def test_default_timeout_is_ten(self):
        with patch("subprocess.run", return_value=_mock_proc('Memory saved: #1 "t" (manual)')) as run:
            engram_client.save_observation("t", "c")
        assert run.call_args.kwargs["timeout"] == 10

    def test_custom_timeout_forwarded(self):
        with patch("subprocess.run", return_value=_mock_proc('Memory saved: #1 "t" (manual)')) as run:
            engram_client.save_observation("t", "c", timeout=30)
        assert run.call_args.kwargs["timeout"] == 30

    def test_non_zero_exit_returns_none(self):
        with patch("subprocess.run", return_value=_mock_proc("ok", returncode=1)):
            assert engram_client.save_observation("t", "c") is None

    def test_file_not_found_returns_none(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            assert engram_client.save_observation("t", "c") is None

    def test_timeout_returns_none(self):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="engram", timeout=10)):
            assert engram_client.save_observation("t", "c") is None

    def test_empty_stdout_returns_none(self):
        with patch("subprocess.run", return_value=_mock_proc("")):
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

    def test_topic_key_save_requires_exact_project_match_before_append(self):
        existing = {"id": 42, "topic_key": "architecture/x", "project": "other"}
        with patch("lib.engram_client.search_observations", return_value=[existing]), \
             patch("lib.engram_client.engram_http_client.update_observation") as update, \
             patch("subprocess.run", return_value=_mock_proc('Memory saved: #99 "t" (manual)')) as run:
            result = engram_client.save_observation("t", "c", topic_key="architecture/x", project="proj")

        assert result is not None
        assert result["id"] == 99
        update.assert_not_called()
        assert run.called


class TestEngramBinOverride:
    def test_env_var_honored_at_import_for_save(self, monkeypatch):
        monkeypatch.setenv("ENGRAM_BIN", "/custom/path/to/engram")
        reloaded = importlib.reload(engram_client)
        try:
            assert reloaded._ENGRAM_BIN == "/custom/path/to/engram"
            with patch("subprocess.run", return_value=_mock_proc('Memory saved: #1 "t" (manual)')) as run:
                reloaded.save_observation("t", "c")
            assert run.call_args[0][0][0] == "/custom/path/to/engram"
        finally:
            monkeypatch.delenv("ENGRAM_BIN", raising=False)
            importlib.reload(engram_client)

    def test_default_binary_is_engram(self, monkeypatch):
        monkeypatch.delenv("ENGRAM_BIN", raising=False)
        reloaded = importlib.reload(engram_client)
        try:
            assert reloaded._ENGRAM_BIN == "engram"
        finally:
            importlib.reload(engram_client)
