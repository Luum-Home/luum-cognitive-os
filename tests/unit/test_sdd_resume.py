"""Unit tests for lib/sdd_resume.py

Validates SDDState dataclass creation and JSON serialization, phase dependency
validation, resume logic, save/load state roundtrip, list_changes parsing,
and state summary formatting.
"""
import json
import sys
from pathlib import Path

import pytest

_LIB_DIR = str(Path(__file__).resolve().parent.parent.parent / "lib")
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from sdd_resume import (
    PHASE_DEPENDENCIES,
    SDD_PHASES,
    SDDState,
    determine_next_phase,
    format_state_summary,
    get_state,
    list_changes,
    resume,
    save_state,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# SDDState dataclass
# ---------------------------------------------------------------------------


class TestSDDState:
    def test_default_creation(self):
        state = SDDState(change_name="add-auth")
        assert state.change_name == "add-auth"
        assert state.current_phase is None
        assert state.phases_completed == []
        assert state.retry_count == 0
        assert state.max_retries == 3
        assert state.timings == {}
        assert state.history == []

    def test_to_dict(self):
        state = SDDState(
            change_name="add-auth",
            phases_completed=["explore", "propose"],
            retry_count=1,
        )
        d = state.to_dict()
        assert d["change_name"] == "add-auth"
        assert d["phases_completed"] == ["explore", "propose"]
        assert d["retry_count"] == 1

    def test_to_json_roundtrip(self):
        state = SDDState(
            change_name="add-auth",
            phases_completed=["explore"],
            current_phase="propose",
            timings={"explore": 30.0},
        )
        json_str = state.to_json()
        restored = SDDState.from_json(json_str)
        assert restored.change_name == "add-auth"
        assert restored.phases_completed == ["explore"]
        assert restored.current_phase == "propose"
        assert restored.timings == {"explore": 30.0}

    def test_from_dict(self):
        data = {
            "change_name": "fix-bug",
            "phases_completed": ["explore"],
            "retry_count": 2,
            "max_retries": 5,
        }
        state = SDDState.from_dict(data)
        assert state.change_name == "fix-bug"
        assert state.phases_completed == ["explore"]
        assert state.retry_count == 2
        assert state.max_retries == 5

    def test_from_dict_missing_fields(self):
        state = SDDState.from_dict({"change_name": "x"})
        assert state.change_name == "x"
        assert state.phases_completed == []
        assert state.retry_count == 0


# ---------------------------------------------------------------------------
# Phase dependencies
# ---------------------------------------------------------------------------


class TestPhaseDependencies:
    def test_explore_no_deps(self):
        assert PHASE_DEPENDENCIES["explore"] == []

    def test_propose_no_deps(self):
        assert PHASE_DEPENDENCIES["propose"] == []

    def test_spec_depends_on_propose(self):
        assert "propose" in PHASE_DEPENDENCIES["spec"]

    def test_tasks_depends_on_spec_and_design(self):
        deps = PHASE_DEPENDENCIES["tasks"]
        assert "spec" in deps
        assert "design" in deps

    def test_archive_depends_on_verify(self):
        assert "verify" in PHASE_DEPENDENCIES["archive"]


# ---------------------------------------------------------------------------
# determine_next_phase
# ---------------------------------------------------------------------------


class TestDetermineNextPhase:
    def test_fresh_state_returns_explore(self):
        state = SDDState(change_name="x")
        phase, reason = determine_next_phase(state)
        assert phase == "explore"

    def test_after_explore_returns_propose(self):
        state = SDDState(change_name="x", phases_completed=["explore"])
        phase, reason = determine_next_phase(state)
        assert phase == "propose"

    def test_start_from_specific_phase(self):
        state = SDDState(change_name="x", phases_completed=["propose"])
        phase, reason = determine_next_phase(state, start_from="spec")
        assert phase == "spec"
        assert "Resuming from requested" in reason

    def test_start_from_unknown_phase(self):
        state = SDDState(change_name="x")
        phase, reason = determine_next_phase(state, start_from="deploy")
        assert phase is None
        assert "Unknown phase" in reason

    def test_start_from_missing_dependencies(self):
        state = SDDState(change_name="x", phases_completed=[])
        phase, reason = determine_next_phase(state, start_from="spec")
        assert phase is None
        assert "missing dependencies" in reason

    def test_resume_in_progress_phase(self):
        state = SDDState(
            change_name="x",
            current_phase="apply",
            phases_completed=["explore", "propose", "spec", "design", "tasks"],
            retry_count=1,
            max_retries=3,
        )
        phase, reason = determine_next_phase(state)
        assert phase == "apply"
        assert "Resuming in-progress" in reason

    def test_max_retries_exceeded(self):
        state = SDDState(
            change_name="x",
            current_phase="apply",
            retry_count=3,
            max_retries=3,
        )
        phase, reason = determine_next_phase(state)
        assert phase is None
        assert "exceeded" in reason
        assert "Human intervention" in reason

    def test_all_phases_complete(self):
        state = SDDState(change_name="x", phases_completed=list(SDD_PHASES))
        phase, reason = determine_next_phase(state)
        assert phase is None
        assert "Pipeline complete" in reason

    def test_tasks_needs_spec_and_design(self):
        # spec done but not design -> can't start tasks
        state = SDDState(
            change_name="x",
            phases_completed=["explore", "propose", "spec"],
        )
        phase, reason = determine_next_phase(state)
        # Should return design (since spec is done, propose is done, design deps are met)
        assert phase == "design"

    def test_tasks_available_when_both_deps_met(self):
        state = SDDState(
            change_name="x",
            phases_completed=["explore", "propose", "spec", "design"],
        )
        phase, reason = determine_next_phase(state)
        assert phase == "tasks"


# ---------------------------------------------------------------------------
# resume()
# ---------------------------------------------------------------------------


class TestResume:
    def test_fresh_resume(self):
        result = resume("add-auth")
        assert result["change_name"] == "add-auth"
        assert result["next_phase"] == "explore"
        assert "state" in result
        assert result["topic_key"] == "planning/add-auth/state"

    def test_resume_with_existing_state(self):
        state = SDDState(
            change_name="add-auth",
            phases_completed=["explore", "propose"],
        )
        result = resume("add-auth", state_json=state.to_json())
        assert result["next_phase"] == "spec"

    def test_resume_overrides_change_name(self):
        state = SDDState(change_name="old-name")
        result = resume("new-name", state_json=state.to_json())
        assert result["change_name"] == "new-name"


# ---------------------------------------------------------------------------
# save_state()
# ---------------------------------------------------------------------------


class TestSaveState:
    def test_save_completed_phase(self):
        result = save_state("add-auth", "explore", "completed", timing_secs=30.0)
        assert result["change_name"] == "add-auth"
        assert result["topic_key"] == "planning/add-auth/state"
        state = json.loads(result["state_json"])
        assert "explore" in state["phases_completed"]
        assert state["timings"]["explore"] == 30.0
        assert state["current_phase"] is None
        assert state["retry_count"] == 0

    def test_save_failed_phase(self):
        result = save_state("add-auth", "apply", "failed")
        state = json.loads(result["state_json"])
        assert state["current_phase"] == "apply"
        assert state["retry_count"] == 1
        assert "apply" not in state["phases_completed"]

    def test_save_with_existing_state(self):
        initial = SDDState(
            change_name="add-auth",
            phases_completed=["explore"],
            timings={"explore": 10.0},
        )
        result = save_state(
            "add-auth", "propose", "completed",
            timing_secs=20.0, state_json=initial.to_json(),
        )
        state = json.loads(result["state_json"])
        assert "explore" in state["phases_completed"]
        assert "propose" in state["phases_completed"]
        assert state["timings"]["propose"] == 20.0

    def test_save_roundtrip(self):
        r1 = save_state("add-auth", "explore", "completed", timing_secs=10.0)
        r2 = save_state(
            "add-auth", "propose", "completed",
            timing_secs=20.0, state_json=r1["state_json"],
        )
        state = json.loads(r2["state_json"])
        assert state["phases_completed"] == ["explore", "propose"]
        assert len(state["history"]) == 2

    def test_save_engram_title(self):
        result = save_state("add-auth", "apply", "failed")
        assert "SDD state: add-auth (apply failed)" == result["engram_title"]

    def test_completed_not_duplicated(self):
        initial = SDDState(
            change_name="x",
            phases_completed=["explore"],
        )
        result = save_state(
            "x", "explore", "completed",
            state_json=initial.to_json(),
        )
        state = json.loads(result["state_json"])
        assert state["phases_completed"].count("explore") == 1


# ---------------------------------------------------------------------------
# get_state()
# ---------------------------------------------------------------------------


class TestGetState:
    def test_no_state(self):
        result = get_state("add-auth")
        assert result["exists"] is False
        assert "No state found" in result["message"]

    def test_with_state(self):
        state = SDDState(
            change_name="add-auth",
            phases_completed=["explore", "propose"],
            timings={"explore": 10.0, "propose": 20.0},
        )
        result = get_state("add-auth", state_json=state.to_json())
        assert result["exists"] is True
        assert result["progress"] == "2/8 phases completed"
        assert len(result["phases_remaining"]) == 6
        assert result["total_time_secs"] == 30.0


# ---------------------------------------------------------------------------
# list_changes()
# ---------------------------------------------------------------------------


class TestListChanges:
    def test_empty_results(self):
        assert list_changes(None) == []
        assert list_changes([]) == []

    def test_parseable_state(self):
        state = SDDState(
            change_name="add-auth",
            phases_completed=["explore"],
            timings={"explore": 10.0},
        )
        results = [{"title": "SDD state: add-auth", "content": state.to_json()}]
        changes = list_changes(results)
        assert len(changes) == 1
        assert changes[0]["change_name"] == "add-auth"
        assert changes[0]["progress"] == "1/8"

    def test_unparseable_content(self):
        results = [{"title": "SDD state: fix-bug", "content": "not json"}]
        changes = list_changes(results)
        assert len(changes) == 1
        assert changes[0]["change_name"] == "fix-bug"
        assert "error" in changes[0]

    def test_code_block_wrapped_state(self):
        state = SDDState(change_name="add-auth", phases_completed=["explore"])
        wrapped = "```json\n%s\n```" % state.to_json()
        results = [{"title": "SDD state: add-auth", "content": wrapped}]
        changes = list_changes(results)
        assert len(changes) == 1
        assert changes[0]["change_name"] == "add-auth"


# ---------------------------------------------------------------------------
# format_state_summary()
# ---------------------------------------------------------------------------


class TestFormatStateSummary:
    def test_basic_summary(self):
        state_dict = {
            "change_name": "add-auth",
            "progress": "3/8 phases completed",
            "phases_completed": ["explore", "propose", "spec"],
            "phases_remaining": ["design", "tasks", "apply", "verify", "archive"],
            "timings": {"explore": 10.0, "propose": 20.0, "spec": 15.0},
            "total_time_secs": 45.0,
        }
        summary = format_state_summary(state_dict)
        assert "add-auth" in summary
        assert "3/8" in summary
        assert "explore, propose, spec" in summary
        assert "45.0s" in summary

    def test_with_current_phase(self):
        state_dict = {
            "change_name": "x",
            "current_phase": "apply",
            "retry_count": 2,
        }
        summary = format_state_summary(state_dict)
        assert "apply" in summary
        assert "retry 2" in summary

    def test_minimal_dict(self):
        summary = format_state_summary({"change_name": "x"})
        assert "x" in summary
