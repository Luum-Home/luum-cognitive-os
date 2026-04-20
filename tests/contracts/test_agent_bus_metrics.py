"""Contract tests for lib.agent_bus_metrics.

Runnable without a live Valkey instance: every test exercises the
FallbackBus path. Behavioral only — no "file exists" checks.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from lib.agent_bus_metrics import AgentBusMetrics


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Isolated project root + metrics path + fallback dir."""
    monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    metrics = tmp_path / ".cognitive-os" / "metrics" / "agent-heartbeat.jsonl"
    fallback = tmp_path / ".cognitive-os" / "agent-bus"
    metrics.parent.mkdir(parents=True, exist_ok=True)
    fallback.mkdir(parents=True, exist_ok=True)
    return {
        "tmp": tmp_path,
        "metrics": metrics,
        "fallback": fallback,
        "adapter": AgentBusMetrics(
            metrics_path=str(metrics),
            fallback_dir=str(fallback),
            # Point Valkey at a dead port so subscribe() uses fallback
            valkey_url="redis://127.0.0.1:19999",
        ),
    }


def _read_events(path: Path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _write_fallback_heartbeat(fallback: Path, agent_id: str, ts_epoch: float, *, alive: bool = True, phase: str = ""):
    d = fallback / agent_id
    d.mkdir(parents=True, exist_ok=True)
    rec = {
        "type": "heartbeat",
        "agent_id": agent_id,
        "alive": alive,
        "phase": phase,
        "tokens_used": 0,
        "timestamp_epoch": ts_epoch,
    }
    (d / "heartbeat.jsonl").open("a", encoding="utf-8").write(json.dumps(rec) + "\n")


# ---------------------------------------------------------------------------
# Event emission
# ---------------------------------------------------------------------------


def test_first_heartbeat_emits_launched_event(env):
    a = env["adapter"]
    a.on_heartbeat_event({"agent_id": "a1", "alive": True, "phase": "apply", "tokens_used": 123})
    events = _read_events(env["metrics"])
    assert len(events) == 1
    e = events[0]
    assert e["source"] == "agent_bus_metrics"
    assert e["event_type"] == "agent_launched"
    assert e["payload"]["agent_id"] == "a1"
    assert e["payload"]["phase"] == "apply"
    assert e["payload"]["tokens_used"] == 123
    assert e["payload"]["alive"] is True


def test_intermediate_alive_beats_are_silent(env):
    a = env["adapter"]
    a.on_heartbeat_event({"agent_id": "a2", "alive": True, "phase": "p"})
    a.on_heartbeat_event({"agent_id": "a2", "alive": True, "phase": "p"})
    a.on_heartbeat_event({"agent_id": "a2", "alive": True, "phase": "p"})
    events = _read_events(env["metrics"])
    # Only the first beat yields agent_launched; the rest are waste-free.
    assert len(events) == 1
    assert events[0]["event_type"] == "agent_launched"


def test_alive_false_emits_completed_event(env):
    a = env["adapter"]
    a.on_heartbeat_event({"agent_id": "a3", "alive": True})
    a.on_heartbeat_event({"agent_id": "a3", "alive": False})
    events = _read_events(env["metrics"])
    assert [e["event_type"] for e in events] == ["agent_launched", "agent_completed"]
    assert events[-1]["payload"]["alive"] is False


def test_empty_agent_id_is_ignored(env):
    a = env["adapter"]
    a.on_heartbeat_event({"agent_id": "", "alive": True})
    a.on_heartbeat_event({"alive": True})  # no agent_id at all
    a.on_heartbeat_event("not-a-dict")  # type: ignore[arg-type]
    # Nothing should be emitted for malformed inputs.
    assert not env["metrics"].exists() or env["metrics"].read_text() == ""


# ---------------------------------------------------------------------------
# scan_stale / list_live
# ---------------------------------------------------------------------------


def test_scan_stale_honors_threshold(env):
    now = time.time()
    _write_fallback_heartbeat(env["fallback"], "old-agent", now - 400, phase="apply")
    _write_fallback_heartbeat(env["fallback"], "fresh-agent", now - 10, phase="verify")
    a = env["adapter"]
    stale = a.scan_stale(max_age_seconds=300)
    live = a.list_live(max_age_seconds=300)
    stale_ids = {r["agent_id"] for r in stale}
    live_ids = {r["agent_id"] for r in live}
    assert "old-agent" in stale_ids and "fresh-agent" not in stale_ids
    assert "fresh-agent" in live_ids and "old-agent" not in live_ids
    # Stale records include age
    assert any(r["age_seconds"] > 300 for r in stale)


def test_scan_stale_no_agents_returns_empty(env):
    a = env["adapter"]
    assert a.scan_stale() == []
    assert a.list_live() == []


def test_scan_stale_handles_malformed_heartbeat_file(env):
    # Write garbage + a valid line; last valid line should be used.
    d = env["fallback"] / "mixed-agent"
    d.mkdir()
    (d / "heartbeat.jsonl").write_text(
        "not json\n" + json.dumps({"agent_id": "mixed-agent", "timestamp_epoch": time.time(), "phase": "x"}) + "\n"
    )
    a = env["adapter"]
    live = a.list_live()
    assert any(r["agent_id"] == "mixed-agent" for r in live)


# ---------------------------------------------------------------------------
# mark_hung_and_publish
# ---------------------------------------------------------------------------


def test_mark_hung_emits_event_and_writes_fallback_control(env):
    now = time.time()
    _write_fallback_heartbeat(env["fallback"], "hung-agent", now - 600, phase="apply")
    a = env["adapter"]
    result = a.mark_hung_and_publish("hung-agent")
    assert result["agent_id"] == "hung-agent"
    assert result["stop_sent_via"] == "fallback"
    assert result["age_seconds"] is not None and result["age_seconds"] > 500

    events = _read_events(env["metrics"])
    assert any(e["event_type"] == "agent_hung" and e["payload"]["agent_id"] == "hung-agent" for e in events)

    ctrl = env["fallback"] / "hung-agent" / "control.jsonl"
    payloads = [json.loads(ln) for ln in ctrl.read_text().splitlines() if ln.strip()]
    assert any(p.get("command") == "stop" and p.get("agent_id") == "hung-agent" for p in payloads)


def test_mark_hung_rejects_empty_agent_id(env):
    a = env["adapter"]
    with pytest.raises(ValueError):
        a.mark_hung_and_publish("")


def test_mark_hung_works_without_prior_heartbeat(env):
    a = env["adapter"]
    # No heartbeat exists; mark_hung should still emit + write control.
    result = a.mark_hung_and_publish("never-seen")
    assert result["stop_sent_via"] == "fallback"
    assert result["age_seconds"] is None
    events = _read_events(env["metrics"])
    assert any(e["event_type"] == "agent_hung" for e in events)


# ---------------------------------------------------------------------------
# Fallback/resilience
# ---------------------------------------------------------------------------


def test_fallback_path_when_valkey_unreachable(env):
    """Constructing with a dead valkey URL must not raise; list_live reads files."""
    a = AgentBusMetrics(
        metrics_path=str(env["metrics"]),
        fallback_dir=str(env["fallback"]),
        valkey_url="redis://127.0.0.1:19998",
    )
    _write_fallback_heartbeat(env["fallback"], "file-only", time.time(), phase="apply")
    live = a.list_live()
    assert any(r["agent_id"] == "file-only" for r in live)


def test_relaunched_agent_id_emits_launched_again_after_completion(env):
    a = env["adapter"]
    a.on_heartbeat_event({"agent_id": "a4", "alive": True})
    a.on_heartbeat_event({"agent_id": "a4", "alive": False})
    a.on_heartbeat_event({"agent_id": "a4", "alive": True})
    events = _read_events(env["metrics"])
    assert [e["event_type"] for e in events] == ["agent_launched", "agent_completed", "agent_launched"]
