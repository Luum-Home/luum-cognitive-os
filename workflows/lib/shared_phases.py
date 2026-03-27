"""Shared pipeline phases for build, test, lint, commit, and pull request.

Adapted for multi-language backend services (Go, Spring Boot, NestJS, Express).
"""

import os
import subprocess
from typing import Callable, List, Tuple

from .agent import prompt_with_retry
from .clickup import (
    add_task_comment,
    fetch_task,
    update_task_status,
)
from .data_types import AgentPromptRequest, ServiceConfig
from .git import (
    commit_changes,
    create_branch,
    create_pr,
    get_diff_stat,
    push_branch,
)
from .utils import get_project_root, get_service_abs_path

# ANSI colors
BOLD = "\033[1m"
GREEN = "\033[32m"
RED = "\033[31m"
CYAN = "\033[36m"
DIM = "\033[2m"
YELLOW = "\033[33m"
RESET = "\033[0m"

MAX_BUILD_FIX_ATTEMPTS = int(os.environ.get("MAX_BUILD_FIX_ATTEMPTS", "3"))
MAX_TEST_FIX_ATTEMPTS = int(os.environ.get("MAX_TEST_FIX_ATTEMPTS", "3"))


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:.0f}s"


def _run_service_command(
    command: str,
    service: ServiceConfig,
    timeout: int = 300,
) -> Tuple[bool, str]:
    """Run a shell command in the service directory.

    Args:
        command: Shell command string to execute.
        service: Service configuration.
        timeout: Command timeout in seconds.

    Returns:
        (success, output) tuple.
    """
    if not command:
        return True, "No command configured (skipped)"

    service_abs_path = get_service_abs_path(service)

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=service_abs_path,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout + result.stderr
        return result.returncode == 0, output.strip()
    except subprocess.TimeoutExpired:
        return False, f"Command timed out after {timeout}s: {command}"
    except Exception as e:
        return False, str(e)


def phase_build(state, step_label: str, service: ServiceConfig) -> bool:
    """Run language-aware build with fix-build retry loop.

    Build commands by language:
    - Go: go build ./...
    - Spring Boot: ./gradlew build
    - NestJS/Express: npx tsc --noEmit
    """
    lang = service.language
    print(
        f"\n{BOLD}{step_label} Building ({lang} - {service.name})...{RESET}"
    )

    project_root = get_project_root()

    for attempt in range(MAX_BUILD_FIX_ATTEMPTS + 1):
        print(
            f"  {DIM}Running build "
            f"(attempt {attempt + 1}/{MAX_BUILD_FIX_ATTEMPTS + 1})...{RESET}"
        )
        print(f"  {DIM}Command: {service.build}{RESET}")

        success, output = _run_service_command(
            service.build, service, timeout=600
        )

        if success:
            state.update(build_passed=True)
            print(f"  {GREEN}OK{RESET} Build passed")
            return True

        error_output = output[:2000]
        print(f"  {RED}FAIL{RESET} Build failed")
        print(f"  {DIM}{error_output[:200]}{RESET}")

        if attempt < MAX_BUILD_FIX_ATTEMPTS:
            state.update(build_retry_count=attempt + 1)
            state.save()
            print(
                f"  {YELLOW}-> Invoking fix-build "
                f"(attempt {attempt + 1})...{RESET}"
            )
            fix_output = os.path.join(
                state.get_state_dir(),
                f"fix_build_attempt_{attempt + 1}",
                "raw_output.jsonl",
            )
            fix_prompt = (
                f"Fix the following build error in the {lang} service "
                f"at {service.path}. Build command: `{service.build}`. "
                f"Error output:\n\n{error_output}"
            )
            fix_request = AgentPromptRequest(
                prompt=fix_prompt,
                allowed_tools=[
                    "Read", "Edit", "Write", "Glob", "Grep", "Bash",
                ],
                timeout_seconds=300,
            )
            prompt_with_retry(
                fix_request, project_root, fix_output, max_retries=0
            )

    state.update(build_passed=False, build_errors=error_output)
    return False


def phase_test(state, step_label: str, service: ServiceConfig) -> bool:
    """Run language-aware tests with fix retry loop.

    Test commands by language:
    - Go: go test ./... -v
    - Spring Boot: ./gradlew test
    - NestJS/Express: npx jest --no-cache
    """
    lang = service.language
    print(
        f"\n{BOLD}{step_label} Running tests ({lang} - {service.name})..."
        f"{RESET}"
    )

    project_root = get_project_root()
    error_output = "Unknown error"

    for attempt in range(MAX_TEST_FIX_ATTEMPTS + 1):
        print(
            f"  {DIM}Running tests "
            f"(attempt {attempt + 1}/{MAX_TEST_FIX_ATTEMPTS + 1})...{RESET}"
        )
        print(f"  {DIM}Command: {service.test}{RESET}")

        success, output = _run_service_command(
            service.test, service, timeout=300
        )

        if success:
            state.update(test_passed=True)
            print(f"  {GREEN}OK{RESET} Tests passed")
            return True

        error_output = output[:2000]
        print(f"  {RED}FAIL{RESET} Tests failed")
        print(f"  {DIM}{error_output[:200]}{RESET}")

        if attempt < MAX_TEST_FIX_ATTEMPTS:
            state.update(test_retry_count=attempt + 1)
            state.save()
            print(
                f"  {YELLOW}-> Invoking fix-tests "
                f"(attempt {attempt + 1})...{RESET}"
            )
            fix_output = os.path.join(
                state.get_state_dir(),
                f"fix_tests_attempt_{attempt + 1}",
                "raw_output.jsonl",
            )
            fix_prompt = (
                f"Fix the following test failure in the {lang} service "
                f"at {service.path}. Test command: `{service.test}`. "
                f"Error output:\n\n{error_output}"
            )
            fix_request = AgentPromptRequest(
                prompt=fix_prompt,
                allowed_tools=[
                    "Read", "Edit", "Write", "Glob", "Grep", "Bash",
                ],
                timeout_seconds=300,
            )
            prompt_with_retry(
                fix_request, project_root, fix_output, max_retries=0
            )

    state.update(test_passed=False, test_errors=error_output)
    return False


def phase_lint(state, step_label: str, service: ServiceConfig) -> bool:
    """Run language-aware linting.

    Lint commands by language:
    - Go: golangci-lint run ./...
    - Spring Boot: (skip - no standard linter)
    - NestJS/Express: npx eslint .
    """
    lang = service.language
    print(
        f"\n{BOLD}{step_label} Linting ({lang} - {service.name})...{RESET}"
    )

    if not service.lint:
        print(f"  {DIM}No lint command configured, skipping{RESET}")
        state.update(lint_passed=True)
        return True

    print(f"  {DIM}Command: {service.lint}{RESET}")

    success, output = _run_service_command(
        service.lint, service, timeout=120
    )

    if success:
        state.update(lint_passed=True)
        print(f"  {GREEN}OK{RESET} Lint passed")
        return True
    else:
        error_output = output[:2000]
        state.update(lint_passed=False, lint_errors=error_output)
        print(f"  {RED}FAIL{RESET} Lint failed")
        print(f"  {DIM}{error_output[:300]}{RESET}")
        # Lint failure is non-blocking - warn but continue
        print(
            f"  {YELLOW}WARNING{RESET} Lint issues found, "
            f"continuing pipeline"
        )
        return True


def phase_commit(
    state, step_label: str, commit_type: str
) -> bool:
    """Commit changes with conventional commit message.

    Args:
        state: BackendWorkflowState instance.
        step_label: Display label like "[9/10]".
        commit_type: Conventional commit type (feat, chore, fix).
    """
    print(f"\n{BOLD}{step_label} Committing changes...{RESET}")

    name = (
        state.data.name[0].lower() + state.data.name[1:]
        if state.data.name
        else ""
    )
    scope = state.data.service_name or state.data.ticket_id.lower()
    commit_msg = f"{commit_type}({scope}): {name}"

    success, result = commit_changes(commit_msg)

    if success:
        state.update(commit_hash=result)
        print(f"  {GREEN}OK{RESET} Committed: {commit_msg}")
        print(f"\n{DIM}{get_diff_stat()}{RESET}")
        return True
    elif "nothing to commit" in result:
        print(
            f"  {YELLOW}WARNING{RESET} Nothing to commit "
            "- changes already committed"
        )
        return True
    else:
        print(f"  {RED}FAIL{RESET} {result}")
        return False


def phase_pr(
    state,
    step_label: str,
    commit_type: str,
    build_pr_description: Callable,
) -> bool:
    """Push and create Pull Request.

    Args:
        state: BackendWorkflowState instance.
        step_label: Display label like "[10/10]".
        commit_type: Conventional commit type.
        build_pr_description: Callable(state) -> str that builds the PR body.
    """
    print(f"\n{BOLD}{step_label} Creating Pull Request...{RESET}")

    # Push branch
    success, result = push_branch(state.data.branch_name)
    if not success:
        print(f"  {RED}FAIL{RESET} Push failed: {result}")
        return False

    print(f"  {GREEN}OK{RESET} Pushed branch")

    # Create PR
    name = (
        state.data.name[0].lower() + state.data.name[1:]
        if state.data.name
        else ""
    )
    scope = state.data.service_name or state.data.ticket_id.lower()
    title = f"{commit_type}({scope}): {name}"
    description = build_pr_description(state)

    success, result = create_pr(title, description)

    if success:
        state.update(pr_url=result, pr_created=True)
        print(f"  {GREEN}OK{RESET} PR created: {result}")
        return True
    else:
        print(f"  {YELLOW}WARNING{RESET} PR creation failed: {result}")
        return True  # Don't fail pipeline for PR issues


def phase_clickup_fetch(
    state, step_label: str, cli_description: str = ""
) -> bool:
    """Fetch task from ClickUp and populate state.

    Moves ticket to "in progress". Non-fatal if fetch fails and
    cli_description is available as fallback.
    """
    print(f"\n{BOLD}{step_label} Fetching ClickUp task...{RESET}")

    token = os.environ.get("CLICKUP_API_TOKEN", "")
    if not token:
        if cli_description:
            print(
                f"  {YELLOW}WARNING{RESET} CLICKUP_API_TOKEN not set, "
                "using CLI description"
            )
            state.update(name=cli_description, description=cli_description)
            state.save()
            return True
        print(
            f"  {RED}FAIL{RESET} CLICKUP_API_TOKEN not set "
            "and no description provided"
        )
        return False

    success, task = fetch_task(state.data.ticket_id)

    if not success:
        if cli_description:
            print(
                f"  {YELLOW}WARNING{RESET} ClickUp fetch failed, "
                "using CLI description"
            )
            state.update(name=cli_description, description=cli_description)
            state.save()
            return True
        print(
            f"  {RED}FAIL{RESET} ClickUp fetch failed "
            "and no description provided"
        )
        return False

    # Populate state from ClickUp data
    state.update(
        name=cli_description if cli_description else task.name,
        description=cli_description if cli_description else task.description,
        clickup_task_id=task.task_id,
        clickup_task_url=task.url,
        clickup_tags=task.tags,
        clickup_custom_fields=task.custom_fields,
    )
    state.save()

    print(f"  {GREEN}OK{RESET} Task: {task.name}")
    print(f"  {DIM}URL: {task.url}{RESET}")

    # Move to "in progress" (non-fatal)
    ok, msg = update_task_status(state.data.clickup_task_id, "in progress")
    if ok:
        print(f"  {GREEN}OK{RESET} Status -> in progress")
    else:
        print(f"  {YELLOW}WARNING{RESET} Could not update status: {msg}")

    return True


def post_pr_clickup_update(state) -> None:
    """Post-PR: add comment with PR link and move to review.

    Non-fatal - only prints warnings on failure.
    """
    if not state.data.clickup_task_id:
        return

    token = os.environ.get("CLICKUP_API_TOKEN", "")
    if not token:
        return

    task_id = state.data.clickup_task_id

    # Add comment with PR URL
    if state.data.pr_url:
        comment = f"PR created: {state.data.pr_url}"
        ok, msg = add_task_comment(task_id, comment)
        if ok:
            print(f"  {GREEN}OK{RESET} ClickUp comment added")
        else:
            print(f"  {YELLOW}WARNING{RESET} ClickUp comment failed: {msg}")

    # Move to "in review"
    ok, msg = update_task_status(task_id, "in review")
    if ok:
        print(f"  {GREEN}OK{RESET} ClickUp status -> in review")
    else:
        print(
            f"  {YELLOW}WARNING{RESET} ClickUp status update failed: {msg}"
        )


# ---------------------------------------------------------------------------
# Shared utilities
# ---------------------------------------------------------------------------

PHASE_DEPS = {
    "evaluate": ("plan_file", "plan"),
    "apply": ("evaluation_files", "evaluate"),
    "implement": ("plan_file", "plan"),
}


def validate_phase_deps(state, phase_name: str) -> None:
    """Warn if a phase's required state fields are missing."""
    if phase_name not in PHASE_DEPS:
        return
    field, source_phase = PHASE_DEPS[phase_name]
    value = getattr(state.data, field, None)
    if not value:
        print(
            f"  {YELLOW}WARNING{RESET} Phase '{phase_name}' expects "
            f"'{field}' from '{source_phase}' phase, but it is empty"
        )


def phase_branch(
    state, step_label: str, branch_type: str = "feat"
) -> bool:
    """Create a git branch from develop."""
    print(f"\n{BOLD}{step_label} Creating branch...{RESET}")

    success, result = create_branch(
        ticket_id=state.data.ticket_id,
        description=state.data.name,
        branch_type=branch_type,
    )

    if success:
        state.update(branch_name=result)
        state.save()
        print(f"  {GREEN}OK{RESET} Branch: {result}")
        return True
    else:
        print(f"  {RED}FAIL{RESET} {result}")
        return False


def build_pr_description_fn(state, pipeline_type: str) -> str:
    """Build a unified PR description for any pipeline type."""
    ticket_section = state.data.ticket_id
    if state.data.clickup_task_url:
        ticket_section = (
            f"[{state.data.ticket_id}]({state.data.clickup_task_url})"
        )

    eval_line = ""
    if state.data.evaluation_score is not None:
        eval_line = (
            f"- [x] Architecture evaluation: "
            f"{state.data.evaluation_score}/50\n"
        )

    service_line = ""
    if state.data.service_name:
        service_line = (
            f"\n## Service\n\n"
            f"- Name: `{state.data.service_name}`\n"
            f"- Language: `{state.data.service_language}`\n"
            f"- Path: `{state.data.service_path}`\n"
        )

    security_line = ""
    if state.data.security_passed is not None:
        status = "passed" if state.data.security_passed else "issues found"
        security_line = f"- [x] Security check: {status}\n"

    lint_line = ""
    if state.data.lint_passed is not None:
        status = "passed" if state.data.lint_passed else "warnings"
        lint_line = f"- [x] Lint: {status}\n"

    # Language-specific validation labels
    lang = state.data.service_language
    build_label = {
        "go": "`go build ./...`",
        "spring-boot": "`./gradlew build`",
        "nestjs": "`npx tsc --noEmit`",
        "express": "`npx tsc --noEmit`",
    }.get(lang, "build")

    test_label = {
        "go": "`go test ./...`",
        "spring-boot": "`./gradlew test`",
        "nestjs": "`npx jest --no-cache`",
        "express": "`npx jest --no-cache`",
    }.get(lang, "test")

    return f"""## Summary

{state.data.description}

## ClickUp Task

{ticket_section}
{service_line}
## Validation

- [x] Build: {build_label} passed
- [x] Tests: {test_label} passed
{lint_line}{eval_line}{security_line}
## Plan Reference

`{state.data.plan_file}`

---
Generated by AI Workflow Pipeline ({pipeline_type})
"""


def print_timing_summary(
    phase_timings: List[Tuple[str, float, bool]],
    pipeline_start: float,
) -> None:
    """Print a table with per-phase durations and status."""
    import time as _time

    total = _time.time() - pipeline_start
    print(f"\n{BOLD}Phase Timing Summary{RESET}")
    print(f"{'_' * 45}")
    for name, duration, ok in phase_timings:
        status = f"{GREEN}OK{RESET}" if ok else f"{RED}FAIL{RESET}"
        print(
            f"  {name:<20} {format_duration(duration):>8}  {status}"
        )
    print(f"{'_' * 45}")
    print(f"  {'TOTAL':<20} {format_duration(total):>8}")


def print_state_summary(state, pipeline_type: str) -> None:
    """Print a compact state overview at pipeline start/end."""
    d = state.data
    completed = (
        ", ".join(d.phases_completed) if d.phases_completed else "none"
    )
    print(f"\n{BOLD}State Summary{RESET}")
    print(f"  ID:          {d.workflow_id}")
    print(f"  Type:        {pipeline_type}")
    print(f"  Ticket:      {d.ticket_id}")
    print(f"  Service:     {d.service_name} ({d.service_language})")
    print(f"  Description: {(d.description or '')[:60]}")
    if d.plan_file:
        print(f"  Plan:        {d.plan_file}")
    if d.evaluation_score is not None:
        print(f"  Eval score:  {d.evaluation_score}/50")
    print(f"  Completed:   {completed}")
    print(f"  Current:     {d.current_phase}")


def cleanup_orphan_node_processes() -> None:
    """Kill orphan node processes left by Claude agent sessions."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "node.*claude"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        pids = result.stdout.strip().split("\n")
        pids = [p.strip() for p in pids if p.strip()]
        if pids:
            for pid in pids:
                try:
                    os.kill(int(pid), 15)  # SIGTERM
                except (ProcessLookupError, ValueError, OSError):
                    pass
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
