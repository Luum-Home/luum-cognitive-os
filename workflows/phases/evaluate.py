"""Phase executor: Evaluation gate (soft gate, score 0-50).

Always passes so that the apply phase can run and fix the plan.
The score is stored for reporting but does not block the pipeline.
"""

import os
import time

from lib.agent import prompt_with_retry
from lib.data_types import AgentPromptRequest
from lib.file_parser import extract_evaluation_info
from lib.shared_phases import BOLD, DIM, GREEN, RED, RESET, YELLOW
from lib.utils import get_project_root

# Only consider evaluation files created in the last N seconds
_EVAL_MAX_AGE_SECONDS = 600  # 10 minutes


def phase_evaluate(state, step_label: str) -> bool:
    """Evaluate the plan with a soft gate (0-50 score).

    Stores score and all evaluation files for the apply phase.
    Always returns True so apply can run.
    """
    print(f"\n{BOLD}{step_label} Evaluating plan...{RESET}")

    if not state.data.plan_file:
        print(f"  {RED}FAIL{RESET} No plan file found")
        return False

    project_root = get_project_root()
    lang = state.data.service_language

    prompt = (
        f"Evaluate the following implementation plan for a {lang} backend "
        f"service. Score it from 0 to 50 based on:\n"
        f"- Completeness (0-10): Are all steps covered?\n"
        f"- Architecture (0-10): Does it follow service patterns?\n"
        f"- Security (0-10): Constitutional gates compliance?\n"
        f"- Testability (0-10): Is the test strategy adequate?\n"
        f"- Risk (0-10): Are risks and rollback addressed?\n\n"
        f"Plan file: {state.data.plan_file}\n\n"
        f"Write the evaluation to .cognitive-os/plans/evaluations/ as a markdown file with:\n"
        f"- **Overall Rating:** X/50\n"
        f"- **Status:** APPROVED or NEEDS_REVISION\n"
        f"- **Plan File:** `{state.data.plan_file}`\n"
        f"- Detailed feedback per category\n"
        f"- Specific improvement suggestions if score < 25"
    )

    request = AgentPromptRequest(
        prompt=prompt,
        allowed_tools=["Read", "Write", "Glob", "Grep"],
        timeout_seconds=600,
    )

    output_path = os.path.join(
        state.get_state_dir(), "evaluator", "raw_output.jsonl"
    )

    response = prompt_with_retry(request, project_root, output_path)

    if not response.success:
        print(
            f"  {YELLOW}WARNING{RESET} Evaluation agent failed "
            f"(continuing to apply): {response.output[:100]}"
        )
        return True

    # Collect evaluation files
    eval_dir = os.path.join(project_root, ".cognitive-os", "workflows", ".cognitive-os", "plans", "evaluations")
    if not os.path.exists(eval_dir):
        eval_dir = os.path.join(project_root, ".cognitive-os", "plans", "evaluations")
    if not os.path.exists(eval_dir):
        print(f"  {YELLOW}WARNING{RESET} No evaluation directory found")
        return True

    # Extract plan name to filter evaluation files
    plan_name = os.path.splitext(
        os.path.basename(state.data.plan_file)
    )[0]

    now = time.time()
    matching_files = sorted(
        [
            f
            for f in os.listdir(eval_dir)
            if f.endswith(".md")
            and (now - os.path.getmtime(os.path.join(eval_dir, f)))
            <= _EVAL_MAX_AGE_SECONDS
        ],
        reverse=True,
    )

    if not matching_files:
        print(
            f"  {YELLOW}WARNING{RESET} No evaluation files found "
            f"for plan '{plan_name}'"
        )
        return True

    # Parse score from the most recent evaluation file
    score = None
    verdict = None
    for eval_file in matching_files:
        eval_path = os.path.join(eval_dir, eval_file)
        info = extract_evaluation_info(eval_path)
        if info.get("score") is not None:
            score = info["score"]
            verdict = info.get("verdict")
            break

    eval_relative_paths = [
        os.path.join(".cognitive-os/plans/evaluations", f) for f in matching_files
    ]

    state.update(
        evaluation_files=eval_relative_paths,
        evaluation_score=score,
        evaluation_verdict=verdict,
    )
    state.save()

    display_score = score if score is not None else "?"
    display_verdict = verdict or "UNKNOWN"
    print(f"  Score: {display_score}/50 - {display_verdict}")
    print(
        f"  {DIM}Evaluation files: {len(matching_files)}{RESET}"
    )

    if score is not None and score >= 25:
        print(f"  {GREEN}OK{RESET} Evaluation passed")
    elif score is not None:
        print(
            f"  {YELLOW}WARNING{RESET} Low score ({score}/50), "
            f"apply phase will fix the plan"
        )
    else:
        print(
            f"  {YELLOW}WARNING{RESET} Could not parse score, "
            f"apply phase will still run"
        )

    return True
