from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

import lib.event_wrap as event_wrap_module  # noqa: E402
from lib.event_wrap import WrappedStepSignatureChanged, event_wrap  # noqa: E402
from lib.session_bus import read_session_events  # noqa: E402


def _reset_counters() -> None:
    event_wrap_module._CALL_COUNTERS.clear()
    event_wrap_module._REPLAY_COUNTERS.clear()


def test_event_wrap_records_json_result_and_replays_without_calling(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_counters()
    calls = {"count": 0}

    @event_wrap(project_dir=tmp_path, session_id="s1")
    def nondeterministic() -> dict[str, int]:
        calls["count"] += 1
        return {"value": 42}

    assert nondeterministic() == {"value": 42}
    assert calls["count"] == 1
    events = read_session_events("s1", project_dir=tmp_path, event_type="wrapped-step")
    assert len(events) == 1
    payload = events[0]["payload"]
    assert payload["call_index"] == 1
    assert payload["result"] == {"value": 42}
    assert "result_sha" in payload

    _reset_counters()
    monkeypatch.setenv("COS_REPLAY_FROM_SEQ", "0")
    assert nondeterministic() == {"value": 42}
    assert calls["count"] == 1


def test_event_wrap_refuses_replay_when_signature_changes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_counters()

    @event_wrap(project_dir=tmp_path, session_id="s1")
    def step(value: int) -> dict[str, int]:
        return {"value": value}

    assert step(1) == {"value": 1}

    _reset_counters()

    @event_wrap(project_dir=tmp_path, session_id="s1")
    def step(value: int, extra: int = 0) -> dict[str, int]:  # type: ignore[no-redef]
        return {"value": value + extra}

    monkeypatch.setenv("COS_REPLAY_FROM_SEQ", "0")
    with pytest.raises(WrappedStepSignatureChanged):
        step(1)


def test_event_wrap_rejects_non_json_result(tmp_path: Path) -> None:
    _reset_counters()

    @event_wrap(project_dir=tmp_path, session_id="s1")
    def bad() -> object:
        return object()

    with pytest.raises(Exception, match="JSON-serializable"):
        bad()
