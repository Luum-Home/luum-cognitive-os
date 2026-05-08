"""Phase executor: Planning for backend services."""

import os
import time

from lib.agent import prompt_with_retry
from lib.data_types import AgentPromptRequest
from lib.file_parser import extract_plan_file
from lib.shared_phases import BOLD, GREEN, RED, RESET
from lib.utils import get_project_root

# Max age in seconds for a plan file to be considered "just created"
_PLAN_MAX_AGE_SECONDS = 300  # 5 minutes


def phase_plan(state, step_label: str) -> bool:
    """Create a plan for the backend service change.

    Generates a plan using Claude Code, adapted for the service's language
    and architecture. The plan is stored under .cognitive-os/plans/ in a subdirectory
    matching the workflow type.
    """
    print(f"\n{BOLD}{step_label} Creating plan...{RESET}")

    project_root = get_project_root()
    wtype = state.data.workflow_type
    lang = state.data.service_language
    service = state.data.service_name

    # Build a context-rich planning prompt
    plan_dirs = {
        "feature": ".cognitive-os/plans/features",
        "bug": ".cognitive-os/plans/bugs",
        "migration": ".cognitive-os/plans/migrations",
        "deploy": ".cognitive-os/plans/deployments",
    }
    rel_dir = plan_dirs.get(wtype, ".cognitive-os/plans/features")

    prompt = (
        f"Create a detailed implementation plan for the following {wtype} "
        f"in the {lang} service '{service}' at path {state.data.service_path}.\n\n"
        f"Ticket: {state.data.ticket_id}\n"
        f"Description: {state.data.description}\n\n"
        f"Requirements:\n"
        f"- Write the plan as a markdown file under {rel_dir}/\n"
        f"- Include: goal, affected files, implementation steps, "
        f"test strategy, rollback plan\n"
        f"- Consider the service language ({lang}) for build/test commands\n"
        f"- Follow project constitutional gates (security, idempotency, "
        f"audit trail for financial ops)\n"
        f"- Reference existing patterns in the codebase\n\n"
        f"Save the plan file and output its path."
    )

    request = AgentPromptRequest(
        prompt=prompt,
        allowed_tools=[
            "Read", "Write", "Edit", "Glob", "Grep", "Bash",
        ],
        timeout_seconds=300,
    )

    output_path = os.path.join(
        state.get_state_dir(), "planner", "raw_output.jsonl"
    )

    response = prompt_with_retry(request, project_root, output_path)

    if response.success:
        # Try to extract the plan file path
        plan_file = extract_plan_file(response.output, output_path)
        if plan_file:
            state.update(plan_file=plan_file)
        else:
            # Fallback: search for recently created plan files
            plan_dir = os.path.join(project_root, rel_dir)
            now = time.time()
            if os.path.exists(plan_dir):
                for f in sorted(os.listdir(plan_dir)):
                    if not f.endswith(".md"):
                        continue
                    full = os.path.join(plan_dir, f)
                    age = now - os.path.getmtime(full)
                    if age <= _PLAN_MAX_AGE_SECONDS:
                        state.update(
                            plan_file=os.path.join(rel_dir, f)
                        )
                        break

        if not state.data.plan_file:
            print(
                f"  {RED}FAIL{RESET} Could not resolve plan file. "
                f"No recently created plan found in {rel_dir}/"
            )
            return False

        state.save()
        print(
            f"  {GREEN}OK{RESET} Plan created: {state.data.plan_file}"
        )
        return True
    else:
        print(
            f"  {RED}FAIL{RESET} Plan failed: {response.output[:100]}"
        )
        return False
