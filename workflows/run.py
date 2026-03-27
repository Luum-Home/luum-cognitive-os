#!/usr/bin/env -S uv run
# /// script
# dependencies = ["pydantic>=2.0", "httpx>=0.27", "click>=8.0", "python-dotenv>=1.0", "pyyaml>=6.0"]
# ///
"""
Cognitive OS Workflow CLI - AI-powered pipeline orchestration.

Usage:
  uv run .cognitive-os/workflows/run.py feature --service <consumer-service-2> --ticket DEV-1234
  uv run .cognitive-os/workflows/run.py bug --service <consumer-codename-a> --ticket BUG-567
  uv run .cognitive-os/workflows/run.py migration --service <consumer-service-4> --description "add transfers table"
  uv run .cognitive-os/workflows/run.py deploy --service <consumer-service-2> --env staging
  uv run .cognitive-os/workflows/run.py new-service --name analytics --port 3006
  uv run .cognitive-os/workflows/run.py resume --workflow-id abc12345
  uv run .cognitive-os/workflows/run.py services
"""

import os
import sys

# Add .cognitive-os/workflows/ to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import click


@click.group()
def cli():
    """Cognitive OS Workflow CLI - AI-powered pipeline orchestration."""
    pass


@cli.command()
@click.option("--service", required=True, help="Service name from services.yaml")
@click.option("--ticket", required=True, help="ClickUp task ID (e.g., DEV-1234)")
@click.option("--description", default="", help="Feature description")
@click.option("--skip-evaluate", is_flag=True, help="Skip evaluate+apply phases")
@click.option("--start-from", default=None, help="Start from a specific phase")
def feature(service, ticket, description, skip_evaluate, start_from):
    """Run the feature development pipeline for a backend service."""
    from backend_feature_pipeline import run_pipeline

    success = run_pipeline(
        ticket_id=ticket,
        service_name=service,
        description=description,
        skip_evaluate=skip_evaluate,
        start_from=start_from,
    )
    sys.exit(0 if success else 1)


@cli.command()
@click.option("--service", required=True, help="Service name from services.yaml")
@click.option("--ticket", required=True, help="ClickUp task ID (e.g., BUG-567)")
@click.option("--description", default="", help="Bug description")
@click.option("--skip-evaluate", is_flag=True, help="Skip evaluate+apply phases")
@click.option("--start-from", default=None, help="Start from a specific phase")
def bug(service, ticket, description, skip_evaluate, start_from):
    """Run the bug fix pipeline for a backend service."""
    from backend_bug_pipeline import run_pipeline

    success = run_pipeline(
        ticket_id=ticket,
        service_name=service,
        description=description,
        skip_evaluate=skip_evaluate,
        start_from=start_from,
    )
    sys.exit(0 if success else 1)


@cli.command()
@click.option("--service", required=True, help="Service name from services.yaml")
@click.option("--description", required=True, help="Migration description")
@click.option("--start-from", default=None, help="Start from a specific phase")
def migration(service, description, start_from):
    """Run the database migration pipeline."""
    from backend_migration_pipeline import run_pipeline

    success = run_pipeline(
        service_name=service,
        description=description,
        start_from=start_from,
    )
    sys.exit(0 if success else 1)


@cli.command()
@click.option("--service", required=True, help="Service name from services.yaml")
@click.option(
    "--env",
    required=True,
    type=click.Choice(["dev", "staging", "prod"]),
    help="Target environment",
)
@click.option("--start-from", default=None, help="Start from a specific phase")
def deploy(service, env, start_from):
    """Run the deployment pipeline for a backend service."""
    from backend_deploy_pipeline import run_pipeline

    success = run_pipeline(
        service_name=service,
        env_name=env,
        start_from=start_from,
    )
    sys.exit(0 if success else 1)


@cli.command("new-service")
@click.option("--name", required=True, help="New service name")
@click.option("--port", required=True, type=int, help="Service port")
def new_service(name, port):
    """Create a new Go microservice from template."""
    from go_service_pipeline import run_pipeline

    success = run_pipeline(
        service_name=name,
        port=port,
    )
    sys.exit(0 if success else 1)


@cli.command()
@click.option("--workflow-id", required=True, help="Workflow ID to resume")
@click.option("--start-from", default=None, help="Start from a specific phase")
def resume(workflow_id, start_from):
    """Resume an interrupted workflow."""
    from backend_state import BackendWorkflowState

    state = BackendWorkflowState.load(workflow_id)
    if not state:
        click.echo(f"Could not load workflow: {workflow_id}")
        sys.exit(1)

    wtype = state.data.workflow_type

    if wtype == "feature":
        from backend_feature_pipeline import run_pipeline

        success = run_pipeline(
            ticket_id=None,
            service_name=None,
            resume_id=workflow_id,
            start_from=start_from,
        )
    elif wtype == "bug":
        from backend_bug_pipeline import run_pipeline

        success = run_pipeline(
            ticket_id=None,
            service_name=None,
            resume_id=workflow_id,
            start_from=start_from,
        )
    elif wtype == "migration":
        from backend_migration_pipeline import run_pipeline

        success = run_pipeline(
            service_name=None,
            description="",
            resume_id=workflow_id,
            start_from=start_from,
        )
    elif wtype == "deploy":
        from backend_deploy_pipeline import run_pipeline

        success = run_pipeline(
            service_name=None,
            env_name="",
            resume_id=workflow_id,
            start_from=start_from,
        )
    else:
        click.echo(f"Unknown workflow type: {wtype}")
        sys.exit(1)

    sys.exit(0 if success else 1)


@cli.command()
def services():
    """List all registered backend services."""
    from lib.utils import get_services_config

    svcs = get_services_config()

    click.echo(f"\n{'Name':<20} {'Language':<12} {'Port':<6} {'Path'}")
    click.echo("-" * 70)
    for s in svcs:
        click.echo(f"{s.name:<20} {s.language:<12} {s.port:<6} {s.path}")
    click.echo(f"\n{len(svcs)} services registered")


if __name__ == "__main__":
    cli()
