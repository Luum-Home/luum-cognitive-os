"""Behavior tests for SDD sprint planning logic.

Tests task sizing, sprint capacity planning, team assignment balancing,
and utilization calculations used by sdd-tasks.

Related skill: sdd-tasks
"""

import pytest

pytestmark = pytest.mark.behavior


# ---------------------------------------------------------------------------
# Size keywords for estimation heuristics
# ---------------------------------------------------------------------------

_SIZE_MAP: dict[str, tuple[str, int]] = {
    "S": ("S", 2),
    "M": ("M", 4),
    "L": ("L", 8),
    "XL": ("XL", 16),
}

_LARGE_INDICATORS = [
    "refactor",
    "multi-file",
    "cross-cutting",
    "migration",
    "rewrite",
    "overhaul",
]

_SMALL_INDICATORS = [
    "single file",
    "rename",
    "typo",
    "config",
    "update constant",
    "add field",
]


# ---------------------------------------------------------------------------
# Sprint planning functions
# ---------------------------------------------------------------------------


def estimate_task_size(description: str) -> tuple[str, int]:
    """Estimate task size from its description.

    Returns (size_label, hours).
    Heuristic: check for indicator keywords, default to M.
    """
    lower = description.lower()

    for indicator in _LARGE_INDICATORS:
        if indicator in lower:
            # Check for XL signals
            if any(
                w in lower
                for w in ("rewrite", "overhaul", "migration", "full rewrite")
            ):
                return "XL", 16
            return "L", 8

    for indicator in _SMALL_INDICATORS:
        if indicator in lower:
            return "S", 2

    return "M", 4


def plan_sprints(
    tasks: list[dict],
    team_size: int = 1,
    hours_per_day: int = 6,
    sprint_days: int = 5,
) -> dict:
    """Plan sprints from a list of tasks.

    Each task dict has: name, hours, depends_on (optional list of task names).

    Returns:
        {
            "sprints": [
                {
                    "id": 1,
                    "tasks": [...],
                    "hours_used": int,
                    "capacity": int,
                    "utilization": float,
                    "risk_flags": [str],
                    "assignments": {member: hours},
                }
            ],
            "error": str | None,
        }
    """
    if not tasks:
        return {"sprints": [], "error": "No tasks provided"}

    capacity = team_size * hours_per_day * sprint_days
    sprints: list[dict] = []
    scheduled: set[str] = set()
    remaining = list(tasks)

    while remaining:
        sprint_tasks: list[dict] = []
        sprint_hours = 0
        still_remaining: list[dict] = []

        for task in remaining:
            deps = task.get("depends_on", [])
            deps_met = all(d in scheduled for d in deps)

            if deps_met and sprint_hours + task["hours"] <= capacity:
                sprint_tasks.append(task)
                sprint_hours += task["hours"]
                scheduled.add(task["name"])
            else:
                still_remaining.append(task)

        if not sprint_tasks:
            # Deadlock or tasks too large — force schedule one
            forced = still_remaining.pop(0)
            sprint_tasks.append(forced)
            sprint_hours = forced["hours"]
            scheduled.add(forced["name"])

        # Assign tasks to team members (round-robin for balance)
        assignments: dict[str, int] = {
            f"dev-{i+1}": 0 for i in range(team_size)
        }
        for task in sprint_tasks:
            # Assign to least-loaded member
            member = min(assignments, key=assignments.get)  # type: ignore[arg-type]
            assignments[member] += task["hours"]
            task["assigned_to"] = member

        utilization = (sprint_hours / capacity) * 100 if capacity > 0 else 0

        risk_flags: list[str] = []
        if utilization > 90:
            risk_flags.append("high-utilization")

        for task in sprint_tasks:
            if task["hours"] >= 16:
                risk_flags.append(f"xl-task:{task['name']}")

        sprints.append(
            {
                "id": len(sprints) + 1,
                "tasks": sprint_tasks,
                "hours_used": sprint_hours,
                "capacity": capacity,
                "utilization": round(utilization, 1),
                "risk_flags": risk_flags,
                "assignments": assignments,
            }
        )

        remaining = still_remaining

    return {"sprints": sprints, "error": None}


# ---------------------------------------------------------------------------
# Tests: Task sizing
# ---------------------------------------------------------------------------


class TestTaskSizing:
    """Tests for the estimate_task_size function."""

    def test_task_sizing_small(self):
        """Single file task is sized as S (2h)."""
        label, hours = estimate_task_size("Update single file config value")
        assert label == "S"
        assert hours == 2

    def test_task_sizing_large(self):
        """Multi-file refactor is sized as L (8h)."""
        label, hours = estimate_task_size(
            "Refactor authentication across multi-file modules"
        )
        assert label == "L"
        assert hours == 8

    def test_xl_task_flagged(self):
        """XL tasks (full rewrite) are identified and flagged."""
        label, hours = estimate_task_size("Full rewrite of the API layer")
        assert label == "XL"
        assert hours == 16

    def test_default_medium(self):
        """Tasks without clear indicators default to M (4h)."""
        label, hours = estimate_task_size("Implement user profile endpoint")
        assert label == "M"
        assert hours == 4

    @pytest.mark.parametrize(
        "description,expected_label",
        [
            ("Rename the helper function", "S"),
            ("Fix typo in error message", "S"),
            ("Cross-cutting concern: logging", "L"),
            ("Database migration to new schema", "XL"),
            ("Add new API endpoint", "M"),
        ],
    )
    def test_sizing_parametrized(self, description: str, expected_label: str):
        """Various descriptions produce expected size labels."""
        label, _ = estimate_task_size(description)
        assert label == expected_label


# ---------------------------------------------------------------------------
# Tests: Sprint capacity
# ---------------------------------------------------------------------------


class TestSprintCapacity:
    """Tests for sprint planning capacity calculations."""

    def test_solo_developer_defaults(self):
        """1 dev, 6h/day, 5 days = 30h capacity."""
        tasks = [{"name": "task-1", "hours": 4}]
        result = plan_sprints(tasks, team_size=1, hours_per_day=6, sprint_days=5)

        assert result["error"] is None
        assert result["sprints"][0]["capacity"] == 30

    def test_capacity_never_exceeded(self):
        """No sprint exceeds team capacity."""
        tasks = [
            {"name": f"task-{i}", "hours": 4}
            for i in range(10)
        ]
        result = plan_sprints(tasks, team_size=2, hours_per_day=6, sprint_days=5)

        for sprint in result["sprints"]:
            assert sprint["hours_used"] <= sprint["capacity"]

    def test_empty_tasks_returns_error(self):
        """No tasks produces an error message."""
        result = plan_sprints([])
        assert result["error"] == "No tasks provided"
        assert result["sprints"] == []


# ---------------------------------------------------------------------------
# Tests: Dependency ordering
# ---------------------------------------------------------------------------


class TestDependencyOrdering:

    def test_dependency_ordering(self):
        """Tasks with dependencies are scheduled in later sprints."""
        tasks = [
            {"name": "setup-db", "hours": 25},
            {"name": "build-api", "hours": 25, "depends_on": ["setup-db"]},
        ]
        result = plan_sprints(tasks, team_size=1, hours_per_day=6, sprint_days=5)

        assert len(result["sprints"]) >= 2

        sprint_1_names = {t["name"] for t in result["sprints"][0]["tasks"]}
        sprint_2_names = {t["name"] for t in result["sprints"][1]["tasks"]}

        assert "setup-db" in sprint_1_names
        assert "build-api" in sprint_2_names


# ---------------------------------------------------------------------------
# Tests: Team assignment and utilization
# ---------------------------------------------------------------------------


class TestTeamAssignment:

    def test_team_assignment_balanced(self):
        """Load is balanced within +/-20% across team members."""
        tasks = [
            {"name": f"task-{i}", "hours": 4}
            for i in range(6)
        ]
        result = plan_sprints(tasks, team_size=3, hours_per_day=6, sprint_days=5)

        for sprint in result["sprints"]:
            hours_list = list(sprint["assignments"].values())
            if not hours_list or max(hours_list) == 0:
                continue
            avg = sum(hours_list) / len(hours_list)
            for h in hours_list:
                if avg > 0:
                    assert abs(h - avg) / avg <= 0.20 or h == 0


class TestUtilization:

    def test_utilization_calculation(self):
        """Utilization = hours_used / capacity * 100."""
        tasks = [{"name": "task-1", "hours": 15}]
        result = plan_sprints(tasks, team_size=1, hours_per_day=6, sprint_days=5)

        sprint = result["sprints"][0]
        expected = (15 / 30) * 100
        assert sprint["utilization"] == expected

    def test_high_utilization_flagged(self):
        """>90% utilization produces a risk flag."""
        tasks = [{"name": "task-1", "hours": 28}]
        result = plan_sprints(tasks, team_size=1, hours_per_day=6, sprint_days=5)

        sprint = result["sprints"][0]
        assert "high-utilization" in sprint["risk_flags"]

    def test_normal_utilization_no_flag(self):
        """<=90% utilization has no high-utilization flag."""
        tasks = [{"name": "task-1", "hours": 20}]
        result = plan_sprints(tasks, team_size=1, hours_per_day=6, sprint_days=5)

        sprint = result["sprints"][0]
        assert "high-utilization" not in sprint["risk_flags"]
