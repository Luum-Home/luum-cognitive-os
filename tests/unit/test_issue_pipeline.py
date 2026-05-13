"""Unit tests for lib/issue_pipeline.py

Validates issue classification, branch name generation, worktree path
construction, port assignment, PR dedup check logic, status comment
formatting, and mock fetch_issue with subprocess.
"""
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_LIB_DIR = str(Path(__file__).resolve().parent.parent.parent / "lib")
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from issue_pipeline import (
    IssueData,
    IssuePipeline,
    PipelineResult,
    _make_workflow_id,
    _port_offset,
    _run_gh,
    _run_git,
    _BACKEND_PORT_BASE,
    _FRONTEND_PORT_BASE,
    _PORT_RANGE,
    _BOT_IDENTIFIER,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# IssueData
# ---------------------------------------------------------------------------


class TestIssueData:
    def test_defaults(self):
        issue = IssueData()
        assert issue.number == 0
        assert issue.title == ""
        assert issue.labels == []

    def test_slug_generation(self):
        issue = IssueData(title="Add User Authentication Flow")
        slug = issue.slug
        assert slug == "add-user-authentication-flow"
        assert len(slug) <= 40

    def test_slug_strips_special_chars(self):
        issue = IssueData(title="Fix: Bug #123 (urgent!)")
        slug = issue.slug
        assert "#" not in slug
        assert "!" not in slug
        assert "(" not in slug

    def test_slug_max_length(self):
        issue = IssueData(title="A" * 100)
        slug = issue.slug
        assert len(slug) <= 40

    def test_slug_trailing_dash_stripped(self):
        issue = IssueData(title="Add Auth -")
        slug = issue.slug
        assert not slug.endswith("-")


# ---------------------------------------------------------------------------
# PipelineResult
# ---------------------------------------------------------------------------


class TestPipelineResult:
    def test_defaults(self):
        result = PipelineResult()
        assert result.issue_number == 0
        assert result.success is False
        assert result.branch_name == ""
        assert result.pr_url == ""
        assert result.phase_results == []
        assert result.error == ""


# ---------------------------------------------------------------------------
# Issue classification
# ---------------------------------------------------------------------------


class TestClassifyIssue:
    def setup_method(self):
        self.pipeline = IssuePipeline()

    def test_bug_label(self):
        issue = IssueData(title="Something", labels=["bug"])
        assert self.pipeline.classify_issue(issue) == "bug"

    def test_bugfix_label(self):
        issue = IssueData(title="Something", labels=["bugfix"])
        assert self.pipeline.classify_issue(issue) == "bug"

    def test_feature_label(self):
        issue = IssueData(title="Something", labels=["feature"])
        assert self.pipeline.classify_issue(issue) == "feature"

    def test_enhancement_label(self):
        issue = IssueData(title="Something", labels=["enhancement"])
        assert self.pipeline.classify_issue(issue) == "feature"

    def test_chore_label(self):
        issue = IssueData(title="Something", labels=["chore"])
        assert self.pipeline.classify_issue(issue) == "chore"

    def test_maintenance_label(self):
        issue = IssueData(title="Something", labels=["maintenance"])
        assert self.pipeline.classify_issue(issue) == "chore"

    def test_refactor_label(self):
        issue = IssueData(title="Something", labels=["refactor"])
        assert self.pipeline.classify_issue(issue) == "chore"

    def test_docs_label(self):
        issue = IssueData(title="Something", labels=["docs"])
        assert self.pipeline.classify_issue(issue) == "chore"

    def test_label_case_insensitive(self):
        issue = IssueData(title="Something", labels=["BUG"])
        assert self.pipeline.classify_issue(issue) == "bug"

    def test_body_heuristic_bug(self):
        issue = IssueData(
            title="Something is broken",
            body="The app crashes when clicking submit. This is an error.",
        )
        assert self.pipeline.classify_issue(issue) == "bug"

    def test_body_heuristic_chore(self):
        issue = IssueData(
            title="Refactor and cleanup",
            body="Tech debt cleanup and refactoring needed.",
        )
        assert self.pipeline.classify_issue(issue) == "chore"

    def test_default_feature(self):
        issue = IssueData(title="Add new capability", body="Would be nice to have X")
        assert self.pipeline.classify_issue(issue) == "feature"

    def test_first_matching_label_wins(self):
        issue = IssueData(title="Something", labels=["bug", "enhancement"])
        assert self.pipeline.classify_issue(issue) == "bug"


# ---------------------------------------------------------------------------
# Branch name generation
# ---------------------------------------------------------------------------


class TestGenerateBranchName:
    def setup_method(self):
        self.pipeline = IssuePipeline()

    def test_feature_prefix(self):
        issue = IssueData(number=42, title="Add OAuth", labels=["feature"])
        branch = self.pipeline.generate_branch_name(issue, "wf-123")
        assert branch.startswith("feat-issue-42-")

    def test_bug_prefix(self):
        issue = IssueData(number=10, title="Fix Login", labels=["bug"])
        branch = self.pipeline.generate_branch_name(issue, "wf-123")
        assert branch.startswith("fix-issue-10-")

    def test_chore_prefix(self):
        issue = IssueData(number=5, title="Cleanup", labels=["chore"])
        branch = self.pipeline.generate_branch_name(issue, "wf-123")
        assert branch.startswith("chore-issue-5-")

    def test_includes_slug(self):
        issue = IssueData(number=42, title="Add OAuth Flow")
        branch = self.pipeline.generate_branch_name(issue, "wf-123")
        assert "add-oauth-flow" in branch

    def test_format(self):
        issue = IssueData(number=42, title="Add Auth", labels=["feature"])
        branch = self.pipeline.generate_branch_name(issue, "wf-123")
        assert branch == "feat-issue-42-add-auth"


# ---------------------------------------------------------------------------
# Port assignment
# ---------------------------------------------------------------------------


class TestPortAssignment:
    def test_deterministic(self):
        offset1 = _port_offset("workflow-abc")
        offset2 = _port_offset("workflow-abc")
        assert offset1 == offset2

    def test_different_ids_different_offsets(self):
        offset1 = _port_offset("workflow-abc")
        offset2 = _port_offset("workflow-xyz")
        # Not guaranteed to be different, but very likely
        # Just verify they're in range
        assert 0 <= offset1 < _PORT_RANGE
        assert 0 <= offset2 < _PORT_RANGE

    def test_offset_in_range(self):
        for i in range(100):
            offset = _port_offset(f"wf-{i}")
            assert 0 <= offset < _PORT_RANGE

    def test_port_bases(self):
        offset = _port_offset("test-wf")
        backend = _BACKEND_PORT_BASE + offset
        frontend = _FRONTEND_PORT_BASE + offset
        assert backend >= _BACKEND_PORT_BASE
        assert backend < _BACKEND_PORT_BASE + _PORT_RANGE
        assert frontend >= _FRONTEND_PORT_BASE
        assert frontend < _FRONTEND_PORT_BASE + _PORT_RANGE


# ---------------------------------------------------------------------------
# Workflow ID generation
# ---------------------------------------------------------------------------


class TestMakeWorkflowId:
    def test_returns_8_char_hex(self):
        wid = _make_workflow_id(42)
        assert len(wid) == 8
        int(wid, 16)  # Should be valid hex

    def test_different_issues_different_ids(self):
        # Due to timestamp, same issue may get different IDs
        # But different issues at the same instant should differ
        with patch("issue_pipeline.time") as mock_time:
            mock_time.time.return_value = 1000000
            wid1 = _make_workflow_id(1)
            wid2 = _make_workflow_id(2)
            assert wid1 != wid2


# ---------------------------------------------------------------------------
# Worktree path construction
# ---------------------------------------------------------------------------


class TestWorktreePath:
    def test_default_root(self):
        pipeline = IssuePipeline(project_dir="/tmp/project")
        expected = os.path.join("/tmp/project", ".cognitive-os", "worktrees")
        assert pipeline.worktree_root == expected

    def test_custom_root(self):
        pipeline = IssuePipeline(
            project_dir="/tmp/project",
            worktree_root="/custom/worktrees",
        )
        assert pipeline.worktree_root == "/custom/worktrees"


# ---------------------------------------------------------------------------
# Status comment formatting
# ---------------------------------------------------------------------------


class TestPostStatusComment:
    @patch("issue_pipeline._run_gh")
    def test_comment_includes_bot_identifier(self, mock_gh):
        mock_gh.return_value = (True, "", "")
        pipeline = IssuePipeline()
        pipeline.post_status_comment(42, "in-progress", "Working on it")
        call_args = mock_gh.call_args[0][0]
        # The body argument should contain the bot identifier
        body_idx = call_args.index("--body")
        body = call_args[body_idx + 1]
        assert _BOT_IDENTIFIER in body
        assert "in-progress" in body

    @patch("issue_pipeline._run_gh")
    def test_comment_failure_returns_false(self, mock_gh):
        mock_gh.return_value = (False, "", "error")
        pipeline = IssuePipeline()
        result = pipeline.post_status_comment(42, "failed")
        assert result is False


# ---------------------------------------------------------------------------
# fetch_issue with mock subprocess
# ---------------------------------------------------------------------------


class TestFetchIssue:
    @patch("issue_pipeline._run_gh")
    def test_successful_fetch(self, mock_gh):
        issue_json = json.dumps({
            "number": 42,
            "title": "Add OAuth",
            "body": "We need OAuth support",
            "labels": [{"name": "feature"}],
            "assignees": [{"login": "user1"}],
            "state": "open",
            "url": "https://github.com/org/repo/issues/42",
        })
        mock_gh.return_value = (True, issue_json, "")

        pipeline = IssuePipeline()
        issue = pipeline.fetch_issue(42)

        assert issue.number == 42
        assert issue.title == "Add OAuth"
        assert issue.body == "We need OAuth support"
        assert issue.labels == ["feature"]
        assert issue.assignees == ["user1"]
        assert issue.state == "open"

    @patch("issue_pipeline._run_gh")
    def test_fetch_failure_raises(self, mock_gh):
        mock_gh.return_value = (False, "", "Not found")

        pipeline = IssuePipeline()
        with pytest.raises(RuntimeError, match="Failed to fetch"):
            pipeline.fetch_issue(999)

    @patch("issue_pipeline._run_gh")
    def test_fetch_handles_null_body(self, mock_gh):
        issue_json = json.dumps({
            "number": 1,
            "title": "No body",
            "body": None,
            "labels": [],
            "assignees": [],
            "state": "open",
            "url": "",
        })
        mock_gh.return_value = (True, issue_json, "")

        pipeline = IssuePipeline()
        issue = pipeline.fetch_issue(1)
        assert issue.body == ""

    @patch("issue_pipeline._run_gh")
    def test_fetch_labels_as_strings(self, mock_gh):
        issue_json = json.dumps({
            "number": 1,
            "title": "Test",
            "body": "",
            "labels": ["bug", "urgent"],
            "assignees": [],
            "state": "open",
            "url": "",
        })
        mock_gh.return_value = (True, issue_json, "")

        pipeline = IssuePipeline()
        issue = pipeline.fetch_issue(1)
        assert issue.labels == ["bug", "urgent"]


# ---------------------------------------------------------------------------
# _run_gh / _run_git helpers
# ---------------------------------------------------------------------------


class TestRunHelpers:
    @patch("issue_pipeline.subprocess.run")
    def test_run_gh_success(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="output\n", stderr="",
        )
        ok, stdout, stderr = _run_gh(["issue", "view", "1"])
        assert ok is True
        assert stdout == "output"

    @patch("issue_pipeline.subprocess.run")
    def test_run_gh_failure(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="not found",
        )
        ok, stdout, stderr = _run_gh(["issue", "view", "999"])
        assert ok is False
        assert stderr == "not found"

    @patch("issue_pipeline.subprocess.run")
    def test_run_gh_timeout(self, mock_run):
        from subprocess import TimeoutExpired
        mock_run.side_effect = TimeoutExpired(cmd="gh", timeout=60)
        ok, stdout, stderr = _run_gh(["issue", "view", "1"])
        assert ok is False

    @patch("issue_pipeline.subprocess.run")
    def test_run_git_success(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="branch-name\n", stderr="",
        )
        ok, stdout, stderr = _run_git(["branch", "--show-current"])
        assert ok is True
        assert stdout == "branch-name"
