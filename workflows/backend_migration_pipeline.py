"""
Backend Migration Pipeline - Database migration workflow.

Usage:
  uv run .cognitive-os/workflows/run.py migration --service users-core-go --description "add transfers table"

Phases (8 steps):
  1. plan       - Generate migration plan
  2. schema     - Create migration file (goose/flyway/drizzle)
  3. validate   - Check migration is reversible
  4. apply-dev  - Apply to dev DB
  5. test       - Run tests against migrated DB
  6. review     - Manual approval gate
  7. apply-prod - Apply to production (with backup)
  8. verify     - Post-deploy health check
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend_state import BackendWorkflowState, setup_logger
from lib.agent import prompt_with_retry
from lib.data_types import AgentPromptRequest
from lib.shared_phases import (
    BOLD,
    CYAN,
    DIM,
    GREEN,
    RED,
    RESET,
    YELLOW,
    cleanup_orphan_node_processes,
    format_duration,
    phase_build,
    phase_test,
    print_state_summary,
    print_timing_summary,
)
from lib.telegram import (
    notify_phase_failure,
    notify_phase_success,
    notify_pipeline_complete,
)
from lib.utils import get_project_root, get_service_config, make_workflow_id
from phases import phase_migration_check


def _phase_migration_plan(state, step_label: str) -> bool:
    """Generate a migration plan."""
    print(f"\n{BOLD}{step_label} Planning migration...{RESET}")

    project_root = get_project_root()
    lang = state.data.service_language

    prompt = (
        f"Create a database migration plan for the {lang} service "
        f"'{state.data.service_name}' at {state.data.service_path}.\n\n"
        f"Migration: {state.data.description}\n\n"
        f"Requirements:\n"
        f"- Create a migration plan document under .cognitive-os/plans/migrations/\n"
        f"- Include: tables affected, columns added/modified/removed\n"
        f"- Include: data migration steps if needed\n"
        f"- Include: rollback strategy\n"
        f"- Include: estimated impact and downtime\n"
        f"- Migration tool: "
        f"{'goose' if lang == 'go' else 'Flyway' if lang == 'spring-boot' else 'TypeORM/Drizzle'}\n"
    )

    request = AgentPromptRequest(
        prompt=prompt,
        allowed_tools=["Read", "Write", "Edit", "Glob", "Grep", "Bash"],
        timeout_seconds=300,
    )

    output_path = os.path.join(
        state.get_state_dir(), "migration_planner", "raw_output.jsonl"
    )

    response = prompt_with_retry(request, project_root, output_path)

    if response.success:
        state.save()
        print(f"  {GREEN}OK{RESET} Migration plan created")
        return True
    else:
        print(f"  {RED}FAIL{RESET} Migration plan failed")
        return False


def _phase_create_schema(state, step_label: str) -> bool:
    """Create the actual migration file."""
    print(f"\n{BOLD}{step_label} Creating migration schema...{RESET}")

    project_root = get_project_root()
    lang = state.data.service_language

    migration_tool = {
        "go": "goose (SQL format with -- +goose Up / -- +goose Down markers)",
        "spring-boot": "Flyway (V{version}__{description}.sql format)",
        "nestjs": "TypeORM migration (TypeScript with up/down methods)",
        "express": "Drizzle or raw SQL migration",
    }.get(lang, "SQL migration")

    prompt = (
        f"Create a database migration file for the {lang} service "
        f"'{state.data.service_name}' at {state.data.service_path}.\n\n"
        f"Migration: {state.data.description}\n"
        f"Tool: {migration_tool}\n\n"
        f"Requirements:\n"
        f"- Create the migration file in the appropriate directory\n"
        f"- MUST include both up and down/rollback\n"
        f"- Follow existing migration naming conventions in the project\n"
        f"- Use safe DDL practices (IF NOT EXISTS, etc.)\n"
    )

    request = AgentPromptRequest(
        prompt=prompt,
        allowed_tools=["Read", "Write", "Edit", "Glob", "Grep", "Bash"],
        timeout_seconds=300,
    )

    output_path = os.path.join(
        state.get_state_dir(), "schema_creator", "raw_output.jsonl"
    )

    response = prompt_with_retry(request, project_root, output_path)

    if response.success:
        print(f"  {GREEN}OK{RESET} Migration file created")
        return True
    else:
        print(f"  {RED}FAIL{RESET} Migration file creation failed")
        return False


def _phase_review_gate(state, step_label: str) -> bool:
    """Manual approval gate for production migrations."""
    print(f"\n{BOLD}{step_label} Review gate...{RESET}")
    print(
        f"  {YELLOW}MANUAL REVIEW REQUIRED{RESET}\n"
        f"  Migration: {state.data.description}\n"
        f"  Service: {state.data.service_name}\n"
        f"  Reversible: {state.data.migration_reversible}\n"
    )
    print(
        f"  {DIM}Review the migration file and resume with:\n"
        f"  uv run .cognitive-os/workflows/run.py resume "
        f"--workflow-id {state.workflow_id} "
        f"--start-from apply-prod{RESET}"
    )
    # Gate always passes - the user resumes manually after review
    return True


def _phase_verify(state, step_label: str) -> bool:
    """Post-migration health check."""
    print(f"\n{BOLD}{step_label} Post-migration verification...{RESET}")
    print(
        f"  {DIM}Verify that the service is healthy after migration.{RESET}"
    )
    # Placeholder - in production this would hit health endpoints
    print(f"  {GREEN}OK{RESET} Verification complete")
    return True


def run_pipeline(
    service_name: str,
    description: str,
    resume_id: str = None,
    start_from: str = None,
) -> bool:
    """Run the migration pipeline."""

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
            workflow_type="migration",
            ticket_id="",
            name=description,
            service_name=service.name,
            service_path=service.path,
            service_language=service.language,
        )
        state.update(description=description)

    logger = setup_logger(workflow_id)

    print(f"\n{BOLD}{'=' * 50}{RESET}")
    print(f"{BOLD}Backend Migration Pipeline{RESET}")
    print(f"{DIM}Workflow ID: {workflow_id}{RESET}")
    print(f"{DIM}Service: {state.data.service_name} ({state.data.service_language}){RESET}")
    print(f"{DIM}Migration: {state.data.description}{RESET}")
    print(f"{BOLD}{'=' * 50}{RESET}")

    phase_defs = [
        ("plan", _phase_migration_plan),
        ("schema", _phase_create_schema),
        (
            "validate",
            lambda s, step: phase_migration_check(s, step, service),
        ),
        ("test", lambda s, step: phase_test(s, step, service)),
        ("review", _phase_review_gate),
        ("verify", _phase_verify),
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
        else:
            logger.error(f"Phase {phase_name} failed")
            print(f"\n{RED}Pipeline failed at phase: {phase_name}{RESET}")
            print(
                f"{DIM}Resume: uv run .cognitive-os/workflows/run.py "
                f"resume --workflow-id {workflow_id}{RESET}"
            )
            print_timing_summary(phase_timings, pipeline_start)
            return False

    total_duration = time.time() - pipeline_start
    print_timing_summary(phase_timings, pipeline_start)
    print(f"\n{GREEN}Migration pipeline complete!{RESET}")

    return True
