#!/usr/bin/env python3
"""ORPHAN: This module is not actively used. See docs/architecture/reality-audit.md.

Issue-to-PR Pipeline — Fetches a GitHub issue, classifies it, creates a worktree,
runs the SDD pipeline, and opens a pull request.

Uses only subprocess + gh CLI (no PyGithub dependency).
Python 3.9+ compatible.

Usage:
    from lib.issue_pipeline import IssuePipeline
    pipeline = IssuePipeline(project_dir="/path/to/repo")
    pipeline.run(42)
"""

import hashlib
import json
import logging
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from lib.claude_executor import ClaudeExecutor, ClaudeResult

logger = logging.getLogger(__name__)

# ANSI colors
_BOLD = "\033[1m"
_GREEN = "\033[32m"
_RED = "\033[31m"
_CYAN = "\033[36m"
_DIM = "\033[2m"
_YELLOW = "\033[33m"
_RESET = "\033[0m"

# Port allocation bases
_BACKEND_PORT_BASE = 9100
_FRONTEND_PORT_BASE = 9200
_PORT_RANGE = 100  # max offset from base

# Bot comment identifier
_BOT_IDENTIFIER = "[COS-AGENTS]"


@dataclass
class IssueData:
    """Parsed GitHub issue data."""

    number: int = 0
    title: str = ""
    body: str = ""
    labels: List[str] = field(default_factory=list)
    assignees: List[str] = field(default_factory=list)
    state: str = ""
    url: str = ""

    @property
    def slug(self) -> str:
        """Generate a short slug from the title (max 40 chars)."""
        text = self.title.lower()
        text = re.sub(r"[^a-z0-9\s-]", "", text)
        text = re.sub(r"[\s_]+", "-", text).strip("-")
        return text[:40].rstrip("-")


@dataclass
class PipelineResult:
    """Result of the full issue-to-PR pipeline."""

    issue_number: int = 0
    success: bool = False
    branch_name: str = ""
    pr_url: str = ""
    worktree_path: str = ""
    workflow_id: str = ""
    phase_results: List[ClaudeResult] = field(default_factory=list)
    error: str = ""
    elapsed_seconds: float = 0.0


def _run_gh(
    args: List[str],
    cwd: Optional[str] = None,
) -> Tuple[bool, str, str]:
    """Run a gh CLI command and return (success, stdout, stderr)."""
    cmd = ["gh"] + args
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=60,
        )
        return proc.returncode == 0, proc.stdout.strip(), proc.stderr.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        return False, "", str(exc)


def _run_git(
    args: List[str],
    cwd: Optional[str] = None,
) -> Tuple[bool, str, str]:
    """Run a git command and return (success, stdout, stderr)."""
    cmd = ["git"] + args
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=120,
        )
        return proc.returncode == 0, proc.stdout.strip(), proc.stderr.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        return False, "", str(exc)


def _make_workflow_id(issue_number: int) -> str:
    """Generate a deterministic workflow ID from issue number + timestamp."""
    ts = int(time.time())
    raw = f"issue-{issue_number}-{ts}"
    return hashlib.sha256(raw.encode()).hexdigest()[:8]


def _port_offset(workflow_id: str) -> int:
    """Deterministic port offset from workflow ID hash."""
    h = int(hashlib.md5(workflow_id.encode()).hexdigest(), 16)
    return h % _PORT_RANGE


class IssuePipeline:
    """End-to-end pipeline: GitHub issue -> SDD -> Pull Request.

    Usage:
        pipeline = IssuePipeline(project_dir=".")
        result = pipeline.run(42)
        if result.success:
            print(f"PR created: {result.pr_url}")
    """

    # SDD phases to run in order
    SDD_PHASES: List[str] = [
        "explore",
        "propose",
        "spec",
        "design",
        "tasks",
        "apply",
        "verify",
    ]

    def __init__(
        self,
        project_dir: str = ".",
        claude_bin: str = "claude",
        timeout_per_phase: int = 900,
        model: Optional[str] = None,
        base_branch: str = "main",
        worktree_root: Optional[str] = None,
        verbose: bool = False,
    ):
        self.project_dir = os.path.abspath(project_dir)
        self.claude_bin = claude_bin
        self.timeout_per_phase = timeout_per_phase
        self.model = model
        self.base_branch = base_branch
        self.worktree_root = worktree_root or os.path.join(
            self.project_dir, ".cognitive-os", "worktrees"
        )
        self.verbose = verbose

    # ── Step 1: Fetch Issue ──────────────────────────────────────────

    def fetch_issue(self, issue_number: int) -> IssueData:
        """Fetch issue data from GitHub using gh CLI.

        Args:
            issue_number: The GitHub issue number.

        Returns:
            IssueData with title, body, labels, assignees.

        Raises:
            RuntimeError: If gh CLI fails.
        """
        ok, stdout, stderr = _run_gh(
            [
                "issue", "view", str(issue_number),
                "--json", "number,title,body,labels,assignees,state,url",
            ],
            cwd=self.project_dir,
        )
        if not ok:
            raise RuntimeError(
                f"Failed to fetch issue #{issue_number}: {stderr}"
            )

        data = json.loads(stdout)
        return IssueData(
            number=data.get("number", issue_number),
            title=data.get("title", ""),
            body=data.get("body", "") or "",
            labels=[
                lbl["name"] if isinstance(lbl, dict) else str(lbl)
                for lbl in data.get("labels", [])
            ],
            assignees=[
                a["login"] if isinstance(a, dict) else str(a)
                for a in data.get("assignees", [])
            ],
            state=data.get("state", ""),
            url=data.get("url", ""),
        )

    # ── Step 2: Classify Issue ───────────────────────────────────────

    def classify_issue(self, issue_data: IssueData) -> str:
        """Classify issue as feature, bug, or chore.

        Classification priority:
        1. Explicit labels (bug, feature, enhancement, chore, etc.)
        2. Body content heuristics
        3. Default: feature

        Args:
            issue_data: Parsed issue data.

        Returns:
            One of: "feature", "bug", "chore".
        """
        labels_lower = [lbl.lower() for lbl in issue_data.labels]

        # Label-based classification
        bug_labels = {"bug", "bugfix", "fix", "defect", "error"}
        feature_labels = {
            "feature", "enhancement", "feat", "new-feature",
            "feature-request", "improvement",
        }
        chore_labels = {
            "chore", "maintenance", "refactor", "tech-debt",
            "ci", "docs", "documentation", "infrastructure",
            "devops", "tooling", "cleanup",
        }

        for lbl in labels_lower:
            if lbl in bug_labels:
                return "bug"
            if lbl in feature_labels:
                return "feature"
            if lbl in chore_labels:
                return "chore"

        # Body heuristic fallback
        body_lower = issue_data.body.lower()
        title_lower = issue_data.title.lower()
        combined = f"{title_lower} {body_lower}"

        bug_signals = [
            "bug", "broken", "crash", "error", "fix",
            "doesn't work", "does not work", "regression",
            "unexpected", "wrong", "failing", "issue",
        ]
        chore_signals = [
            "refactor", "cleanup", "tech debt", "ci/cd",
            "documentation", "upgrade", "migrate", "chore",
            "devops", "tooling",
        ]

        bug_score = sum(1 for s in bug_signals if s in combined)
        chore_score = sum(1 for s in chore_signals if s in combined)

        if bug_score >= 2:
            return "bug"
        if chore_score >= 2:
            return "chore"

        return "feature"

    # ── Step 3: Generate Branch Name ─────────────────────────────────

    def generate_branch_name(
        self,
        issue_data: IssueData,
        workflow_id: str,
    ) -> str:
        """Generate a branch name from issue data.

        Format: {type}-issue-{number}-{short-slug}

        Args:
            issue_data: Parsed issue data.
            workflow_id: Unique workflow identifier.

        Returns:
            Branch name string.
        """
        issue_type = self.classify_issue(issue_data)

        # Map type to branch prefix
        prefix_map = {
            "feature": "feat",
            "bug": "fix",
            "chore": "chore",
        }
        prefix = prefix_map.get(issue_type, "feat")
        slug = issue_data.slug
        return f"{prefix}-issue-{issue_data.number}-{slug}"

    # ── Step 4: Create Worktree ──────────────────────────────────────

    def create_worktree(
        self,
        branch_name: str,
        workflow_id: str,
    ) -> Tuple[str, int, int]:
        """Create a git worktree for isolated development.

        Creates the worktree at .cognitive-os/worktrees/{workflow_id}/
        with deterministic port allocation based on workflow_id hash.

        Args:
            branch_name: Git branch name to create.
            workflow_id: Unique workflow identifier.

        Returns:
            Tuple of (worktree_path, backend_port, frontend_port).

        Raises:
            RuntimeError: If worktree creation fails.
        """
        worktree_path = os.path.join(self.worktree_root, workflow_id)
        os.makedirs(self.worktree_root, exist_ok=True)

        # Calculate deterministic ports
        offset = _port_offset(workflow_id)
        backend_port = _BACKEND_PORT_BASE + offset
        frontend_port = _FRONTEND_PORT_BASE + offset

        # Create worktree with new branch from base
        ok, stdout, stderr = _run_git(
            [
                "worktree", "add",
                "-b", branch_name,
                worktree_path,
                self.base_branch,
            ],
            cwd=self.project_dir,
        )
        if not ok:
            # Branch may already exist — try without -b
            if "already exists" in stderr:
                ok2, stdout2, stderr2 = _run_git(
                    ["worktree", "add", worktree_path, branch_name],
                    cwd=self.project_dir,
                )
                if not ok2:
                    raise RuntimeError(
                        f"Failed to create worktree: {stderr2}"
                    )
            else:
                raise RuntimeError(
                    f"Failed to create worktree: {stderr}"
                )

        logger.info(
            "Worktree created at %s (ports: %d/%d)",
            worktree_path,
            backend_port,
            frontend_port,
        )
        return worktree_path, backend_port, frontend_port

    # ── Step 5: Run SDD Pipeline ─────────────────────────────────────

    def run_sdd_pipeline(
        self,
        issue_data: IssueData,
        worktree_path: str,
    ) -> List[ClaudeResult]:
        """Execute SDD phases via ClaudeExecutor in the worktree.

        Runs explore -> propose -> spec -> design -> tasks -> apply -> verify.
        Stops on first failure.

        Args:
            issue_data: Parsed issue data (used for change name).
            worktree_path: Path to the git worktree.

        Returns:
            List of ClaudeResults for each phase attempted.
        """
        change_name = f"issue-{issue_data.number}-{issue_data.slug}"
        issue_type = self.classify_issue(issue_data)

        executor = ClaudeExecutor(
            working_dir=worktree_path,
            default_timeout=self.timeout_per_phase,
        )

        # Build phase prompts — explore gets full issue context
        phase_prompts: Dict[str, str] = {
            "explore": (
                f"GitHub Issue #{issue_data.number}: {issue_data.title}\n\n"
                f"{issue_data.body}\n\n"
                f"Labels: {', '.join(issue_data.labels)}\n"
                f"Type: {issue_type}\n\n"
                f"/sdd-explore {change_name}"
            ),
            "propose": f"Run sdd-propose for change: {change_name}",
            "spec": f"Run sdd-spec for change: {change_name}",
            "design": f"Run sdd-design for change: {change_name}",
            "tasks": f"Run sdd-tasks for change: {change_name}",
            "apply": f"Run sdd-apply for change: {change_name}",
            "verify": f"Run sdd-verify for change: {change_name}",
        }

        results: List[ClaudeResult] = []

        for i, phase in enumerate(self.SDD_PHASES):
            print(
                f"\n{_BOLD}  [{i + 1}/{len(self.SDD_PHASES)}] "
                f"SDD {phase.upper()}{_RESET}"
            )

            prompt = phase_prompts[phase]
            result = executor.run(
                prompt=prompt,
                model=self.model,
                timeout=self.timeout_per_phase,
            )
            results.append(result)

            status = (
                f"{_GREEN}OK{_RESET}"
                if result.success
                else f"{_RED}FAIL{_RESET}"
            )
            duration = f"{result.duration_secs:.1f}s"
            print(f"  [{status}] {phase} completed in {duration}")

            if not result.success:
                logger.error(
                    "SDD pipeline failed at phase %s for %s: %s",
                    phase,
                    change_name,
                    result.error_message,
                )
                break

        return results

    # ── Step 6: Create PR ────────────────────────────────────────────

    def create_pr(
        self,
        branch_name: str,
        issue_data: IssueData,
        worktree_path: Optional[str] = None,
    ) -> str:
        """Create a pull request using gh CLI.

        Pushes the branch and creates a PR with proper title, body,
        and Closes #{number} reference.

        Args:
            branch_name: Git branch name.
            issue_data: Parsed issue data.
            worktree_path: Path to worktree (for push cwd).

        Returns:
            PR URL string.

        Raises:
            RuntimeError: If PR creation fails.
        """
        cwd = worktree_path or self.project_dir

        # Push branch to remote
        ok, stdout, stderr = _run_git(
            ["push", "-u", "origin", branch_name],
            cwd=cwd,
        )
        if not ok:
            raise RuntimeError(f"Failed to push branch: {stderr}")

        # Build PR body
        issue_type = self.classify_issue(issue_data)
        pr_title = f"{issue_type}: {issue_data.title}"
        if len(pr_title) > 72:
            pr_title = pr_title[:69] + "..."

        pr_body = (
            f"## Summary\n\n"
            f"Automated PR for issue #{issue_data.number}.\n\n"
            f"**Type:** {issue_type}\n"
            f"**Issue:** #{issue_data.number}\n\n"
            f"## Changes\n\n"
            f"Implemented via SDD pipeline (explore -> verify).\n\n"
            f"## Test Plan\n\n"
            f"- [ ] SDD verify phase passed\n"
            f"- [ ] Manual review of changes\n"
            f"- [ ] CI checks pass\n\n"
            f"Closes #{issue_data.number}\n\n"
            f"---\n"
            f"Generated by {_BOT_IDENTIFIER} issue-to-pr pipeline"
        )

        ok, stdout, stderr = _run_gh(
            [
                "pr", "create",
                "--title", pr_title,
                "--body", pr_body,
                "--base", self.base_branch,
                "--head", branch_name,
            ],
            cwd=cwd,
        )
        if not ok:
            raise RuntimeError(f"Failed to create PR: {stderr}")

        pr_url = stdout.strip()
        logger.info("PR created: %s", pr_url)
        return pr_url

    # ── Step 7: Post Status Comment ──────────────────────────────────

    def post_status_comment(
        self,
        issue_number: int,
        status: str,
        details: str = "",
    ) -> bool:
        """Post a bot comment on the issue with status update.

        Comments are prefixed with [COS-AGENTS] for identification.

        Args:
            issue_number: GitHub issue number.
            status: Status string (e.g., "in-progress", "completed", "failed").
            details: Additional details to include.

        Returns:
            True if comment was posted successfully.
        """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        body = (
            f"{_BOT_IDENTIFIER} **Status: {status}**\n\n"
            f"Timestamp: {timestamp}\n"
        )
        if details:
            body += f"\n{details}\n"

        ok, stdout, stderr = _run_gh(
            [
                "issue", "comment", str(issue_number),
                "--body", body,
            ],
            cwd=self.project_dir,
        )
        if not ok:
            logger.warning(
                "Failed to post comment on issue #%d: %s",
                issue_number,
                stderr,
            )
        return ok

    # ── Step 8: Cleanup Worktree ─────────────────────────────────────

    def cleanup_worktree(self, workflow_id: str) -> bool:
        """Remove worktree after PR is merged or abandoned.

        Args:
            workflow_id: Unique workflow identifier.

        Returns:
            True if cleanup succeeded.
        """
        worktree_path = os.path.join(self.worktree_root, workflow_id)

        if not os.path.isdir(worktree_path):
            logger.info("Worktree already removed: %s", worktree_path)
            return True

        ok, stdout, stderr = _run_git(
            ["worktree", "remove", "--force", worktree_path],
            cwd=self.project_dir,
        )
        if not ok:
            logger.warning(
                "Failed to remove worktree %s: %s",
                worktree_path,
                stderr,
            )
            return False

        logger.info("Worktree removed: %s", worktree_path)
        return True

    # ── Step 9: Full Pipeline ────────────────────────────────────────

    def run(self, issue_number: int) -> PipelineResult:
        """Run the full issue-to-PR pipeline.

        Chains all steps with error handling:
        1. Fetch issue
        2. Classify
        3. Generate branch name
        4. Create worktree
        5. Run SDD pipeline
        6. Create PR
        7. Post status comments

        On failure, posts a failure comment and cleans up.

        Args:
            issue_number: GitHub issue number.

        Returns:
            PipelineResult with success status, PR URL, etc.
        """
        pipeline_start = time.time()
        result = PipelineResult(issue_number=issue_number)
        workflow_id = _make_workflow_id(issue_number)
        result.workflow_id = workflow_id

        print(f"\n{_BOLD}{_CYAN}{'=' * 50}{_RESET}")
        print(f"{_BOLD}{_CYAN}  Issue-to-PR Pipeline: #{issue_number}{_RESET}")
        print(f"{_BOLD}{_CYAN}{'=' * 50}{_RESET}")

        try:
            # Step 1: Fetch issue
            print(f"\n{_DIM}[1/7] Fetching issue #{issue_number}...{_RESET}")
            issue_data = self.fetch_issue(issue_number)
            print(f"  Title: {issue_data.title}")
            print(f"  Labels: {', '.join(issue_data.labels) or 'none'}")

            # Step 2: Classify
            issue_type = self.classify_issue(issue_data)
            print(f"  Type: {issue_type}")

            # Step 3: Generate branch name
            print(f"\n{_DIM}[2/7] Generating branch name...{_RESET}")
            branch_name = self.generate_branch_name(issue_data, workflow_id)
            result.branch_name = branch_name
            print(f"  Branch: {branch_name}")

            # Step 4: Create worktree
            print(f"\n{_DIM}[3/7] Creating worktree...{_RESET}")
            worktree_path, backend_port, frontend_port = (
                self.create_worktree(branch_name, workflow_id)
            )
            result.worktree_path = worktree_path
            print(f"  Path: {worktree_path}")
            print(f"  Ports: backend={backend_port}, frontend={frontend_port}")

            # Post in-progress comment
            self.post_status_comment(
                issue_number,
                "in-progress",
                (
                    f"Branch: `{branch_name}`\n"
                    f"Workflow ID: `{workflow_id}`\n"
                    f"Running SDD pipeline..."
                ),
            )

            # Step 5: Run SDD pipeline
            print(f"\n{_DIM}[4/7] Running SDD pipeline...{_RESET}")
            phase_results = self.run_sdd_pipeline(issue_data, worktree_path)
            result.phase_results = phase_results

            # Check if all phases passed
            failed_indices = [
                i for i, r in enumerate(phase_results) if not r.success
            ]
            if failed_indices:
                failed_name = self.SDD_PHASES[failed_indices[0]]
                raise RuntimeError(
                    f"SDD pipeline failed at phase: {failed_name}"
                )

            # Step 6: Create PR
            print(f"\n{_DIM}[5/7] Creating pull request...{_RESET}")
            pr_url = self.create_pr(branch_name, issue_data, worktree_path)
            result.pr_url = pr_url
            print(f"  PR: {pr_url}")

            # Step 7: Post completion comment
            print(f"\n{_DIM}[6/7] Posting status comment...{_RESET}")
            phases_summary = ", ".join(
                f"{self.SDD_PHASES[i]} ({r.duration_secs:.0f}s)"
                for i, r in enumerate(phase_results)
            )
            self.post_status_comment(
                issue_number,
                "completed",
                (
                    f"PR created: {pr_url}\n"
                    f"Branch: `{branch_name}`\n"
                    f"Phases: {phases_summary}\n"
                ),
            )

            # Step 8: Cleanup worktree
            print(f"\n{_DIM}[7/7] Cleaning up worktree...{_RESET}")
            self.cleanup_worktree(workflow_id)

            result.success = True

        except Exception as exc:
            result.error = str(exc)
            logger.error(
                "Pipeline failed for issue #%d: %s",
                issue_number,
                exc,
            )
            print(f"\n  {_RED}[FAIL]{_RESET} {exc}")

            # Post failure comment
            self.post_status_comment(
                issue_number,
                "failed",
                (
                    f"Error: {exc}\n"
                    f"Workflow ID: `{workflow_id}`\n"
                    f"Resume manually if needed."
                ),
            )

            # Cleanup on failure
            if result.worktree_path:
                self.cleanup_worktree(workflow_id)

        result.elapsed_seconds = time.time() - pipeline_start

        # Print summary
        total = f"{result.elapsed_seconds:.1f}s"
        if result.success:
            print(f"\n{_BOLD}{_GREEN}{'=' * 50}{_RESET}")
            print(f"{_BOLD}{_GREEN}  PIPELINE COMPLETE ({total}){_RESET}")
            print(f"{_BOLD}{_GREEN}{'=' * 50}{_RESET}")
            print(f"  PR: {result.pr_url}")
        else:
            print(f"\n{_BOLD}{_RED}{'=' * 50}{_RESET}")
            print(f"{_BOLD}{_RED}  PIPELINE FAILED ({total}){_RESET}")
            print(f"{_BOLD}{_RED}{'=' * 50}{_RESET}")
            print(f"  Error: {result.error}")

        return result


# ── CLI entry point ──────────────────────────────────────────────────

def main() -> None:
    """CLI entry point for the issue-to-PR pipeline."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Issue-to-PR Pipeline: fetch issue, run SDD, create PR"
    )
    parser.add_argument(
        "issue_number",
        type=int,
        help="GitHub issue number",
    )
    parser.add_argument(
        "--project-dir",
        default=".",
        help="Project directory (default: cwd)",
    )
    parser.add_argument(
        "--base-branch",
        default="main",
        help="Base branch for PR (default: main)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Claude model to use",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=900,
        help="Timeout per SDD phase in seconds (default: 900)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    pipeline = IssuePipeline(
        project_dir=args.project_dir,
        timeout_per_phase=args.timeout,
        model=args.model,
        base_branch=args.base_branch,
        verbose=args.verbose,
    )

    result = pipeline.run(args.issue_number)
    raise SystemExit(0 if result.success else 1)


if __name__ == "__main__":
    main()
