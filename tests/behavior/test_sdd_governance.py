"""Behavior tests for SDD governance scoring and compliance.

Tests artifact completeness scoring, structural validation, freshness
checks, process violation detection, rollback assessment, and health
classification.

Related skill: sdd-verify / sdd-archive (governance layer)
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pytest

pytestmark = pytest.mark.behavior


# ---------------------------------------------------------------------------
# Default weights and required phases
# ---------------------------------------------------------------------------

DEFAULT_WEIGHTS: Dict[str, float] = {
    "proposal": 0.15,
    "spec": 0.25,
    "design": 0.15,
    "tasks": 0.20,
    "apply": 0.15,
    "verify": 0.10,
}

REQUIRED_ARTIFACTS = {"proposal", "spec", "tasks", "apply", "verify"}

# Phase dependency: each phase requires its predecessor to exist
PHASE_DEPENDENCIES: Dict[str, str] = {
    "spec": "proposal",
    "design": "proposal",
    "tasks": "spec",
    "apply": "tasks",
    "verify": "apply",
    "archive": "verify",
}


# ---------------------------------------------------------------------------
# Governance functions
# ---------------------------------------------------------------------------


def calculate_compliance_score(
    artifacts: Dict[str, Optional[str]],
    weights: Optional[Dict[str, float]] = None,
) -> float:
    """Calculate artifact completeness score as a percentage.

    Args:
        artifacts: Mapping of artifact name -> content (or None if missing).
        weights: Optional custom weights per artifact.

    Returns:
        Score from 0.0 to 100.0.
    """
    w = weights or DEFAULT_WEIGHTS
    total_weight = sum(w.values())
    if total_weight == 0:
        return 0.0

    earned = sum(
        w.get(name, 0) for name, content in artifacts.items() if content is not None
    )
    return round((earned / total_weight) * 100, 1)


def classify_health(score: float) -> str:
    """Classify overall health from compliance score.

    Returns: 'HEALTHY' | 'WARNING' | 'CRITICAL'
    """
    if score >= 85:
        return "HEALTHY"
    if score >= 50:
        return "WARNING"
    return "CRITICAL"


def validate_structure(content: str, required_sections: Optional[List[str]] = None) -> Tuple[bool, str]:
    """Validate that an artifact has sufficient content and structure.

    Args:
        content: The artifact text.
        required_sections: Optional list of section headers to check.

    Returns:
        (passed, reason)
    """
    if len(content.strip()) < 100:
        return False, "Content too short (<100 chars)"

    if required_sections:
        missing = [s for s in required_sections if s not in content]
        if missing:
            return False, f"Missing sections: {', '.join(missing)}"

    return True, "ok"


def check_freshness(artifact_date: str, threshold_days: int = 30) -> Tuple[str, bool]:
    """Check if an artifact is fresh or stale.

    Returns: (status, is_fresh) where status is 'fresh' or 'stale'.
    """
    last = datetime.fromisoformat(artifact_date)
    age = (datetime.now() - last).days

    if age >= threshold_days:
        return "stale", False
    return "fresh", True


def check_process_compliance(artifacts: Dict[str, Optional[str]]) -> List[dict]:
    """Check for process violations based on phase dependencies.

    Returns a list of violation dicts with 'phase', 'missing', and 'severity'.
    """
    violations: List[dict] = []

    for phase, required_predecessor in PHASE_DEPENDENCIES.items():
        if artifacts.get(phase) is not None and artifacts.get(required_predecessor) is None:
            violations.append(
                {
                    "phase": phase,
                    "missing": required_predecessor,
                    "severity": "CRITICAL",
                    "message": f"Phase '{phase}' exists but required predecessor "
                    f"'{required_predecessor}' is missing",
                }
            )

    return violations


def assess_rollback(files_modified: int, has_migrations: bool = False) -> str:
    """Assess rollback complexity.

    Returns: 'git revert' | 'manual review' | 'migration rollback required'
    """
    if has_migrations:
        return "migration rollback required"
    if files_modified > 10:
        return "manual review"
    return "git revert"


# ---------------------------------------------------------------------------
# Tests: Compliance score
# ---------------------------------------------------------------------------


class TestComplianceScore:
    """Tests for calculate_compliance_score."""

    def test_compliance_score_all_present(self):
        """All artifacts present = 100% completeness."""
        artifacts = {
            "proposal": "content",
            "spec": "content",
            "design": "content",
            "tasks": "content",
            "apply": "content",
            "verify": "content",
        }
        score = calculate_compliance_score(artifacts)
        assert score == 100.0

    def test_compliance_score_missing_required(self):
        """Missing spec lowers the score."""
        artifacts = {
            "proposal": "content",
            "spec": None,
            "design": "content",
            "tasks": "content",
            "apply": "content",
            "verify": "content",
        }
        score = calculate_compliance_score(artifacts)
        assert score < 100.0
        # spec weight is 0.25, so score should be 75%
        assert score == 75.0

    def test_compliance_score_none_present(self):
        """No artifacts = 0%."""
        artifacts = {
            "proposal": None,
            "spec": None,
            "design": None,
            "tasks": None,
            "apply": None,
            "verify": None,
        }
        score = calculate_compliance_score(artifacts)
        assert score == 0.0

    @pytest.mark.parametrize(
        "missing,expected_reduction",
        [
            ("proposal", 15.0),
            ("spec", 25.0),
            ("design", 15.0),
            ("tasks", 20.0),
            ("apply", 15.0),
            ("verify", 10.0),
        ],
    )
    def test_individual_artifact_weight(self, missing: str, expected_reduction: float):
        """Each missing artifact reduces score by its weight percentage."""
        artifacts = {
            "proposal": "content",
            "spec": "content",
            "design": "content",
            "tasks": "content",
            "apply": "content",
            "verify": "content",
        }
        artifacts[missing] = None
        score = calculate_compliance_score(artifacts)
        assert score == 100.0 - expected_reduction


# ---------------------------------------------------------------------------
# Tests: Structural validation
# ---------------------------------------------------------------------------


class TestStructuralValidation:

    def test_structural_validation_pass(self):
        """Artifact with required sections and sufficient content passes."""
        content = (
            "## Overview\n"
            "This is a detailed proposal for the authentication system. "
            "It covers all the requirements and design considerations "
            "needed for implementation.\n\n"
            "## Requirements\n"
            "The system must support OAuth2 and JWT tokens.\n"
        )
        passed, reason = validate_structure(
            content, required_sections=["## Overview", "## Requirements"]
        )
        assert passed is True
        assert reason == "ok"

    def test_structural_validation_fail_empty(self):
        """Content <100 chars fails validation."""
        content = "Too short."
        passed, reason = validate_structure(content)
        assert passed is False
        assert "<100 chars" in reason

    def test_structural_validation_missing_section(self):
        """Missing required section fails validation."""
        content = (
            "## Overview\n"
            "This is a detailed proposal with sufficient length to pass "
            "the minimum character requirement for structural validation.\n"
        )
        passed, reason = validate_structure(
            content, required_sections=["## Overview", "## Requirements"]
        )
        assert passed is False
        assert "Requirements" in reason


# ---------------------------------------------------------------------------
# Tests: Freshness
# ---------------------------------------------------------------------------


class TestFreshness:

    def test_freshness_within_threshold(self):
        """Artifact <30 days old is fresh."""
        recent = (datetime.now() - timedelta(days=10)).isoformat()
        status, is_fresh = check_freshness(recent)
        assert status == "fresh"
        assert is_fresh is True

    def test_freshness_stale(self):
        """Artifact >=30 days old is stale."""
        old = (datetime.now() - timedelta(days=45)).isoformat()
        status, is_fresh = check_freshness(old)
        assert status == "stale"
        assert is_fresh is False

    @pytest.mark.parametrize(
        "days_ago,expected_status",
        [
            (0, "fresh"),
            (29, "fresh"),
            (30, "stale"),
            (90, "stale"),
        ],
    )
    def test_freshness_boundary(self, days_ago: int, expected_status: str):
        """Freshness boundary at 30 days."""
        date = (datetime.now() - timedelta(days=days_ago)).isoformat()
        status, _ = check_freshness(date)
        assert status == expected_status


# ---------------------------------------------------------------------------
# Tests: Process violations
# ---------------------------------------------------------------------------


class TestProcessViolations:

    def test_process_violation_skip_phase(self):
        """Spec exists without proposal = CRITICAL violation."""
        artifacts = {
            "proposal": None,
            "spec": "some spec content",
            "design": None,
            "tasks": None,
            "apply": None,
            "verify": None,
        }
        violations = check_process_compliance(artifacts)
        assert len(violations) >= 1
        assert any(
            v["phase"] == "spec" and v["severity"] == "CRITICAL"
            for v in violations
        )

    def test_process_violation_no_verify(self):
        """Archive without verify = CRITICAL violation."""
        artifacts = {
            "proposal": "content",
            "spec": "content",
            "design": "content",
            "tasks": "content",
            "apply": "content",
            "verify": None,
            "archive": "content",
        }
        violations = check_process_compliance(artifacts)
        assert any(
            v["phase"] == "archive"
            and v["missing"] == "verify"
            and v["severity"] == "CRITICAL"
            for v in violations
        )

    def test_no_violations_when_ordered(self):
        """Properly ordered artifacts produce no violations."""
        artifacts = {
            "proposal": "content",
            "spec": "content",
            "design": "content",
            "tasks": "content",
            "apply": "content",
            "verify": "content",
        }
        violations = check_process_compliance(artifacts)
        assert violations == []


# ---------------------------------------------------------------------------
# Tests: Rollback assessment
# ---------------------------------------------------------------------------


class TestRollbackAssessment:

    def test_rollback_assessment_simple(self):
        """Few files modified = 'git revert'."""
        assert assess_rollback(files_modified=3) == "git revert"

    def test_rollback_assessment_complex(self):
        """Many files modified = 'manual review'."""
        assert assess_rollback(files_modified=25) == "manual review"

    def test_rollback_with_migrations(self):
        """Migrations present = 'migration rollback required'."""
        assert assess_rollback(files_modified=2, has_migrations=True) == "migration rollback required"

    @pytest.mark.parametrize(
        "files,migrations,expected",
        [
            (1, False, "git revert"),
            (10, False, "git revert"),
            (11, False, "manual review"),
            (50, False, "manual review"),
            (1, True, "migration rollback required"),
            (50, True, "migration rollback required"),
        ],
    )
    def test_rollback_parametrized(
        self, files: int, migrations: bool, expected: str
    ):
        """Rollback assessment across various scenarios."""
        assert assess_rollback(files, migrations) == expected


# ---------------------------------------------------------------------------
# Tests: Health classification
# ---------------------------------------------------------------------------


class TestHealthClassification:

    def test_classification_healthy(self):
        """Score >=85% = HEALTHY."""
        assert classify_health(85.0) == "HEALTHY"
        assert classify_health(100.0) == "HEALTHY"

    def test_classification_warning(self):
        """Score 50-84% = WARNING."""
        assert classify_health(50.0) == "WARNING"
        assert classify_health(84.9) == "WARNING"

    def test_classification_critical(self):
        """Score <50% = CRITICAL."""
        assert classify_health(49.9) == "CRITICAL"
        assert classify_health(0.0) == "CRITICAL"

    @pytest.mark.parametrize(
        "score,expected",
        [
            (100.0, "HEALTHY"),
            (85.0, "HEALTHY"),
            (84.9, "WARNING"),
            (50.0, "WARNING"),
            (49.9, "CRITICAL"),
            (0.0, "CRITICAL"),
        ],
    )
    def test_classification_boundaries(self, score: float, expected: str):
        """Health classification at boundary values."""
        assert classify_health(score) == expected


# ---------------------------------------------------------------------------
# Tests: Governance is read-only
# ---------------------------------------------------------------------------


class TestGovernanceReadOnly:

    def test_governance_is_readonly(self, tmp_path):
        """Governance functions do not modify any files or state."""
        # Create a sentinel file
        sentinel = tmp_path / "sentinel.txt"
        sentinel.write_text("original")

        # Run all governance functions
        artifacts = {
            "proposal": "content",
            "spec": "content",
            "design": "content",
            "tasks": "content",
            "apply": "content",
            "verify": "content",
        }

        calculate_compliance_score(artifacts)
        classify_health(85.0)
        assess_rollback(5)
        check_process_compliance(artifacts)
        validate_structure("x" * 200)
        check_freshness(datetime.now().isoformat())

        # Verify sentinel is untouched
        assert sentinel.read_text() == "original"
