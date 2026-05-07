from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from lib.session_bus import append_session_event, read_session_events, recover_session_counter  # noqa: E402


@pytest.mark.behavior
def test_event_sourced_bus_record_recover_read_smoke(tmp_path: Path) -> None:
    session_id = "smoke-session"
    expected = []
    for idx in range(30):
        event = append_session_event("coordination-claim", {"idx": idx}, project_dir=tmp_path, session_id=session_id)
        expected.append((event["seq"], event["event_type"], event["payload"]))

    # Simulate a fresh process losing only the rebuildable counter cache.
    counter = tmp_path / ".cognitive-os" / "sessions" / ".seq-counters" / f"{session_id}.counter"
    counter.unlink()
    assert recover_session_counter(session_id, project_dir=tmp_path) == 30

    actual = [
        (event["seq"], event["event_type"], event["payload"])
        for event in read_session_events(session_id, project_dir=tmp_path)
    ]
    assert actual == expected
