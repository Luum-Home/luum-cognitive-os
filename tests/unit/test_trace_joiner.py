import json

from lib.trace_joiner import build_run_trace, normalize_event, stable_event_id


def test_stable_event_id_is_deterministic():
    row = {"timestamp": "2026-05-06T00:00:00Z", "session_id": "s1", "action": "start"}

    assert stable_event_id("hook-timing", 1, row) == stable_event_id("hook-timing", 1, row)
    assert stable_event_id("hook-timing", 1, row) != stable_event_id("hook-timing", 2, row)


def test_normalize_event_uses_existing_event_id_and_session_as_run_fallback():
    event = normalize_event(
        "agent-trajectory",
        4,
        {"event_id": "evt-explicit", "session_id": "fixture-session", "timestamp": "2026-05-06T00:00:00Z"},
        requested_session_id="fixture-session",
    )

    assert event["event_id"] == "evt-explicit"
    assert event["run_id"] == "fixture-session"
    assert event["session_id"] == "fixture-session"


def test_build_run_trace_joins_streams_without_raw_private_payload(tmp_path):
    metrics = tmp_path / ".cognitive-os" / "metrics"
    metrics.mkdir(parents=True)
    (metrics / "hook-timing.jsonl").write_text(
        '{"timestamp":"2026-05-06T00:00:00Z","session_id":"fixture-session","hook":"agent-prelaunch","duration_ms":12}\n',
        encoding="utf-8",
    )
    (metrics / "skill-feedback.jsonl").write_text(
        '{"timestamp":"2026-05-06T00:00:01Z","session_id":"fixture-session","skill":"docs-to-artifact","success":true}\n',
        encoding="utf-8",
    )
    (metrics / "private-content-access.jsonl").write_text(
        '{"timestamp":"2026-05-06T00:00:02Z","session_id":"fixture-session","path":".cognitive-os/strategy/x.md","content":"SECRET PRIVATE TEXT"}\n',
        encoding="utf-8",
    )

    payload = build_run_trace(tmp_path, session_id="fixture-session")

    assert payload["schema_version"] == "run-flight-recorder/v1"
    assert payload["run_id"] == "fixture-session"
    assert payload["event_count"] == 3
    assert payload["streams"] == {"hook-timing": 1, "private-content-access": 1, "skill-feedback": 1}
    assert "SECRET PRIVATE TEXT" not in json.dumps(payload)
    private_events = [event for event in payload["events"] if event["stream"] == "private-content-access"]
    assert private_events[0]["private_content_ref_only"] is True
    assert private_events[0]["data"]["content_ref"] == "redacted-by-adr-202"
    assert (tmp_path / ".cognitive-os" / "runs" / "fixture-session" / "trace.json").exists()
    assert (tmp_path / ".cognitive-os" / "metrics" / "run-trace.jsonl").exists()
    assert (tmp_path / ".cognitive-os" / "reports" / "run-trace-latest.json").exists()


def test_build_run_trace_includes_codebase_itinerary_as_ref_only_stream(tmp_path):
    metrics = tmp_path / ".cognitive-os" / "metrics"
    metrics.mkdir(parents=True)
    (metrics / "codebase-itinerary.jsonl").write_text(
        '{"timestamp":"2026-05-06T00:00:03Z","session_id":"fixture-session","tool":"Grep","action_kind":"search","target_ref":{"hash_sha256_12":"abc123"},"selector_ref":{"kind":"grep-pattern","hash_sha256_12":"def456"}}\n',
        encoding="utf-8",
    )

    payload = build_run_trace(tmp_path, session_id="fixture-session")

    assert payload["event_count"] == 1
    assert payload["streams"] == {"codebase-itinerary": 1}
    assert payload["privacy_policy"]["private_content_streams"] == [
        "private-content-access",
        "codebase-itinerary",
    ]
    event = payload["events"][0]
    assert event["stream"] == "codebase-itinerary"
    assert event["private_content_ref_only"] is True
