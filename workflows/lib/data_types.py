"""Pydantic models for backend workflow state and agent communication."""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ServiceLanguage(str, Enum):
    GO = "go"
    SPRING_BOOT = "spring-boot"
    NESTJS = "nestjs"
    EXPRESS = "express"


class RetryCode(Enum):
    SUCCESS = "success"
    RETRY = "retry"
    FAIL = "fail"


class AgentPromptRequest(BaseModel):
    prompt: str
    allowed_tools: List[str] = Field(default_factory=list)
    cwd: Optional[str] = None
    timeout_seconds: int = 600


class AgentPromptResponse(BaseModel):
    success: bool
    output: str
    duration_seconds: float = 0.0
    raw_jsonl_path: Optional[str] = None


class ClickUpTaskData(BaseModel):
    """Represents a ClickUp task with relevant fields."""

    task_id: str
    custom_id: str = ""
    name: str = ""
    description: str = ""
    status: str = ""
    tags: List[str] = Field(default_factory=list)
    assignees: List[str] = Field(default_factory=list)
    url: str = ""
    custom_fields: Dict[str, Any] = Field(default_factory=dict)
    attachments: List[Dict[str, Any]] = Field(default_factory=list)


class ServiceConfig(BaseModel):
    """Configuration for a backend service from services.yaml."""

    name: str
    path: str
    language: ServiceLanguage
    port: int
    build: str = ""
    test: str = ""
    lint: str = ""
    docker: bool = False


class BackendWorkflowStateData(BaseModel):
    """State data for backend workflows.

    workflow_type: "feature" | "bug" | "migration" | "deploy"
    """

    workflow_id: str
    workflow_type: str
    ticket_id: str = ""
    name: str = ""
    description: str = ""
    branch_name: str = ""

    # Service info
    service_name: str = ""
    service_path: str = ""
    service_language: str = ""

    # ClickUp
    clickup_task_id: str = ""
    clickup_task_url: str = ""
    clickup_tags: List[str] = Field(default_factory=list)
    clickup_custom_fields: Dict[str, Any] = Field(default_factory=dict)

    # Plan phase
    plan_file: Optional[str] = None

    # Evaluation phase
    evaluation_files: List[str] = Field(default_factory=list)
    evaluation_score: Optional[int] = None
    evaluation_verdict: Optional[str] = None

    # Build phase
    build_passed: Optional[bool] = None
    build_retry_count: int = 0
    build_errors: Optional[str] = None

    # Test phase
    test_passed: Optional[bool] = None
    test_retry_count: int = 0
    test_errors: Optional[str] = None

    # Lint phase
    lint_passed: Optional[bool] = None
    lint_errors: Optional[str] = None

    # Security check phase
    security_passed: Optional[bool] = None
    security_issues: List[str] = Field(default_factory=list)

    # Migration phase
    migration_file: Optional[str] = None
    migration_applied_dev: bool = False
    migration_applied_prod: bool = False
    migration_reversible: Optional[bool] = None

    # Deploy phase
    deploy_env: str = ""
    deploy_image_tag: str = ""
    deploy_status: str = ""
    deploy_rollback_available: bool = False

    # Git
    commit_hash: Optional[str] = None
    pr_url: Optional[str] = None
    pr_created: bool = False

    # Phase tracking
    current_phase: str = "init"
    phases_completed: List[str] = Field(default_factory=list)
