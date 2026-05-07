from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from lib.session_bus import append_session_event  # noqa: E402


@pytest.mark.audit
def test_event_sourced_bus_manifest_declares_slice_a_contract(project_root: Path) -> None:
    manifest = yaml.safe_load((project_root / "manifests" / "event-sourced-session-bus.yaml").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "event-sourced-session-bus/v1"
    assert manifest["extends"] == "ADR-205 Flight Recorder"
    assert manifest["performance"]["slice_a_baseline_required"] is True
    assert "fan_out_global_index" in manifest["slice_a"]["deferred"]


@pytest.mark.audit
def test_event_sourced_bus_writes_only_declared_paths(tmp_path: Path) -> None:
    before = {path.relative_to(tmp_path) for path in tmp_path.rglob("*")}
    append_session_event("session-start", {}, project_dir=tmp_path, session_id="s1")
    after = {path.relative_to(tmp_path) for path in tmp_path.rglob("*")}
    created = after - before

    assert created <= {
        Path(".cognitive-os"),
        Path(".cognitive-os/sessions"),
        Path(".cognitive-os/sessions/s1.events.jsonl"),
        Path(".cognitive-os/sessions/.seq-counters"),
        Path(".cognitive-os/sessions/.seq-counters/s1.lock"),
        Path(".cognitive-os/sessions/.seq-counters/s1.counter"),
    }
