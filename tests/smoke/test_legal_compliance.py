"""Behavioral tests for legal compliance across the Cognitive OS codebase.

Verifies that NOTICE attributions, trademark disclaimers, pricing
annotations, and safety warnings are present where required.

Author: luum
"""

from __future__ import annotations

from pathlib import Path

import pytest


# All paths relative to project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class TestNoticeFile:
    """NOTICE file must exist and contain all Apache-2.0 attributions."""

    @pytest.fixture
    def notice_content(self) -> str:
        notice = PROJECT_ROOT / "NOTICE"
        assert notice.exists(), "NOTICE file does not exist"
        return notice.read_text()

    def test_notice_file_exists(self) -> None:
        assert (PROJECT_ROOT / "NOTICE").exists()

    def test_notice_has_crawl4ai_attribution(self, notice_content: str) -> None:
        assert "Crawl4AI" in notice_content
        assert "UncleCode" in notice_content
        assert "Apache" in notice_content

    def test_notice_has_clickhouse_attribution(self, notice_content: str) -> None:
        assert "ClickHouse" in notice_content
        assert "ClickHouse Inc" in notice_content

    def test_notice_has_nemo_guardrails_attribution(
        self, notice_content: str
    ) -> None:
        assert "NeMo Guardrails" in notice_content
        assert "NVIDIA" in notice_content

    def test_notice_has_seaweedfs_attribution(self, notice_content: str) -> None:
        assert "SeaweedFS" in notice_content

    def test_notice_has_opik_attribution(self, notice_content: str) -> None:
        assert "Opik" in notice_content
        assert "Comet" in notice_content

    def test_notice_has_cognee_attribution(self, notice_content: str) -> None:
        assert "Cognee" in notice_content
        assert "Topoteretes" in notice_content

    def test_notice_has_deepeval_attribution(self, notice_content: str) -> None:
        assert "DeepEval" in notice_content
        assert "Confident AI" in notice_content

    def test_notice_has_ragas_attribution(self, notice_content: str) -> None:
        assert "RAGAS" in notice_content
        assert "Exploding Gradients" in notice_content


class TestTrademarkDisclaimer:
    """docs/INDEX.md must have a trademark disclaimer."""

    def test_index_has_trademark_disclaimer(self) -> None:
        index = PROJECT_ROOT / "docs" / "INDEX.md"
        assert index.exists(), "docs/INDEX.md does not exist"
        content = index.read_text()
        assert "not affiliated with" in content
        assert "endorsed by" in content or "sponsored by" in content
        assert "trademarks" in content.lower() or "trademark" in content.lower()


class TestPricingAnnotations:
    """Pricing references must include date annotations."""

    def test_model_routing_has_price_date_annotation(self) -> None:
        routing = PROJECT_ROOT / "rules" / "model-routing.md"
        assert routing.exists(), "rules/model-routing.md does not exist"
        content = routing.read_text()
        assert "Prices as of" in content or "prices as of" in content
        assert "2026" in content

    def test_competitive_landscape_has_data_freshness_note(self) -> None:
        landscape = PROJECT_ROOT / "docs" / "competitive-landscape.md"
        assert landscape.exists(), "docs/competitive-landscape.md does not exist"
        content = landscape.read_text()
        assert "may be outdated" in content or "as of" in content.lower()


class TestCompatibilityDisclaimer:
    """docs/ide-compatibility.md must have a compatibility disclaimer."""

    def test_ide_compatibility_has_disclaimer(self) -> None:
        ide = PROJECT_ROOT / "docs" / "ide-compatibility.md"
        assert ide.exists(), "docs/ide-compatibility.md does not exist"
        content = ide.read_text()
        assert "may not reflect actual testing" in content or "Last verified" in content


class TestDangerousFlag:
    """--dangerously-skip-permissions must have a safety warning."""

    def test_batch_runner_has_warning(self) -> None:
        skill = PROJECT_ROOT / "skills" / "batch-runner" / "SKILL.md"
        assert skill.exists(), "skills/batch-runner/SKILL.md does not exist"
        content = skill.read_text()
        if "--dangerously-skip-permissions" in content:
            # Must have a warning near the flag usage
            assert (
                "development/testing ONLY" in content
                or "Warning" in content
                or "ONLY" in content
            ), "Missing safety warning for --dangerously-skip-permissions"
