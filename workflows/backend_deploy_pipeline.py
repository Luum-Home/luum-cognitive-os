"""
Backend Deploy Pipeline - Deployment workflow for backend services.

Usage:
  uv run .cognitive-os/workflows/run.py deploy --service accounts-go --env staging
  uv run .cognitive-os/workflows/run.py deploy --service <consumer-codename-a> --env prod

Phases (5 steps):
  1. build      - Compile service (language-aware)
  2. test       - Run tests (language-aware)
  3. security   - Security validation
  4. docker     - Docker build + push
  5. deploy     - K8s apply or ArgoCD sync + health check
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend_state import BackendWorkflowState, setup_logger
from lib.shared_phases import (
    BOLD,
    DIM,
    GREEN,
    RED,
    RESET,
    cleanup_orphan_node_processes,
    format_duration,
    phase_build,
    phase_test,
    print_timing_summary,
)
from lib.telegram import (
    notify_phase_failure,
    notify_phase_success,
    notify_pipeline_complete,
)
from lib.utils import get_service_config, make_workflow_id
from phases import phase_deploy, phase_security_check


def run_pipeline(
    service_name: str,
    env_name: str,
    resume_id: str = None,
    start_from: str = None,
) -> bool:
    """Run the deployment pipeline."""

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
            workflow_type="deploy",
            name=f"Deploy {service_name} to {env_name}",
            service_name=service.name,
            service_path=service.path,
            service_language=service.language,
        )
        state.update(
            deploy_env=env_name,
            description=f"Deploy {service_name} to {env_name}",
        )

    logger = setup_logger(workflow_id)

    print(f"\n{BOLD}{'=' * 50}{RESET}")
    print(f"{BOLD}Backend Deploy Pipeline{RESET}")
    print(f"{DIM}Workflow ID: {workflow_id}{RESET}")
    print(f"{DIM}Service: {state.data.service_name} ({state.data.service_language}){RESET}")
    print(f"{DIM}Environment: {state.data.deploy_env}{RESET}")
    print(f"{BOLD}{'=' * 50}{RESET}")

    phase_defs = [
        ("build", lambda s, step: phase_build(s, step, service)),
        ("test", lambda s, step: phase_test(s, step, service)),
        (
            "security",
            lambda s, step: phase_security_check(s, step, service),
        ),
        (
            "deploy",
            lambda s, step: phase_deploy(
                s, step, service, state.data.deploy_env
            ),
        ),
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
                "deploy", workflow_id, phase_name,
                service=state.data.service_name,
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
                "deploy", workflow_id, phase_name,
                service=state.data.service_name,
            )
            return False

    total_duration = time.time() - pipeline_start
    print_timing_summary(phase_timings, pipeline_start)
    print(f"\n{GREEN}Deploy pipeline complete!{RESET}")
    print(f"{DIM}Duration: {format_duration(total_duration)}{RESET}")

    notify_pipeline_complete(
        "deploy", workflow_id,
        duration=format_duration(total_duration),
        service=state.data.service_name,
    )

    return True
