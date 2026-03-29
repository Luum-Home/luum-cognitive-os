"""Behavior tests for the COS Web Dashboard Architecture document.

Validates that docs/dashboard-architecture.md exists and contains
all required architectural sections.
"""

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DOC_PATH = PROJECT_ROOT / "docs" / "dashboard-architecture.md"


@pytest.fixture
def doc_content() -> str:
    """Read the dashboard architecture document."""
    assert DOC_PATH.is_file(), f"Dashboard architecture doc not found at {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


class TestDashboardArchitectureExists:
    """The architecture document must exist."""

    def test_design_doc_exists(self):
        assert DOC_PATH.is_file(), (
            "docs/dashboard-architecture.md must exist. "
            "This is the primary design document for the COS web dashboard."
        )

    def test_design_doc_not_empty(self, doc_content: str):
        assert len(doc_content.strip()) > 500, (
            "Dashboard architecture doc is too short to be meaningful."
        )


class TestTechStackSection:
    """The document must include a tech stack decision section."""

    def test_has_tech_stack_section(self, doc_content: str):
        assert "tech stack" in doc_content.lower(), (
            "Document must contain a 'Tech Stack' section."
        )

    def test_tech_stack_has_framework(self, doc_content: str):
        lower = doc_content.lower()
        assert "next.js" in lower or "nextjs" in lower or "react" in lower, (
            "Tech stack must specify a frontend framework."
        )

    def test_tech_stack_has_ui_library(self, doc_content: str):
        lower = doc_content.lower()
        assert "shadcn" in lower or "radix" in lower or "ui library" in lower, (
            "Tech stack must specify a UI component library."
        )

    def test_tech_stack_has_state_management(self, doc_content: str):
        lower = doc_content.lower()
        assert "zustand" in lower or "state" in lower, (
            "Tech stack must address state management."
        )

    def test_tech_stack_has_realtime(self, doc_content: str):
        lower = doc_content.lower()
        assert "websocket" in lower or "real-time" in lower or "realtime" in lower, (
            "Tech stack must address real-time communication for agent monitoring."
        )


class TestPagesViewsSection:
    """The document must define dashboard pages/views."""

    def test_has_pages_section(self, doc_content: str):
        lower = doc_content.lower()
        assert "pages" in lower and "views" in lower, (
            "Document must contain a 'Pages and Views' section."
        )

    def test_has_dashboard_page(self, doc_content: str):
        assert "Dashboard" in doc_content, (
            "Must define a Dashboard overview page."
        )

    def test_has_rules_page(self, doc_content: str):
        assert "Rules" in doc_content, (
            "Must define a Rules management page."
        )

    def test_has_skills_page(self, doc_content: str):
        assert "Skills" in doc_content, (
            "Must define a Skills browser page."
        )

    def test_has_agents_page(self, doc_content: str):
        assert "Agents" in doc_content or "Agent" in doc_content, (
            "Must define an Agents monitoring page."
        )

    def test_has_memory_page(self, doc_content: str):
        lower = doc_content.lower()
        assert "memory" in lower or "engram" in lower, (
            "Must define a Memory/Engram browser page."
        )

    def test_has_cost_page(self, doc_content: str):
        lower = doc_content.lower()
        assert "cost" in lower or "budget" in lower, (
            "Must define a Cost/Budget tracking page."
        )

    def test_has_security_page(self, doc_content: str):
        lower = doc_content.lower()
        assert "security" in lower, (
            "Must define a Security dashboard page."
        )


class TestAPILayerSection:
    """The document must describe the API layer connecting dashboard to COS backend."""

    def test_has_api_layer_section(self, doc_content: str):
        lower = doc_content.lower()
        assert "api layer" in lower or "api" in lower, (
            "Document must contain an 'API Layer' section."
        )

    def test_references_mcp_server(self, doc_content: str):
        lower = doc_content.lower()
        assert "mcp" in lower or "cos_mcp" in lower, (
            "API layer must reference the COS MCP server as the backend."
        )

    def test_has_endpoint_mapping(self, doc_content: str):
        lower = doc_content.lower()
        assert "cos_status" in lower or "/api/" in lower, (
            "API layer must map MCP tools to dashboard endpoints."
        )


class TestDeploymentSection:
    """The document must describe deployment strategy."""

    def test_has_deployment_section(self, doc_content: str):
        lower = doc_content.lower()
        assert "deployment" in lower or "docker" in lower, (
            "Document must contain a 'Deployment' section."
        )

    def test_has_docker_compose(self, doc_content: str):
        lower = doc_content.lower()
        assert "docker-compose" in lower or "docker compose" in lower, (
            "Deployment must include Docker Compose configuration."
        )

    def test_has_port_assignment(self, doc_content: str):
        assert "3300" in doc_content or "port" in doc_content.lower(), (
            "Deployment must specify the dashboard port."
        )


class TestPhasePlanSection:
    """The document must include a phased implementation plan."""

    def test_has_phase_plan_section(self, doc_content: str):
        lower = doc_content.lower()
        assert "phase plan" in lower or "phase 1" in lower, (
            "Document must contain a 'Phase Plan' section."
        )

    def test_has_multiple_phases(self, doc_content: str):
        lower = doc_content.lower()
        assert "phase 1" in lower and "phase 2" in lower, (
            "Phase plan must define at least Phase 1 and Phase 2."
        )

    def test_phase_1_is_mvp(self, doc_content: str):
        lower = doc_content.lower()
        # Phase 1 should cover basic functionality
        phase_1_idx = lower.find("phase 1")
        assert phase_1_idx != -1, "Must have Phase 1"
        # Check that some MVP features are mentioned near Phase 1
        phase_1_region = lower[phase_1_idx:phase_1_idx + 1000]
        has_mvp_features = (
            "dashboard" in phase_1_region
            or "rules" in phase_1_region
            or "skills" in phase_1_region
            or "mvp" in phase_1_region
        )
        assert has_mvp_features, (
            "Phase 1 must cover MVP features (dashboard, rules, or skills)."
        )


class TestComponentExtractionSection:
    """The document must describe which components to extract from evaluated platforms."""

    def test_has_component_extraction(self, doc_content: str):
        lower = doc_content.lower()
        assert "component" in lower and "extract" in lower, (
            "Document must contain a 'Component Extraction' section."
        )

    def test_references_mit_sources(self, doc_content: str):
        lower = doc_content.lower()
        assert "mit" in lower or "apache" in lower, (
            "Component extraction must reference license-compatible sources."
        )

    def test_references_automaker(self, doc_content: str):
        lower = doc_content.lower()
        assert "automaker" in lower, (
            "Must reference AutoMaker as a component source (MIT, high COS fit)."
        )

    def test_references_agent_kit(self, doc_content: str):
        lower = doc_content.lower()
        assert "inngest" in lower or "agent-kit" in lower or "agent_kit" in lower, (
            "Must reference inngest/agent-kit as a component source (Apache-2.0)."
        )
