"""Behavior tests for security audit infrastructure.

Validates that the security-audit skill, agent-security rule,
pentesting-readiness rule, and permission system are properly
configured and documented.

Python 3.9+ compatible. Author: luum.
"""

import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RULES_DIR = PROJECT_ROOT / "rules"
SKILLS_DIR = PROJECT_ROOT / "skills"
LIB_DIR = PROJECT_ROOT / "lib"


# ---------------------------------------------------------------------------
# Skill existence and structure
# ---------------------------------------------------------------------------


class TestSecurityAuditSkill:
    """Tests that the security-audit skill is properly structured."""

    def test_security_audit_skill_exists(self):
        """security-audit/SKILL.md should exist."""
        skill_path = SKILLS_DIR / "security-audit" / "SKILL.md"
        assert skill_path.exists(), f"Missing: {skill_path}"

    def test_skill_has_frontmatter(self):
        """SKILL.md should contain YAML frontmatter with required fields."""
        content = (SKILLS_DIR / "security-audit" / "SKILL.md").read_text()
        assert "---" in content
        assert "name: security-audit" in content
        assert "version:" in content
        assert "description:" in content

    def test_skill_has_secret_scanning_step(self):
        """Skill should include a step for scanning exposed secrets."""
        content = (SKILLS_DIR / "security-audit" / "SKILL.md").read_text()
        assert "secret" in content.lower() or "api" in content.lower()
        assert "scan" in content.lower() or "search" in content.lower()

    def test_skill_has_permission_review_step(self):
        """Skill should include a step for reviewing agent permissions."""
        content = (SKILLS_DIR / "security-audit" / "SKILL.md").read_text()
        assert "permission" in content.lower()


# ---------------------------------------------------------------------------
# Rules existence
# ---------------------------------------------------------------------------


class TestSecurityRules:
    """Tests that security rules exist and are documented."""

    def test_agent_security_rule_exists(self):
        """rules/agent-security.md should exist."""
        rule_path = RULES_DIR / "agent-security.md"
        assert rule_path.exists(), f"Missing: {rule_path}"

    def test_pentesting_readiness_rule_exists(self):
        """rules/pentesting-readiness.md should exist."""
        rule_path = RULES_DIR / "pentesting-readiness.md"
        assert rule_path.exists(), f"Missing: {rule_path}"

    def test_always_blocked_paths_documented(self):
        """agent-security.md should document always-blocked paths."""
        content = (RULES_DIR / "agent-security.md").read_text()
        assert ".env" in content
        assert "*.key" in content
        assert "*.pem" in content
        assert "secrets/" in content

    def test_monotonic_attenuation_documented(self):
        """agent-security.md should document monotonic attenuation."""
        content = (RULES_DIR / "agent-security.md").read_text()
        assert "monotonic" in content.lower() or "attenuation" in content.lower()

    def test_permission_profiles_documented(self):
        """agent-security.md should document permission profiles."""
        content = (RULES_DIR / "agent-security.md").read_text()
        assert "readonly" in content
        assert "documentation" in content
        assert "implementation" in content
        assert "sdd_phase" in content
        assert "security_audit" in content


# ---------------------------------------------------------------------------
# Permission system integration
# ---------------------------------------------------------------------------


class TestPermissionSystemIntegration:
    """Tests that the permission system module exists and is importable."""

    def test_agent_permissions_module_exists(self):
        """lib/agent_permissions.py should exist."""
        mod_path = LIB_DIR / "agent_permissions.py"
        assert mod_path.exists(), f"Missing: {mod_path}"

    def test_agent_permissions_importable(self):
        """Module should be importable without errors."""
        from lib.agent_permissions import (
            AgentPermissionManager,
            PermissionLevel,
            PERMISSION_PROFILES,
            get_profile_for_task,
            grant_from_profile,
        )
        assert PermissionLevel.ADMIN.value == 5
        assert "readonly" in PERMISSION_PROFILES
        assert callable(get_profile_for_task)

    def test_always_blocked_in_code_matches_docs(self):
        """ALWAYS_BLOCKED in code should match what's documented."""
        from lib.agent_permissions import AgentPermissionManager

        blocked = AgentPermissionManager.ALWAYS_BLOCKED
        assert ".env" in blocked
        assert "*.key" in blocked
        assert "*.pem" in blocked
        assert "*.p12" in blocked
        assert ".git/config" in blocked
