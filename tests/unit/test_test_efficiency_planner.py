from __future__ import annotations

import pytest

from lib.test_efficiency_planner import extract_failed_nodeids, plan_tests


@pytest.mark.unit
def test_runtime_change_selects_targeted_before_laptop(project_root) -> None:
    plan = plan_tests(project_root, changed_files=["lib/dispatch.py"], include_final_laptop=True)
    names = [lane.name for lane in plan.lanes]
    assert names[:2] == ["syntax", "unit"]
    assert "integration" in names
    assert plan.final_lane is not None
    assert plan.final_lane.name == "laptop"
    assert names[0] != "laptop"


@pytest.mark.unit
def test_docs_manifest_change_selects_audit_only(project_root) -> None:
    plan = plan_tests(project_root, changed_files=["docs/adrs/ADR-237-test-execution-efficiency-protocol.md"])
    assert [lane.name for lane in plan.lanes] == ["audit"]


@pytest.mark.unit
def test_failure_text_extracts_nodeids() -> None:
    text = "FAILED tests/unit/test_example.py::test_a - AssertionError\nFAILED tests/chaos/test_x.py::test_b - boom"
    assert extract_failed_nodeids(text) == ["tests/chaos/test_x.py::test_b", "tests/unit/test_example.py::test_a"]


@pytest.mark.unit
def test_failure_text_prefers_failed_nodeids_before_broad(project_root) -> None:
    plan = plan_tests(project_root, failure_text="FAILED tests/chaos/test_x.py::test_b - boom", include_final_laptop=True)
    assert plan.lanes[0].name == "failed-nodeids"
    assert "make test-laptop" in plan.final_lane.command
