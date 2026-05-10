from __future__ import annotations

from lib.dspy_pilot import build_pilot_report, sdd_verify_signature


def test_dspy_pilot_declares_structured_io_without_router_touch() -> None:
    report = build_pilot_report()
    assert report.schema_version == "dspy-structured-skill-pilot/v1"
    assert report.target_skill == "sdd-verify"
    assert report.router_touched is False
    assert report.signature == sdd_verify_signature()
    assert set(report.signature["outputs"]) >= {"verdict", "next_action"}
