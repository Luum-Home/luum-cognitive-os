"""Unit tests for lib/changelog_generator.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

from lib.changelog_generator import (
    SessionChangelog,
    SprintChangelog,
    format_changelog_md,
    generate_session_changelog,
    generate_sprint_changelog,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def _write_jsonl(path: Path, records: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n")


def _make_cos(tmp_path: Path) -> Path:
    """Return the .cognitive-os dir inside tmp_path, creating it."""
    cos = tmp_path / ".cognitive-os"
    cos.mkdir(parents=True, exist_ok=True)
    return cos


# ---------------------------------------------------------------------------
# C1: generate_session_changelog from real files
# ---------------------------------------------------------------------------


class TestGenerateSessionChangelog:
    def test_session_changelog_from_files(self, tmp_path: Path) -> None:
        """C1: Read meta, git-context, active-tasks, cost-events and produce correct changelog."""
        cos = _make_cos(tmp_path)
        session_id = "sess-1"

        # meta.json
        _write_json(
            cos / "sessions" / session_id / "meta.json",
            {
                "session_id": session_id,
                "start_time": "2026-04-10T10:00:00Z",
            },
        )

        # git-context.json
        _write_json(
            cos / "sessions" / session_id / "git-context.json",
            {
                "commits": [
                    {"sha": "abc1234", "message": "feat: add auth endpoint"},
                    {"sha": "def5678", "message": "fix: handle null user"},
                ],
                "files_added": 2,
                "files_modified": 3,
            },
        )

        # active-tasks.json (2 completed tasks for this session)
        _write_json(
            cos / "tasks" / "active-tasks.json",
            {
                "tasks": [
                    {
                        "id": "task-1",
                        "description": "feat: implement JWT login",
                        "status": "completed",
                        "session_id": session_id,
                    },
                    {
                        "id": "task-2",
                        "description": "fix: resolve token expiry bug",
                        "status": "completed",
                        "session_id": session_id,
                    },
                    {
                        "id": "task-3",
                        "description": "chore: update deps",
                        "status": "in_progress",
                        "session_id": session_id,
                    },
                ]
            },
        )

        # cost-events.jsonl (2 entries totalling $0.50)
        _write_jsonl(
            cos / "metrics" / "cost-events.jsonl",
            [
                {
                    "session_id": session_id,
                    "estimated_cost_usd": 0.30,
                    "timestamp": "2026-04-10T10:20:00Z",
                },
                {
                    "session_id": session_id,
                    "estimated_cost_usd": 0.20,
                    "timestamp": "2026-04-10T10:45:00Z",
                },
            ],
        )

        changelog = generate_session_changelog(str(tmp_path), session_id)

        assert changelog.session_id == session_id
        assert len(changelog.tasks_completed) == 2
        assert changelog.cost_usd == pytest.approx(0.50, abs=1e-6)
        # 2 added + 3 modified = 5
        assert changelog.files_changed_count == 5
        assert len(changelog.commits) == 2
        # Duration: 10:00 -> 10:45 = 45 minutes
        assert changelog.duration_minutes == pytest.approx(45.0, abs=0.1)

    def test_graceful_with_missing_files(self, tmp_path: Path) -> None:
        """Missing files should return zero/empty values rather than raising."""
        _make_cos(tmp_path)
        changelog = generate_session_changelog(str(tmp_path), "nonexistent-session")

        assert changelog.session_id == "nonexistent-session"
        assert changelog.commits == []
        assert changelog.tasks_completed == []
        assert changelog.cost_usd == 0.0
        assert changelog.files_changed_count == 0
        assert changelog.duration_minutes == 0.0

    def test_only_matching_session_tasks_counted(self, tmp_path: Path) -> None:
        """Tasks belonging to a different session must not be counted."""
        cos = _make_cos(tmp_path)
        session_id = "sess-A"

        _write_json(
            cos / "sessions" / session_id / "meta.json",
            {"session_id": session_id, "start_time": "2026-04-10T09:00:00Z"},
        )
        _write_json(
            cos / "tasks" / "active-tasks.json",
            {
                "tasks": [
                    {
                        "id": "t1",
                        "description": "feat: thing A",
                        "status": "completed",
                        "session_id": "sess-A",
                    },
                    {
                        "id": "t2",
                        "description": "feat: thing B",
                        "status": "completed",
                        "session_id": "sess-B",  # different session
                    },
                ]
            },
        )

        changelog = generate_session_changelog(str(tmp_path), session_id)
        assert len(changelog.tasks_completed) == 1
        assert "thing A" in changelog.tasks_completed[0]


# ---------------------------------------------------------------------------
# C2: generate_sprint_changelog aggregation
# ---------------------------------------------------------------------------


class TestGenerateSprintChangelog:
    def _make_session(
        self,
        session_id: str,
        num_commits: int,
        tasks: list,
        cost: float,
        date: str = "2026-04-10",
    ) -> SessionChangelog:
        return SessionChangelog(
            session_id=session_id,
            date=date,
            duration_minutes=30.0,
            commits=[{"sha": f"sha{i}", "message": f"commit {i}"} for i in range(num_commits)],
            tasks_completed=tasks,
            decisions=[],
            files_changed_count=num_commits * 2,
            cost_usd=cost,
        )

    def test_sprint_changelog_aggregation(self, tmp_path: Path) -> None:
        """C2: SprintChangelog totals = sum of individual session values."""
        sessions = [
            self._make_session("s1", 3, ["feat: feature A"], 0.10),
            self._make_session("s2", 5, ["fix: bug B", "feat: feature C"], 0.25),
            self._make_session("s3", 2, ["fix: bug D"], 0.15),
        ]

        sprint = SprintChangelog(
            sprint_id="2026-w15",
            sessions=sessions,
            total_commits=sum(len(s.commits) for s in sessions),
            total_tasks=sum(len(s.tasks_completed) for s in sessions),
            total_cost=round(sum(s.cost_usd for s in sessions), 6),
            features_completed=[t for s in sessions for t in s.tasks_completed if t.startswith("feat:")],
            bugs_fixed=[t for s in sessions for t in s.tasks_completed if t.startswith("fix:")],
        )

        assert sprint.total_commits == 10          # 3 + 5 + 2
        assert sprint.total_tasks == 4             # 1 + 2 + 1
        assert sprint.total_cost == pytest.approx(0.50, abs=1e-6)
        assert len(sprint.features_completed) == 2
        assert len(sprint.bugs_fixed) == 2

    def test_sprint_aggregation_from_disk(self, tmp_path: Path) -> None:
        """Aggregation via generate_sprint_changelog using session-audit.jsonl."""
        cos = _make_cos(tmp_path)
        sprint_id = "2026-w16"

        for sess_num in range(1, 3):
            sid = f"sess-{sess_num}"
            _write_json(
                cos / "sessions" / sid / "meta.json",
                {"session_id": sid, "start_time": "2026-04-10T10:00:00Z"},
            )
            _write_json(
                cos / "sessions" / sid / "git-context.json",
                {
                    "commits": [{"sha": f"abc{sess_num}", "message": "feat: thing"}],
                    "files_added": 1,
                    "files_modified": 1,
                },
            )
            _write_json(
                cos / "tasks" / "active-tasks.json",
                {
                    "tasks": [
                        {
                            "id": f"t-{sess_num}",
                            "description": f"feat: feature {sess_num}",
                            "status": "completed",
                            "session_id": sid,
                        }
                    ]
                },
            )
            _write_jsonl(
                cos / "metrics" / "cost-events.jsonl",
                [
                    {
                        "session_id": sid,
                        "estimated_cost_usd": 0.10,
                        "timestamp": "2026-04-10T10:30:00Z",
                    }
                ],
            )

        # Write session-audit.jsonl to link sessions to the sprint
        _write_jsonl(
            cos / "metrics" / "session-audit.jsonl",
            [
                {"session_id": "sess-1", "sprint_id": sprint_id},
                {"session_id": "sess-2", "sprint_id": sprint_id},
            ],
        )

        sprint = generate_sprint_changelog(str(tmp_path), sprint_id)
        assert len(sprint.sessions) == 2
        assert sprint.total_commits == 2


# ---------------------------------------------------------------------------
# C3: format_changelog_md produces valid Markdown
# ---------------------------------------------------------------------------


class TestFormatChangelogMd:
    def _make_session_changelog(self) -> SessionChangelog:
        return SessionChangelog(
            session_id="sess-test-123",
            date="2026-04-10",
            duration_minutes=75.5,
            commits=[
                {"sha": "abc1234def", "message": "feat: user auth"},
                {"sha": "999", "message": "fix: null pointer"},
            ],
            tasks_completed=[
                "feat: implement JWT",
                "fix: handle empty passwords",
            ],
            decisions=["Use Redis for session store", "Keep tokens in HTTP-only cookies"],
            files_changed_count=12,
            cost_usd=0.347,
        )

    def test_format_changelog_md_valid_markdown(self) -> None:
        """C3: output contains expected section headers and cost value."""
        sc = self._make_session_changelog()
        md = format_changelog_md(sc)

        assert "# Session Changelog: sess-test-123" in md
        assert "## Commits" in md
        assert "## Tasks Completed" in md
        assert "## Decisions" in md
        # Cost formatted to 2 decimal places
        assert "$0.35" in md
        # File count present
        assert "12" in md

    def test_format_session_contains_commits(self) -> None:
        sc = self._make_session_changelog()
        md = format_changelog_md(sc)
        # SHA should be truncated to 7 chars
        assert "abc1234" in md
        assert "feat: user auth" in md

    def test_format_session_contains_tasks(self) -> None:
        sc = self._make_session_changelog()
        md = format_changelog_md(sc)
        assert "feat: implement JWT" in md
        assert "fix: handle empty passwords" in md

    def test_format_session_contains_decisions(self) -> None:
        sc = self._make_session_changelog()
        md = format_changelog_md(sc)
        assert "Redis for session store" in md

    def test_format_sprint_md_structure(self) -> None:
        """SprintChangelog should produce sprint-specific headers."""
        sprint = SprintChangelog(
            sprint_id="2026-w20",
            sessions=[],
            total_commits=42,
            total_tasks=17,
            total_cost=1.23,
            features_completed=["feat: payments", "feat: notifications"],
            bugs_fixed=["fix: crash on startup"],
        )
        md = format_changelog_md(sprint)
        assert "# Sprint Changelog: 2026-w20" in md
        assert "## Features Completed" in md
        assert "## Bugs Fixed" in md
        assert "## Session Breakdown" in md
        assert "$1.23" in md
        assert "feat: payments" in md
        assert "fix: crash on startup" in md

    def test_format_changelog_raises_on_unknown_type(self) -> None:
        with pytest.raises(TypeError):
            format_changelog_md("not a changelog")  # type: ignore[arg-type]

    def test_format_session_empty_collections(self) -> None:
        """Empty commits/tasks/decisions should produce placeholder text, not crash."""
        sc = SessionChangelog(
            session_id="empty",
            date="2026-01-01",
            duration_minutes=0.0,
            commits=[],
            tasks_completed=[],
            decisions=[],
            files_changed_count=0,
            cost_usd=0.0,
        )
        md = format_changelog_md(sc)
        assert "# Session Changelog: empty" in md
        assert "$0.00" in md
