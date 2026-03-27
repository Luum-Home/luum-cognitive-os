"""Phase executor: Implementation for backend services."""

import os

from lib.agent import prompt_with_retry
from lib.data_types import AgentPromptRequest
from lib.shared_phases import BOLD, GREEN, RED, RESET
from lib.utils import get_project_root


def phase_implement(state, step_label: str) -> bool:
    """Implement the plan using Claude Code.

    Generates code according to the plan, respecting the service's
    language and architectural patterns.
    """
    print(f"\n{BOLD}{step_label} Implementing plan...{RESET}")

    if not state.data.plan_file:
        print(f"  {RED}FAIL{RESET} No plan file found")
        return False

    project_root = get_project_root()
    lang = state.data.service_language
    service = state.data.service_name

    prompt = (
        f"Implement the plan at {state.data.plan_file} for the {lang} "
        f"service '{service}' at {state.data.service_path}.\n\n"
        f"Requirements:\n"
        f"- Follow existing code patterns and conventions in the service\n"
        f"- Write clean, well-documented code\n"
        f"- Include appropriate error handling\n"
        f"- Add/update tests as specified in the plan\n"
        f"- Do NOT modify files outside the service directory unless "
        f"the plan explicitly requires it\n"
        f"- For {lang}: follow idiomatic patterns\n"
    )

    # Add language-specific implementation hints
    if lang == "go":
        prompt += (
            "\nGo-specific:\n"
            "- Follow Go conventions (error handling, naming, packages)\n"
            "- Use dependency injection via constructor functions\n"
            "- Write table-driven tests\n"
        )
    elif lang == "spring-boot":
        prompt += (
            "\nSpring Boot-specific:\n"
            "- Follow layered architecture (controller/service/repository)\n"
            "- Use Bean Validation for input validation\n"
            "- Write tests with @SpringBootTest or MockMvc\n"
        )
    elif lang in ("nestjs", "express"):
        prompt += (
            "\nTypeScript-specific:\n"
            "- Use strict TypeScript types\n"
            "- Follow NestJS/Express patterns already in the codebase\n"
            "- Write Jest tests with proper mocking\n"
        )

    request = AgentPromptRequest(
        prompt=prompt,
        allowed_tools=[
            "Read", "Write", "Edit", "Bash", "Glob", "Grep",
        ],
        timeout_seconds=900,
    )

    output_path = os.path.join(
        state.get_state_dir(), "implementor", "raw_output.jsonl"
    )

    response = prompt_with_retry(request, project_root, output_path)

    if response.success:
        state.save()
        print(f"  {GREEN}OK{RESET} Implementation complete")
        return True
    else:
        print(f"  {RED}FAIL{RESET} Implementation failed")
        return False
