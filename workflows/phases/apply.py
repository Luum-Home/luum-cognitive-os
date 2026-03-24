"""Phase executor: Apply evaluation findings to plan."""

import os

from lib.agent import prompt_with_retry
from lib.data_types import AgentPromptRequest
from lib.shared_phases import BOLD, DIM, GREEN, RED, RESET, YELLOW
from lib.utils import get_project_root


def phase_apply(state, step_label: str) -> bool:
    """Apply evaluation findings to the plan.

    Only applies the most recent evaluation file to avoid redundant work.
    """
    print(f"\n{BOLD}{step_label} Applying evaluation findings...{RESET}")

    if not state.data.evaluation_files:
        print(
            f"  {YELLOW}WARNING{RESET} No evaluation files to apply "
            f"(skipping)"
        )
        return True

    project_root = get_project_root()

    # Only apply the most recent evaluation
    eval_file = state.data.evaluation_files[0]

    if len(state.data.evaluation_files) > 1:
        print(
            f"  {DIM}Found {len(state.data.evaluation_files)} evaluations, "
            f"applying only the most recent{RESET}"
        )

    print(f"  {DIM}Applying: {eval_file}{RESET}")

    prompt = (
        f"Read the evaluation at {eval_file} and apply its suggestions "
        f"to improve the plan at {state.data.plan_file}. "
        f"Focus on addressing any NEEDS_REVISION items and improving "
        f"the overall score. Update the plan file in place."
    )

    request = AgentPromptRequest(
        prompt=prompt,
        allowed_tools=["Read", "Edit", "Write", "Glob", "Grep"],
        timeout_seconds=300,
    )

    output_path = os.path.join(
        state.get_state_dir(), "applier", "raw_output.jsonl"
    )

    response = prompt_with_retry(
        request, project_root, output_path, max_retries=1
    )

    if response.success:
        print(f"  {GREEN}OK{RESET} Applied: {eval_file}")
    else:
        print(
            f"  {YELLOW}WARNING{RESET} Apply failed for {eval_file} "
            f"(continuing): {response.output[:100]}"
        )

    state.save()
    return True
