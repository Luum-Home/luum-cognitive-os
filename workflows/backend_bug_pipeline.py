"""
Backend Bug Pipeline - Orchestrator for bug fixes in any backend service.

Usage:
  uv run .cognitive-os/workflows/run.py bug --service <consumer-service-2> --ticket BUG-567
  uv run .cognitive-os/workflows/run.py bug --service <consumer-codename-a> --ticket BUG-567 --description "Fix auth token"

Phases (11 steps):
  1. fetch      - Fetch task from ClickUp
  2. branch     - Create fix branch from develop
  3. plan       - Generate bug resolution plan
  4. evaluate   - Score plan (soft gate)
  5. apply      - Fix plan if needed
  6. implement  - Write fix
  7. build      - Compile (language-aware)
  8. test       - Run tests (language-aware)
  9. security   - Security check (constitutional gates)
  10. commit    - Git commit (fix type)
  11. pr        - Create PR + update ClickUp
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend_state import BackendWorkflowState, setup_logger
from lib.shared_phases import (
    BOLD,
    CYAN,
    DIM,
    GREEN,
    RED,
    RESET,
    YELLOW,
    build_pr_description_fn,
    cleanup_orphan_node_processes,
    format_duration,
    phase_branch,
    phase_build,
    phase_clickup_fetch,
    phase_commit,
    phase_pr,
    phase_test,
    post_pr_clickup_update,
    print_state_summary,
    print_timing_summary,
    validate_phase_deps,
)
from lib.telegram import (
    notify_phase_failure,
    notify_phase_success,
    notify_pipeline_complete,
)
from lib.utils import get_service_config, make_workflow_id
from phases import (
    phase_apply,
    phase_evaluate,
    phase_implement,
    phase_plan,
    phase_security_check,
)


def run_pipeline(
    ticket_id: str,
    service_name: str,
    description: str = "",
    resume_id: str = None,
    start_from: str = None,
    skip_evaluate: bool = False,
) -> bool:
    """Run the bug fix pipeline for a backend service."""

    service = get_service_config(service_name) if service_name else None
    if not service and not resume_id:
        print(f"{RED}Unknown service: {service_name}{RESET}")
        return False

    if resume_id:
        state = BackendWorkflowState.load(resume_id)
        if not state:
            print(f"{RED}Could not load workflow: {resume_id}{RESET}")
            return False
        workflow_id = resume_id
        if not service:
            service = get_service_config(state.data.service_name)
    else:
        workflow_id = make_workflow_id()
        state = BackendWorkflowState(
            workflow_id=workflow_id,
            workflow_type="bug",
            ticket_id=ticket_id,
            name=description if description else "bug fix",
            service_name=service.name,
            service_path=service.path,
            service_language=service.language,
        )
        state.update(description=description or "")

    cli_description = description or ""
    logger = setup_logger(workflow_id)

    print(f"\n{BOLD}{'=' * 50}{RESET}")
    print(f"{BOLD}Backend Bug Fix Pipeline{RESET}")
    print(f"{DIM}Workflow ID: {workflow_id}{RESET}")
    print(f"{DIM}Ticket: {state.data.ticket_id}{RESET}")
    print(f"{DIM}Service: {state.data.service_name} ({state.data.service_language}){RESET}")
    print(f"{BOLD}{'=' * 50}{RESET}")

    print_state_summary(state, "bug")

    phase_defs = [
        (
            "fetch",
            lambda s, step: phase_clickup_fetch(s, step, cli_description),
        ),
        (
            "branch",
            lambda s, step: phase_branch(s, step, branch_type="fix"),
        ),
        ("plan", phase_plan),
        ("evaluate", phase_evaluate),
        ("apply", phase_apply),
        ("implement", phase_implement),
        ("build", lambda s, step: phase_build(s, step, service)),
        ("test", lambda s, step: phase_test(s, step, service)),
        (
            "security",
            lambda s, step: phase_security_check(s, step, service),
        ),
        (
            "commit",
            lambda s, step: phase_commit(s, step, "fix"),
        ),
        (
            "pr",
            lambda s, step: phase_pr(
                s,
                step,
                "fix",
                lambda st: build_pr_description_fn(st, "bug"),
            ),
        ),
    ]

    if skip_evaluate:
        phase_defs = [
            (n, f)
            for n, f in phase_defs
            if n not in ("evaluate", "apply")
        ]

    total = len(phase_defs)
    phases = [
        (
            name,
            lambda s, _fn=fn, _step=f"[{i}/{total}]": _fn(s, _step),
        )
        for i, (name, fn) in enumerate(phase_defs, 1)
    ]

    if start_from:
        phase_names = [p[0] for p in phases]
        if start_from in phase_names:
            idx = phase_names.index(start_from)
            phases = phases[idx:]

    pipeline_start = time.time()
    phase_timings = []

    for phase_name, phase_fn in phases:
        if phase_name in state.data.phases_completed:
            print(f"\n{DIM}Skipping {phase_name} (already completed){RESET}")
            continue

        validate_phase_deps(state, phase_name)
        state.update(current_phase=phase_name)
        state.save()

        phase_start = time.time()
        success = phase_fn(state)
        phase_duration = time.time() - phase_start
        phase_timings.append((phase_name, phase_duration, success))

        cleanup_orphan_node_processes()

        if success:
            state.mark_phase_completed(phase_name)
            state.save()
            logger.info(
                f"Phase {phase_name} completed in "
                f"{format_duration(phase_duration)}"
            )
            notify_phase_success(
                "bug", workflow_id, phase_name,
                state.data.ticket_id, service=state.data.service_name,
            )
        else:
            logger.error(f"Phase {phase_name} failed")
            print(f"\n{RED}Pipeline failed at phase: {phase_name}{RESET}")
            print(
                f"{DIM}Resume: uv run .cognitive-os/workflows/run.py "
                f"resume --workflow-id {workflow_id}{RESET}"
            )
            print_timing_summary(phase_timings, pipeline_start)
            notify_phase_failure(
                "bug", workflow_id, phase_name,
                state.data.ticket_id, service=state.data.service_name,
            )
            return False

    post_pr_clickup_update(state)
    total_duration = time.time() - pipeline_start

    print_timing_summary(phase_timings, pipeline_start)
    print(f"\n{GREEN}Pipeline complete!{RESET}")
    if state.data.pr_url:
        print(f"{CYAN}PR: {state.data.pr_url}{RESET}")

    notify_pipeline_complete(
        "bug", workflow_id,
        pr_url=state.data.pr_url or "",
        duration=format_duration(total_duration),
        ticket_id=state.data.ticket_id,
        service=state.data.service_name,
    )

    return True
