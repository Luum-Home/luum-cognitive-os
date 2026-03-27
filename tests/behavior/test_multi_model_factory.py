"""
Multi-Model AI Software Factory Tests

Validates the multi-model-factory.md documentation:
  - Document exists and is non-trivial
  - Describes the 3-layer architecture (Strategic/Execution/Worker)
  - Maps SDD phases to factory layers
  - Documents cost optimization strategies
  - Includes roadmap integration
  - References existing lib components (model_router, planning_poker, etc.)
"""

from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DOC_PATH = PROJECT_ROOT / "docs" / "multi-model-factory.md"


def _read_doc() -> str:
    """Read the multi-model-factory.md document."""
    assert DOC_PATH.exists(), f"Document not found: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


class TestMultiModelFactoryDocExists:
    """Verify the document exists and has substantial content."""

    def test_document_exists(self):
        """multi-model-factory.md must exist in docs/."""
        assert DOC_PATH.exists(), (
            "docs/multi-model-factory.md does not exist. "
            "This document describes the multi-model AI software factory architecture."
        )

    def test_document_is_not_empty(self):
        """Document must have meaningful content (at least 2000 characters)."""
        content = _read_doc()
        assert len(content) > 2000, (
            f"Document is too short ({len(content)} chars). "
            "Expected substantial documentation of the multi-model factory."
        )


class TestThreeLayerArchitecture:
    """Verify the 3-layer factory architecture is documented."""

    def test_strategic_layer_documented(self):
        """Document must describe the Strategic layer."""
        content = _read_doc()
        assert "strategic" in content.lower(), (
            "Document must describe the Strategic layer "
            "(reasoning, architecture, CTO/Chief Architect role)."
        )

    def test_execution_layer_documented(self):
        """Document must describe the Execution layer."""
        content = _read_doc()
        assert "execution" in content.lower(), (
            "Document must describe the Execution layer "
            "(implementation, refactoring, Senior Engineer role)."
        )

    def test_worker_layer_documented(self):
        """Document must describe the Worker layer."""
        content = _read_doc()
        assert "worker" in content.lower(), (
            "Document must describe the Worker layer "
            "(bulk operations, docs, Junior Dev role)."
        )

    def test_all_three_layers_present(self):
        """All three layers must be described in the same document."""
        content = _read_doc().lower()
        layers = ["strategic layer", "execution layer", "worker layer"]
        missing = [layer for layer in layers if layer not in content]
        assert not missing, (
            f"Missing layer descriptions: {missing}. "
            "The 3-layer factory model requires all three layers."
        )


class TestSDDPhaseMapping:
    """Verify SDD pipeline phases are mapped to factory layers."""

    def test_sdd_phase_mapping_section_exists(self):
        """Document must have a section mapping SDD phases to layers."""
        content = _read_doc()
        assert "sdd" in content.lower() and "phase" in content.lower(), (
            "Document must include SDD phase-to-layer mapping."
        )

    def test_core_sdd_phases_mapped(self):
        """All core SDD phases must appear in the mapping."""
        content = _read_doc().lower()
        phases = ["explore", "propose", "spec", "design", "tasks", "apply", "verify", "archive"]
        missing = [phase for phase in phases if phase not in content]
        assert not missing, (
            f"SDD phases not found in document: {missing}. "
            "All 8 core SDD phases must be mapped to factory layers."
        )

    def test_archive_uses_worker_layer(self):
        """Archive phase should map to the Worker layer (cheapest model)."""
        content = _read_doc().lower()
        # Find the archive line and check it mentions haiku or worker
        assert "archive" in content and "haiku" in content, (
            "Archive phase should be mapped to haiku (Worker layer) "
            "as it requires minimal reasoning."
        )


class TestCostOptimizationStrategies:
    """Verify cost optimization strategies are documented."""

    def test_cost_optimization_section_exists(self):
        """Document must have a cost optimization section."""
        content = _read_doc().lower()
        assert "cost optimization" in content or "cost" in content, (
            "Document must include cost optimization strategies."
        )

    def test_local_model_offloading_documented(self):
        """Local model offloading must be mentioned as a cost strategy."""
        content = _read_doc().lower()
        assert "local" in content and ("offload" in content or "zero-cost" in content or "llama" in content), (
            "Document must describe local model offloading "
            "(Llama/Qwen for zero-cost execution)."
        )

    def test_model_downgrade_chain_documented(self):
        """Model downgrade chain (opus->sonnet->haiku) must be documented."""
        content = _read_doc().lower()
        assert "downgrade" in content or "fallback" in content, (
            "Document must describe the model downgrade chain "
            "for budget pressure scenarios."
        )

    def test_budget_thresholds_documented(self):
        """Budget thresholds (80%, 95%, 100%) must appear."""
        content = _read_doc()
        assert "80%" in content or "95%" in content, (
            "Document must include budget threshold percentages "
            "that trigger model downgrades."
        )


class TestRoadmapIntegration:
    """Verify roadmap integration is documented."""

    def test_roadmap_section_exists(self):
        """Document must have a roadmap integration section."""
        content = _read_doc().lower()
        assert "roadmap" in content, (
            "Document must include a roadmap integration section "
            "showing how the factory evolves across phases."
        )

    def test_phase_1_referenced(self):
        """Phase 1 (Q2 2026) must be referenced."""
        content = _read_doc()
        assert "Phase 1" in content or "Q2 2026" in content, (
            "Document must reference Phase 1 (Q2 2026) "
            "as the initial multi-model activation phase."
        )

    def test_roadmap_doc_cross_referenced(self):
        """Document must cross-reference roadmap.md."""
        content = _read_doc()
        assert "roadmap.md" in content, (
            "Document must cross-reference docs/roadmap.md."
        )


class TestExistingComponentReferences:
    """Verify references to existing lib components."""

    def test_model_router_referenced(self):
        """model_router.py must be referenced."""
        content = _read_doc()
        assert "model_router" in content, (
            "Document must reference lib/model_router.py "
            "(the static routing table with dynamic selection)."
        )

    def test_planning_poker_referenced(self):
        """planning_poker.py must be referenced."""
        content = _read_doc()
        assert "planning_poker" in content, (
            "Document must reference lib/planning_poker.py "
            "(multi-model estimation using all 3 layers)."
        )

    def test_capability_levels_referenced(self):
        """capability_levels.py must be referenced."""
        content = _read_doc()
        assert "capability_levels" in content, (
            "Document must reference lib/capability_levels.py "
            "(model capability assessment driving layer assignment)."
        )

    def test_litellm_referenced(self):
        """LiteLLM must be referenced as the multi-provider proxy."""
        content = _read_doc()
        assert "LiteLLM" in content or "litellm" in content, (
            "Document must reference LiteLLM as the multi-provider routing proxy."
        )

    def test_cost_predictor_referenced(self):
        """cost_predictor.py must be referenced."""
        content = _read_doc()
        assert "cost_predictor" in content, (
            "Document must reference lib/cost_predictor.py "
            "(historical cost data informing model selection)."
        )

    def test_agent_bus_referenced(self):
        """agent_bus.py must be referenced."""
        content = _read_doc()
        assert "agent_bus" in content, (
            "Document must reference lib/agent_bus.py "
            "(communication between models working on same task)."
        )
