"""Tests for sdd-apply next-batch assessment step.

Validates that the next-batch logic correctly counts remaining tasks,
identifies the next logical batch respecting phases, and handles
the all-complete case.
"""

import pytest

pytestmark = pytest.mark.behavior


# ---------------------------------------------------------------------------
# Helpers — pure-Python simulators for next-batch assessment logic
# ---------------------------------------------------------------------------

def parse_tasks(tasks_md: str) -> list[dict]:
    """Parse a tasks markdown into a list of task dicts.

    Each dict has keys: id, description, completed, phase.
    """
    tasks = []
    current_phase = "default"
    for line in tasks_md.splitlines():
        stripped = line.strip()
        if stripped.startswith("## Phase"):
            current_phase = stripped.lstrip("# ").strip()
            continue
        if stripped.startswith("- [x]") or stripped.startswith("- [ ]"):
            completed = stripped.startswith("- [x]")
            desc = stripped[5:].strip()
            # extract task id (e.g., "1.1 Do something" -> "1.1")
            parts = desc.split(" ", 1)
            task_id = parts[0] if len(parts) > 1 else desc
            task_desc = parts[1] if len(parts) > 1 else desc
            tasks.append({
                "id": task_id,
                "description": task_desc,
                "completed": completed,
                "phase": current_phase,
            })
    return tasks


def count_remaining(tasks: list[dict]) -> int:
    """Count uncompleted tasks."""
    return sum(1 for t in tasks if not t["completed"])


def suggest_next_batch(tasks: list[dict]) -> dict:
    """Suggest the next batch of tasks to implement.

    Returns a dict with:
    - remaining: count of uncompleted tasks
    - suggested_next: description of the next batch or "All tasks complete"
    """
    remaining = count_remaining(tasks)

    if remaining == 0:
        return {
            "remaining": 0,
            "suggested_next": "All tasks complete \u2014 ready for verify",
        }

    # Group uncompleted tasks by phase
    phases_with_pending: dict[str, list[dict]] = {}
    for t in tasks:
        if not t["completed"]:
            phases_with_pending.setdefault(t["phase"], []).append(t)

    # Pick the first phase with pending tasks (preserves document order)
    first_phase = next(iter(phases_with_pending))
    batch_tasks = phases_with_pending[first_phase]
    task_ids = ", ".join(t["id"] for t in batch_tasks)

    return {
        "remaining": remaining,
        "suggested_next": f"{first_phase}, tasks {task_ids}",
    }


def format_next_batch_section(assessment: dict) -> str:
    """Format the ### Next Batch section for the return summary."""
    return (
        f"### Next Batch\n"
        f"- **Remaining tasks**: {assessment['remaining']}\n"
        f"- **Suggested next**: {assessment['suggested_next']}"
    )


# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

TASKS_PARTIAL = """\
## Phase 1: Foundation

- [x] 1.1 Create auth middleware
- [x] 1.2 Add config struct
- [ ] 1.3 Add auth routes

## Phase 2: Integration

- [ ] 2.1 Wire up middleware
- [ ] 2.2 Add integration tests
"""

TASKS_ALL_COMPLETE = """\
## Phase 1: Foundation

- [x] 1.1 Create auth middleware
- [x] 1.2 Add config struct
- [x] 1.3 Add auth routes
"""

TASKS_MULTI_PHASE = """\
## Phase 1: Foundation

- [x] 1.1 Create auth middleware
- [x] 1.2 Add config struct
- [x] 1.3 Add auth routes

## Phase 2: Integration

- [ ] 2.1 Wire up middleware
- [ ] 2.2 Add integration tests

## Phase 3: Polish

- [ ] 3.1 Add logging
- [ ] 3.2 Write docs
"""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRemainingTasksCounted:
    def test_remaining_tasks_counted(self):
        tasks = parse_tasks(TASKS_PARTIAL)
        remaining = count_remaining(tasks)
        assert remaining == 3

    def test_all_counted_when_none_complete(self):
        md = "## Phase 1: Setup\n\n- [ ] 1.1 Do A\n- [ ] 1.2 Do B\n"
        tasks = parse_tasks(md)
        assert count_remaining(tasks) == 2


class TestAllTasksComplete:
    def test_all_tasks_complete(self):
        tasks = parse_tasks(TASKS_ALL_COMPLETE)
        assessment = suggest_next_batch(tasks)

        assert assessment["remaining"] == 0
        assert "All tasks complete" in assessment["suggested_next"]
        assert "verify" in assessment["suggested_next"]

    def test_format_all_complete(self):
        tasks = parse_tasks(TASKS_ALL_COMPLETE)
        assessment = suggest_next_batch(tasks)
        section = format_next_batch_section(assessment)

        assert "Remaining tasks**: 0" in section
        assert "All tasks complete" in section


class TestNextBatchRespectsPhases:
    def test_next_batch_respects_phases(self):
        tasks = parse_tasks(TASKS_MULTI_PHASE)
        assessment = suggest_next_batch(tasks)

        assert assessment["remaining"] == 4
        assert "Phase 2" in assessment["suggested_next"]
        assert "2.1" in assessment["suggested_next"]
        assert "2.2" in assessment["suggested_next"]
        # Phase 3 tasks should NOT be in the suggested next batch
        assert "3.1" not in assessment["suggested_next"]

    def test_suggests_first_incomplete_phase(self):
        # All of phase 1 done, phase 2 partially done
        md = (
            "## Phase 1: A\n\n- [x] 1.1 Done\n\n"
            "## Phase 2: B\n\n- [x] 2.1 Done\n- [ ] 2.2 Pending\n\n"
            "## Phase 3: C\n\n- [ ] 3.1 Pending\n"
        )
        tasks = parse_tasks(md)
        assessment = suggest_next_batch(tasks)

        assert "Phase 2" in assessment["suggested_next"]
        assert "2.2" in assessment["suggested_next"]


class TestBackwardCompatible:
    def test_backward_compatible(self):
        """The return summary format includes Next Batch as an additive section
        that does not break the existing structure."""
        tasks = parse_tasks(TASKS_PARTIAL)
        assessment = suggest_next_batch(tasks)
        section = format_next_batch_section(assessment)

        # Section uses the expected heading
        assert section.startswith("### Next Batch")
        # Contains the two required fields
        assert "**Remaining tasks**:" in section
        assert "**Suggested next**:" in section

    def test_format_partial(self):
        tasks = parse_tasks(TASKS_PARTIAL)
        assessment = suggest_next_batch(tasks)
        section = format_next_batch_section(assessment)

        assert "Remaining tasks**: 3" in section
        assert "Phase 1" in section
