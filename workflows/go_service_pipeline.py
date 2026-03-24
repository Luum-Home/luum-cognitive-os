"""
Go Service Pipeline - Create a new Go microservice from template.

Usage:
  uv run .cognitive-os/workflows/run.py new-service --name analytics --port 3006

Creates a new Go service with:
- Clean architecture structure (cmd/, internal/, pkg/)
- HTTP server with health endpoints
- Docker and docker-compose integration
- Basic test scaffolding
- Services.yaml registration
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.agent import prompt_with_retry
from lib.data_types import AgentPromptRequest
from lib.shared_phases import BOLD, CYAN, DIM, GREEN, RED, RESET, YELLOW
from lib.utils import get_project_root


def run_pipeline(
    service_name: str,
    port: int,
) -> bool:
    """Create a new Go microservice from template."""

    project_root = get_project_root()
    service_path = f"micro-services/{service_name}"
    abs_path = os.path.join(project_root, service_path)

    print(f"\n{BOLD}{'=' * 50}{RESET}")
    print(f"{BOLD}New Go Service Pipeline{RESET}")
    print(f"{DIM}Service: {service_name}{RESET}")
    print(f"{DIM}Port: {port}{RESET}")
    print(f"{DIM}Path: {service_path}{RESET}")
    print(f"{BOLD}{'=' * 50}{RESET}")

    # Check if service already exists
    if os.path.exists(abs_path):
        print(f"  {RED}FAIL{RESET} Directory already exists: {service_path}")
        return False

    # Step 1: Scaffold the service
    print(f"\n{BOLD}[1/4] Scaffolding service...{RESET}")

    prompt = (
        f"Create a new Go microservice called '{service_name}' at "
        f"{service_path}/ in the project monorepo.\n\n"
        f"Port: {port}\n\n"
        f"Follow the existing Go service patterns in the repo "
        f"(check backend-go/ and micro-services/ for reference). "
        f"Create the following structure:\n\n"
        f"```\n"
        f"{service_path}/\n"
        f"  cmd/{service_name}/\n"
        f"    main.go              -- HTTP server entry point on port {port}\n"
        f"  internal/\n"
        f"    handler/             -- HTTP handlers\n"
        f"    service/             -- Business logic\n"
        f"    repository/          -- Data access\n"
        f"    model/               -- Domain models\n"
        f"  pkg/                   -- Shared utilities\n"
        f"  go.mod                 -- Module: github.com/example-org/{service_name}\n"
        f"  go.sum\n"
        f"  Dockerfile             -- Multi-stage build\n"
        f"  Makefile               -- build, test, lint, run targets\n"
        f"  README.md              -- Service documentation\n"
        f"```\n\n"
        f"Include:\n"
        f"- Health check endpoint: GET /health\n"
        f"- Readiness endpoint: GET /ready\n"
        f"- Graceful shutdown\n"
        f"- Structured logging (slog)\n"
        f"- Basic middleware (recovery, logging, CORS)\n"
        f"- Example handler with tests\n"
        f"- Dockerfile with multi-stage build (final image < 50MB)\n"
    )

    request = AgentPromptRequest(
        prompt=prompt,
        allowed_tools=[
            "Read", "Write", "Edit", "Bash", "Glob", "Grep",
        ],
        timeout_seconds=600,
    )

    response = prompt_with_retry(request, project_root, max_retries=1)

    if not response.success:
        print(f"  {RED}FAIL{RESET} Service scaffolding failed")
        return False

    print(f"  {GREEN}OK{RESET} Service scaffolded")

    # Step 2: Update services.yaml
    print(f"\n{BOLD}[2/4] Registering in services.yaml...{RESET}")

    config_path = os.path.join(
        project_root, ".cognitive-os", "workflows", "config", "services.yaml"
    )

    try:
        with open(config_path, "r") as f:
            content = f.read()

        new_entry = (
            f"\n  - name: {service_name}\n"
            f"    path: {service_path}\n"
            f"    language: go\n"
            f"    port: {port}\n"
            f"    build: go build ./...\n"
            f"    test: go test ./...\n"
            f"    lint: golangci-lint run ./...\n"
            f"    docker: true\n"
        )

        content = content.rstrip() + new_entry
        with open(config_path, "w") as f:
            f.write(content)

        print(f"  {GREEN}OK{RESET} Registered in services.yaml")
    except Exception as e:
        print(f"  {YELLOW}WARNING{RESET} Could not update services.yaml: {e}")

    # Step 3: Verify build
    print(f"\n{BOLD}[3/4] Verifying build...{RESET}")

    import subprocess

    try:
        result = subprocess.run(
            ["go", "build", "./..."],
            cwd=abs_path,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            print(f"  {GREEN}OK{RESET} Build successful")
        else:
            print(
                f"  {YELLOW}WARNING{RESET} Build had issues: "
                f"{result.stderr[:200]}"
            )
    except Exception as e:
        print(f"  {YELLOW}WARNING{RESET} Could not verify build: {e}")

    # Step 4: Verify tests
    print(f"\n{BOLD}[4/4] Verifying tests...{RESET}")

    try:
        result = subprocess.run(
            ["go", "test", "./..."],
            cwd=abs_path,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            print(f"  {GREEN}OK{RESET} Tests passed")
        else:
            print(
                f"  {YELLOW}WARNING{RESET} Tests had issues: "
                f"{result.stderr[:200]}"
            )
    except Exception as e:
        print(f"  {YELLOW}WARNING{RESET} Could not run tests: {e}")

    print(f"\n{BOLD}{'=' * 50}{RESET}")
    print(f"{GREEN}New Go service created!{RESET}")
    print(f"{DIM}Path: {service_path}{RESET}")
    print(f"{DIM}Port: {port}{RESET}")
    print(f"\n{DIM}Next steps:{RESET}")
    print(f"  1. cd {service_path}")
    print(f"  2. go mod tidy")
    print(f"  3. make run")
    print(f"{BOLD}{'=' * 50}{RESET}")

    return True
