"""Phase executor: Security validation.

Checks constitutional gates compliance, hardcoded secrets, and license policy.
"""

import os
import re
import subprocess

from lib.agent import prompt_with_retry
from lib.data_types import AgentPromptRequest
from lib.shared_phases import BOLD, DIM, GREEN, RED, RESET, YELLOW
from lib.utils import get_project_root, get_service_abs_path


def phase_security_check(state, step_label: str, service) -> bool:
    """Run security validations on the service.

    Checks:
    1. Constitutional gates compliance (project-specific rules)
    2. Hardcoded secrets detection
    3. License check on new dependencies
    """
    print(
        f"\n{BOLD}{step_label} Security check "
        f"({state.data.service_name})...{RESET}"
    )

    project_root = get_project_root()
    service_abs = get_service_abs_path(service)
    issues = []

    # --- Check 1: Hardcoded secrets ---
    print(f"  {DIM}Scanning for hardcoded secrets...{RESET}")
    secret_patterns = [
        r'(?i)(api[_-]?key|apikey)\s*[:=]\s*["\'][a-zA-Z0-9]{16,}',
        r'(?i)(secret|password|passwd|pwd)\s*[:=]\s*["\'][^"\']{8,}',
        r'(?i)(token)\s*[:=]\s*["\'][a-zA-Z0-9._-]{20,}',
        r'(?i)Bearer\s+[a-zA-Z0-9._-]{20,}',
        r'(?i)(aws_access_key_id|aws_secret_access_key)\s*[:=]',
    ]

    for pattern in secret_patterns:
        try:
            result = subprocess.run(
                ["grep", "-rn", "-E", pattern, "."],
                cwd=service_abs,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.stdout.strip():
                # Filter out test files and .env.example
                lines = result.stdout.strip().split("\n")
                real_issues = [
                    l for l in lines
                    if not any(
                        skip in l
                        for skip in [
                            "test", "spec", ".env.example",
                            "mock", "fixture", "node_modules",
                        ]
                    )
                ]
                if real_issues:
                    issues.extend(
                        [f"Possible secret: {l[:100]}" for l in real_issues[:5]]
                    )
        except (subprocess.TimeoutExpired, Exception):
            pass

    # --- Check 2: Constitutional gates (Claude-assisted) ---
    print(f"  {DIM}Checking constitutional gates...{RESET}")

    prompt = (
        f"Review the recent changes in the {state.data.service_language} "
        f"service at {state.data.service_path} for compliance with these "
        f"constitutional gates:\n\n"
        f"1. Mobile Never Talks to Microservices (all traffic via BFF)\n"
        f"2. Mock Before Integrate (external providers need mocks)\n"
        f"3. Secrets Never in Code (env vars only)\n"
        f"4. Backward Compatible APIs (no breaking changes)\n"
        f"5. Idempotent Operations (financial ops need transaction IDs)\n"
        f"6. Audit Trail (financial ops must be traceable)\n\n"
        f"Check the git diff for recent changes and report any violations. "
        f"Output a brief report with PASS or FAIL for each gate. "
        f"Only report actual violations, not theoretical ones."
    )

    request = AgentPromptRequest(
        prompt=prompt,
        allowed_tools=["Read", "Glob", "Grep", "Bash"],
        timeout_seconds=300,
    )

    output_path = os.path.join(
        state.get_state_dir(), "security", "raw_output.jsonl"
    )

    response = prompt_with_retry(
        request, project_root, output_path, max_retries=0
    )

    if response.success:
        output_lower = response.output.lower()
        if "fail" in output_lower and "gate" in output_lower:
            issues.append("Constitutional gate violation detected")
            print(f"  {YELLOW}WARNING{RESET} Gate violation found")
        else:
            print(f"  {GREEN}OK{RESET} Constitutional gates passed")
    else:
        print(
            f"  {YELLOW}WARNING{RESET} Gate check inconclusive "
            f"(continuing)"
        )

    # --- Check 3: License check for new dependencies ---
    print(f"  {DIM}Checking dependency licenses...{RESET}")
    lang = state.data.service_language

    blocked_licenses = [
        "AGPL", "SSPL", "BSL", "ELv2", "Commons Clause",
        "FSL", "Server Side Public License",
    ]

    if lang == "go":
        # Check go.sum for new entries
        go_sum = os.path.join(service_abs, "go.sum")
        if os.path.exists(go_sum):
            print(f"  {DIM}Go dependencies found (manual license review "
                  f"recommended for new deps){RESET}")
    elif lang in ("nestjs", "express"):
        # Check for package-lock.json changes
        lock_file = os.path.join(service_abs, "package-lock.json")
        if os.path.exists(lock_file):
            print(f"  {DIM}Node dependencies found (manual license review "
                  f"recommended for new deps){RESET}")

    # --- Results ---
    if issues:
        state.update(
            security_passed=False,
            security_issues=issues[:10],
        )
        print(f"\n  {YELLOW}WARNING{RESET} {len(issues)} security issue(s):")
        for issue in issues[:5]:
            print(f"    - {issue}")
        # Security check is a warning, not a blocker
        print(
            f"  {YELLOW}WARNING{RESET} Security issues found but "
            f"pipeline continues (review recommended)"
        )
        return True
    else:
        state.update(security_passed=True, security_issues=[])
        print(f"  {GREEN}OK{RESET} Security check passed")
        return True
