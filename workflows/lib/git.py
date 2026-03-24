"""Git operations for backend workflows."""

import subprocess
from typing import Tuple

from .utils import get_project_root


def run_git(args: list, cwd: str = None) -> Tuple[bool, str]:
    """Run a git command and return (success, output)."""
    if cwd is None:
        cwd = get_project_root()
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout.strip() or result.stderr.strip()
        return result.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, "Git command timed out"
    except Exception as e:
        return False, str(e)


def get_current_branch() -> str:
    """Get the current branch name."""
    success, output = run_git(["branch", "--show-current"])
    return output if success else "unknown"


def create_branch(
    ticket_id: str,
    description: str,
    branch_type: str = "feat",
    base_branch: str = "develop",
) -> Tuple[bool, str]:
    """Create a new branch from base branch.

    Args:
        ticket_id: Ticket ID (e.g., DEV-123).
        description: Short description for branch name.
        branch_type: "feat", "chore", "fix", or "migration".
        base_branch: Base branch to create from (default: develop).

    Returns:
        (success, branch_name or error message)
    """
    # Normalize description for branch name
    slug = description.lower()
    slug = slug.replace(" ", "-")
    slug = "".join(c for c in slug if c.isalnum() or c == "-")
    slug = slug[:30].strip("-")

    branch_name = f"{branch_type}/{ticket_id.lower()}-{slug}"

    # Checkout base branch and pull
    success, output = run_git(["checkout", base_branch])
    if not success:
        return False, f"Failed to checkout {base_branch}: {output}"

    success, output = run_git(["pull", "origin", base_branch])
    if not success:
        return False, f"Failed to pull {base_branch}: {output}"

    # Create and checkout new branch (or switch if it exists)
    success, output = run_git(["checkout", "-b", branch_name])
    if not success:
        success, output = run_git(["checkout", branch_name])
        if not success:
            return False, f"Failed to checkout branch: {output}"

    return True, branch_name


def commit_changes(message: str, cwd: str = None) -> Tuple[bool, str]:
    """Stage all changes and commit."""
    if cwd is None:
        cwd = get_project_root()
    success, output = run_git(["add", "."], cwd=cwd)
    if not success:
        return False, f"Failed to stage changes: {output}"

    success, output = run_git(["commit", "-m", message], cwd=cwd)
    if not success:
        return False, f"Failed to commit: {output}"

    return True, output


def push_branch(branch_name: str) -> Tuple[bool, str]:
    """Push branch to origin."""
    success, output = run_git(["push", "-u", "origin", branch_name])
    if not success:
        return False, f"Failed to push: {output}"
    return True, output


def create_pr(
    title: str,
    description: str,
    target_branch: str = "develop",
) -> Tuple[bool, str]:
    """Create a Pull Request using gh CLI.

    Returns:
        (success, PR URL or error message)
    """
    cwd = get_project_root()

    try:
        result = subprocess.run(
            [
                "gh",
                "pr",
                "create",
                "--title",
                title,
                "--body",
                description,
                "--base",
                target_branch,
            ],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0:
            output = result.stdout.strip()
            for line in output.split("\n"):
                if "https://" in line and "/pull/" in line:
                    return True, line.strip()
            return True, output
        else:
            return False, result.stderr.strip() or result.stdout.strip()

    except FileNotFoundError:
        return False, "gh CLI not found. Install with: brew install gh"
    except subprocess.TimeoutExpired:
        return False, "PR creation timed out"
    except Exception as e:
        return False, str(e)


def get_diff_stat() -> str:
    """Get git diff --stat output."""
    success, output = run_git(["diff", "--stat", "HEAD~1"])
    return output if success else "No diff available"
