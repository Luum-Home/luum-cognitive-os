"""Unit tests for lib/agent_permissions.py

Validates agent permission grants, access checks, path blocking,
time expiration, monotonic attenuation, audit trails, and profiles.

Python 3.9+ compatible. Author: luum.
"""

from datetime import datetime, timedelta, timezone

import pytest

from lib.agent_permissions import (
    PERMISSION_PROFILES,
    AccessLog,
    AgentPermissionManager,
    PermissionGrant,
    PermissionLevel,
    get_profile_for_task,
    grant_from_profile,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mgr() -> AgentPermissionManager:
    """Create a fresh permission manager (no disk I/O)."""
    return AgentPermissionManager(audit_log_path="/tmp/test-audit.jsonl")


@pytest.fixture
def granted_agent(mgr: AgentPermissionManager) -> str:
    """Grant a standard write agent and return its id."""
    agent_id = "test-agent-001"
    mgr.grant(
        agent_id=agent_id,
        task="fix documentation",
        paths=["docs/*.md", "README.md"],
        tools=["Read", "Edit", "Glob"],
        level=PermissionLevel.WRITE,
        ttl_minutes=30,
    )
    return agent_id


# ---------------------------------------------------------------------------
# Grant creation
# ---------------------------------------------------------------------------


class TestGrant:
    """Tests for permission grant creation."""

    def test_grant_creates_permission_with_ttl(self, mgr: AgentPermissionManager):
        """Grant should create a permission with a future expiry."""
        grant = mgr.grant(
            agent_id="agent-1",
            task="test task",
            paths=["src/*.py"],
            tools=["Read"],
            level=PermissionLevel.READ,
            ttl_minutes=15,
        )
        assert grant.agent_id == "agent-1"
        assert grant.level == PermissionLevel.READ
        assert grant.expires_at > datetime.now(timezone.utc)
        assert grant.task_description == "test task"

    def test_grant_ttl_capped_at_120(self, mgr: AgentPermissionManager):
        """TTL should be capped at 120 minutes regardless of input."""
        grant = mgr.grant(
            agent_id="agent-long",
            task="long task",
            paths=["**/*"],
            tools=["Read"],
            ttl_minutes=999,
        )
        max_expected = datetime.now(timezone.utc) + timedelta(minutes=121)
        assert grant.expires_at < max_expected

    def test_grant_includes_always_blocked(self, mgr: AgentPermissionManager):
        """Grant should always include ALWAYS_BLOCKED in blocked_paths."""
        grant = mgr.grant(
            agent_id="agent-x",
            task="task",
            paths=["**/*"],
            tools=["Read"],
        )
        assert ".env" in grant.blocked_paths
        assert "*.key" in grant.blocked_paths
        assert "*.pem" in grant.blocked_paths

    def test_grant_with_extra_blocked(self, mgr: AgentPermissionManager):
        """Grant should merge blocked_extra with ALWAYS_BLOCKED."""
        grant = mgr.grant(
            agent_id="agent-y",
            task="task",
            paths=["**/*"],
            tools=["Read"],
            blocked_extra=["hooks/*", "rules/*"],
        )
        assert "hooks/*" in grant.blocked_paths
        assert "rules/*" in grant.blocked_paths
        assert ".env" in grant.blocked_paths


# ---------------------------------------------------------------------------
# Access checks
# ---------------------------------------------------------------------------


class TestCheck:
    """Tests for permission check logic."""

    def test_check_allows_permitted_path(
        self, mgr: AgentPermissionManager, granted_agent: str
    ):
        """Should allow access to a path matching allowed_paths."""
        assert mgr.check(granted_agent, "write", "docs/setup.md") is True

    def test_check_blocks_unpermitted_path(
        self, mgr: AgentPermissionManager, granted_agent: str
    ):
        """Should deny access to a path not in allowed_paths."""
        assert mgr.check(granted_agent, "write", "src/main.py") is False

    def test_check_blocks_always_blocked_env(
        self, mgr: AgentPermissionManager
    ):
        """Should deny access to .env even with **/* allowed."""
        mgr.grant(
            agent_id="wide-agent",
            task="broad task",
            paths=["**/*"],
            tools=["Read", "Write"],
            level=PermissionLevel.ADMIN,
        )
        assert mgr.check("wide-agent", "read", ".env") is False

    def test_check_blocks_always_blocked_key(
        self, mgr: AgentPermissionManager
    ):
        """Should deny access to *.key files."""
        mgr.grant(
            agent_id="key-agent",
            task="task",
            paths=["**/*"],
            tools=["Read"],
            level=PermissionLevel.ADMIN,
        )
        assert mgr.check("key-agent", "read", "certs/server.key") is False

    def test_check_blocks_always_blocked_pem(
        self, mgr: AgentPermissionManager
    ):
        """Should deny access to *.pem files."""
        mgr.grant(
            agent_id="pem-agent",
            task="task",
            paths=["**/*"],
            tools=["Read"],
            level=PermissionLevel.ADMIN,
        )
        assert mgr.check("pem-agent", "read", "tls/cert.pem") is False

    def test_check_denies_insufficient_level(
        self, mgr: AgentPermissionManager
    ):
        """READ-level agent should be denied WRITE action."""
        mgr.grant(
            agent_id="reader",
            task="read only",
            paths=["docs/*.md"],
            tools=["Read"],
            level=PermissionLevel.READ,
        )
        assert mgr.check("reader", "write", "docs/README.md") is False

    def test_check_denies_no_grant(self, mgr: AgentPermissionManager):
        """Agent without any grant should be denied."""
        assert mgr.check("unknown-agent", "read", "file.txt") is False

    def test_always_blocked_overrides_allowed_paths(
        self, mgr: AgentPermissionManager
    ):
        """ALWAYS_BLOCKED should take precedence over allowed_paths."""
        mgr.grant(
            agent_id="env-seeker",
            task="try to read env",
            paths=[".env", "**/*"],
            tools=["Read"],
            level=PermissionLevel.ADMIN,
        )
        assert mgr.check("env-seeker", "read", ".env") is False

    def test_admin_allows_non_blocked_path(
        self, mgr: AgentPermissionManager
    ):
        """ADMIN level should allow everything except always-blocked."""
        mgr.grant(
            agent_id="admin-agent",
            task="admin work",
            paths=["**/*"],
            tools=["Read", "Write", "Bash"],
            level=PermissionLevel.ADMIN,
        )
        assert mgr.check("admin-agent", "write", "src/main.py") is True
        assert mgr.check("admin-agent", "execute", "scripts/build.sh") is True

    def test_empty_paths_denies_everything(
        self, mgr: AgentPermissionManager
    ):
        """Agent with empty paths list should be denied access to all files."""
        mgr.grant(
            agent_id="no-paths",
            task="empty paths",
            paths=[],
            tools=["Read"],
            level=PermissionLevel.READ,
        )
        assert mgr.check("no-paths", "read", "any-file.txt") is False


# ---------------------------------------------------------------------------
# Expiration
# ---------------------------------------------------------------------------


class TestExpiration:
    """Tests for time-based permission expiry."""

    def test_expired_permission_auto_denied(
        self, mgr: AgentPermissionManager
    ):
        """Expired grant should be automatically denied."""
        mgr.grant(
            agent_id="expiring",
            task="short task",
            paths=["**/*"],
            tools=["Read"],
            level=PermissionLevel.READ,
            ttl_minutes=0,  # expires immediately (actually uses min value)
        )
        # Force expiry by manipulating the grant
        mgr.grants["expiring"].expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        assert mgr.check("expiring", "read", "file.txt") is False
        # Grant should be removed after failed check
        assert "expiring" not in mgr.grants

    def test_cleanup_expired_removes_old_grants(
        self, mgr: AgentPermissionManager
    ):
        """cleanup_expired should remove all expired grants."""
        mgr.grant("a1", "task1", ["**/*"], ["Read"], ttl_minutes=5)
        mgr.grant("a2", "task2", ["**/*"], ["Read"], ttl_minutes=5)
        # Expire both
        for g in mgr.grants.values():
            g.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        removed = mgr.cleanup_expired()
        assert removed == 2
        assert len(mgr.grants) == 0


# ---------------------------------------------------------------------------
# Revocation
# ---------------------------------------------------------------------------


class TestRevocation:
    """Tests for permission revocation."""

    def test_revoke_removes_all_grants_for_agent(
        self, mgr: AgentPermissionManager, granted_agent: str
    ):
        """Revoke should remove the agent's grant entirely."""
        mgr.revoke(granted_agent)
        assert granted_agent not in mgr.grants

    def test_revoke_all_clears_everything(
        self, mgr: AgentPermissionManager
    ):
        """revoke_all should remove all grants and return count."""
        mgr.grant("a1", "t1", ["**/*"], ["Read"])
        mgr.grant("a2", "t2", ["**/*"], ["Read"])
        mgr.grant("a3", "t3", ["**/*"], ["Read"])
        count = mgr.revoke_all()
        assert count == 3
        assert len(mgr.grants) == 0


# ---------------------------------------------------------------------------
# Monotonic attenuation (child grants)
# ---------------------------------------------------------------------------


class TestMonotonicAttenuation:
    """Tests for parent-child permission inheritance."""

    def test_child_cannot_exceed_parent_level(
        self, mgr: AgentPermissionManager
    ):
        """Child level should be capped at parent level."""
        mgr.grant(
            "parent",
            "parent task",
            ["src/**"],
            ["Read", "Edit"],
            level=PermissionLevel.WRITE,
        )
        child = mgr.create_child_grant(
            parent_id="parent",
            child_id="child",
            task="child task",
            level=PermissionLevel.ADMIN,  # should be capped
        )
        assert child is not None
        assert child.level == PermissionLevel.WRITE

    def test_child_tools_subset_of_parent(
        self, mgr: AgentPermissionManager
    ):
        """Child should only get tools the parent has."""
        mgr.grant(
            "parent",
            "parent task",
            ["**/*"],
            ["Read", "Edit"],
            level=PermissionLevel.WRITE,
        )
        child = mgr.create_child_grant(
            parent_id="parent",
            child_id="child",
            task="child task",
            tools=["Read", "Edit", "Bash"],  # Bash not in parent
        )
        assert child is not None
        assert "Bash" not in child.allowed_tools
        assert "Read" in child.allowed_tools
        assert "Edit" in child.allowed_tools

    def test_child_grant_returns_none_without_parent(
        self, mgr: AgentPermissionManager
    ):
        """Should return None if parent has no grant."""
        result = mgr.create_child_grant("nonexistent", "child", "task")
        assert result is None

    def test_child_inherits_blocked_paths(
        self, mgr: AgentPermissionManager
    ):
        """Child should inherit all parent blocked paths."""
        mgr.grant(
            "parent",
            "task",
            ["**/*"],
            ["Read"],
            blocked_extra=["config/*"],
        )
        child = mgr.create_child_grant("parent", "child", "child task")
        assert child is not None
        assert ".env" in child.blocked_paths  # from ALWAYS_BLOCKED


# ---------------------------------------------------------------------------
# Audit trail
# ---------------------------------------------------------------------------


class TestAuditTrail:
    """Tests for access audit logging."""

    def test_audit_trail_records_all_checks(
        self, mgr: AgentPermissionManager, granted_agent: str
    ):
        """Every check should produce an audit log entry."""
        mgr.check(granted_agent, "write", "docs/setup.md")  # allowed
        mgr.check(granted_agent, "write", "src/main.py")  # denied
        trail = mgr.get_audit_trail()
        assert len(trail) == 2
        assert trail[0].granted is True
        assert trail[1].granted is False

    def test_audit_trail_filtered_by_agent(
        self, mgr: AgentPermissionManager
    ):
        """get_audit_trail with agent_id should filter entries."""
        mgr.grant("a1", "t1", ["**/*"], ["Read"], level=PermissionLevel.READ)
        mgr.grant("a2", "t2", ["**/*"], ["Read"], level=PermissionLevel.READ)
        mgr.check("a1", "read", "file1.txt")
        mgr.check("a2", "read", "file2.txt")
        mgr.check("a1", "read", "file3.txt")
        trail_a1 = mgr.get_audit_trail(agent_id="a1")
        assert len(trail_a1) == 2
        assert all(entry.agent_id == "a1" for entry in trail_a1)


# ---------------------------------------------------------------------------
# Permission profiles
# ---------------------------------------------------------------------------


class TestPermissionProfiles:
    """Tests for pre-built permission profiles."""

    def test_readonly_blocks_write(self, mgr: AgentPermissionManager):
        """Readonly profile should deny write actions."""
        grant_from_profile(mgr, "ro-agent", "research topic", "readonly")
        assert mgr.check("ro-agent", "read", "src/main.py") is True
        assert mgr.check("ro-agent", "write", "src/main.py") is False

    def test_documentation_allows_docs_md(
        self, mgr: AgentPermissionManager
    ):
        """Documentation profile should allow docs/*.md."""
        grant_from_profile(mgr, "doc-agent", "update docs", "documentation")
        assert mgr.check("doc-agent", "write", "docs/guide.md") is True

    def test_implementation_blocks_hooks(
        self, mgr: AgentPermissionManager
    ):
        """Implementation profile should block hooks/ directory."""
        grant_from_profile(mgr, "impl-agent", "implement feature", "implementation")
        assert mgr.check("impl-agent", "write", "hooks/my-hook.sh") is False

    def test_sdd_phase_allows_agent_tool(
        self, mgr: AgentPermissionManager
    ):
        """SDD phase profile should include Agent tool."""
        grant_from_profile(mgr, "sdd-agent", "run sdd-apply", "sdd_phase")
        assert mgr.check_tool_allowed("sdd-agent", "Agent") is True

    def test_security_audit_is_read_level(
        self, mgr: AgentPermissionManager
    ):
        """Security audit profile should be READ level."""
        grant_from_profile(mgr, "sec-agent", "security scan", "security_audit")
        grant = mgr.grants["sec-agent"]
        assert grant.level == PermissionLevel.READ


# ---------------------------------------------------------------------------
# Profile auto-detection
# ---------------------------------------------------------------------------


class TestProfileAutoDetection:
    """Tests for get_profile_for_task routing."""

    def test_security_task_routes_to_security_audit(self):
        assert get_profile_for_task("review security configuration") == "security_audit"

    def test_sdd_task_routes_to_sdd_phase(self):
        assert get_profile_for_task("run sdd-apply for auth feature") == "sdd_phase"

    def test_doc_task_routes_to_documentation(self):
        assert get_profile_for_task("fix typo in README") == "documentation"

    def test_research_task_routes_to_readonly(self):
        assert get_profile_for_task("research this topic") == "readonly"

    def test_generic_task_routes_to_implementation(self):
        assert get_profile_for_task("implement auth endpoint") == "implementation"


# ---------------------------------------------------------------------------
# Path matching
# ---------------------------------------------------------------------------


class TestPathMatching:
    """Tests for glob pattern matching in check_path_allowed."""

    def test_check_path_allowed_with_glob(
        self, mgr: AgentPermissionManager
    ):
        """Should match glob patterns like docs/*.md."""
        mgr.grant("glob-agent", "task", ["docs/*.md"], ["Read"])
        assert mgr.check_path_allowed("glob-agent", "docs/guide.md") is True
        assert mgr.check_path_allowed("glob-agent", "src/main.py") is False

    def test_check_path_allowed_blocked_wins(
        self, mgr: AgentPermissionManager
    ):
        """Blocked paths should override allowed paths."""
        mgr.grant("block-test", "task", ["**/*"], ["Read"])
        assert mgr.check_path_allowed("block-test", ".env") is False

    def test_check_path_allowed_no_grant(
        self, mgr: AgentPermissionManager
    ):
        """Should return False if agent has no grant."""
        assert mgr.check_path_allowed("nobody", "file.txt") is False


# ---------------------------------------------------------------------------
# Format summary
# ---------------------------------------------------------------------------


class TestFormatSummary:
    """Tests for human-readable permission summary."""

    def test_format_permission_summary_active(
        self, mgr: AgentPermissionManager, granted_agent: str
    ):
        """Should produce a multi-line summary for an active grant."""
        summary = mgr.format_permission_summary(granted_agent)
        assert "WRITE" in summary
        assert "fix documentation" in summary
        assert "Read" in summary

    def test_format_permission_summary_no_grant(
        self, mgr: AgentPermissionManager
    ):
        """Should indicate no permissions for unknown agent."""
        summary = mgr.format_permission_summary("ghost")
        assert "no active permissions" in summary


# ---------------------------------------------------------------------------
# Concurrent grants
# ---------------------------------------------------------------------------


class TestConcurrentGrants:
    """Tests for multiple agents with different grants."""

    def test_concurrent_grants_for_different_agents(
        self, mgr: AgentPermissionManager
    ):
        """Multiple agents should have independent grants."""
        mgr.grant("agent-a", "task-a", ["src/*"], ["Read"], level=PermissionLevel.READ)
        mgr.grant("agent-b", "task-b", ["docs/*"], ["Edit"], level=PermissionLevel.WRITE)

        assert mgr.check("agent-a", "read", "src/main.py") is True
        assert mgr.check("agent-a", "read", "docs/guide.md") is False
        assert mgr.check("agent-b", "write", "docs/guide.md") is True
        assert mgr.check("agent-b", "write", "src/main.py") is False


# ---------------------------------------------------------------------------
# Tool checking
# ---------------------------------------------------------------------------


class TestToolAllowed:
    """Tests for tool-level permission checks."""

    def test_check_tool_allowed_granted(
        self, mgr: AgentPermissionManager, granted_agent: str
    ):
        """Should allow tools in the grant's allowed_tools list."""
        assert mgr.check_tool_allowed(granted_agent, "Read") is True
        assert mgr.check_tool_allowed(granted_agent, "Edit") is True

    def test_check_tool_blocked(
        self, mgr: AgentPermissionManager, granted_agent: str
    ):
        """Should deny tools not in allowed_tools."""
        assert mgr.check_tool_allowed(granted_agent, "Bash") is False

    def test_check_tool_no_grant(self, mgr: AgentPermissionManager):
        """Should deny all tools for agent without grant."""
        assert mgr.check_tool_allowed("nobody", "Read") is False
