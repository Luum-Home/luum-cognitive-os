# SCOPE: both
# scope: both
"""Agent Permission System — Least Privilege Access Control.

Provides scoped, time-limited permissions for sub-agents with audit logging.
Every agent gets ONLY the access needed for its specific task, with automatic
expiration and always-blocked paths for sensitive files.

Usage:
    from lib.agent_permissions import AgentPermissionManager, PermissionLevel

    mgr = AgentPermissionManager()
    grant = mgr.grant("agent-123", "fix docs", paths=["docs/*.md"],
                       tools=["Read", "Edit"], level=PermissionLevel.WRITE)
    allowed = mgr.check("agent-123", "write", "docs/README.md")
    mgr.revoke("agent-123")

Python 3.9+ compatible. Author: luum.
"""

import fnmatch
import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class PermissionLevel(Enum):
    """Permission levels ordered by increasing access."""

    NONE = 0  # No access
    READ = 1  # Read only
    SUGGEST = 2  # Can suggest changes (dry-run)
    WRITE = 3  # Can modify files
    EXECUTE = 4  # Can run commands
    ADMIN = 5  # Full access (orchestrator only)


@dataclass
class PermissionGrant:
    """A scoped, time-limited permission grant for an agent."""

    agent_id: str
    level: PermissionLevel
    allowed_paths: List[str]  # glob patterns: ["README.md", "docs/*.md"]
    blocked_paths: List[str]  # always blocked: [".env", "*.key", "secrets/*"]
    allowed_tools: List[str]  # ["Read", "Edit"] — no Bash
    expires_at: datetime  # auto-expire
    granted_by: str  # who granted (orchestrator, human)
    task_description: str  # why this access was granted


@dataclass
class AccessLog:
    """An audit trail entry for a permission check."""

    timestamp: datetime
    agent_id: str
    action: str  # read, write, execute, denied
    target: str  # file path or command
    permission_level: PermissionLevel
    granted: bool
    reason: str  # why granted or denied


# Action -> minimum required PermissionLevel
_ACTION_LEVELS: Dict[str, PermissionLevel] = {
    "read": PermissionLevel.READ,
    "suggest": PermissionLevel.SUGGEST,
    "write": PermissionLevel.WRITE,
    "execute": PermissionLevel.EXECUTE,
    "admin": PermissionLevel.ADMIN,
}

# Tools -> action mapping
_TOOL_ACTIONS: Dict[str, str] = {
    "Read": "read",
    "Glob": "read",
    "Grep": "read",
    "WebSearch": "read",
    "WebFetch": "read",
    "Write": "write",
    "Edit": "write",
    "Bash": "execute",
    "Agent": "execute",
}


class AgentPermissionManager:
    """Manages scoped, time-limited permissions for agents."""

    # Paths that are ALWAYS blocked regardless of grants
    ALWAYS_BLOCKED: List[str] = [
        ".env",
        ".env.*",
        "*.key",
        "*.pem",
        "*.p12",
        "secrets/*",
        "**/credentials*",
        "**/password*",
        ".git/config",
    ]

    def __init__(
        self,
        audit_log_path: str = ".cognitive-os/metrics/access-audit.jsonl",
    ) -> None:
        self.grants: Dict[str, PermissionGrant] = {}
        self.audit_log_path = audit_log_path
        self._audit_buffer: List[AccessLog] = []

    def grant(
        self,
        agent_id: str,
        task: str,
        paths: List[str],
        tools: List[str],
        level: PermissionLevel = PermissionLevel.WRITE,
        ttl_minutes: int = 30,
        granted_by: str = "orchestrator",
        blocked_extra: Optional[List[str]] = None,
    ) -> PermissionGrant:
        """Grant scoped, time-limited permissions to an agent.

        Args:
            agent_id: Unique identifier for the agent.
            task: Description of the task requiring access.
            paths: Glob patterns for allowed file paths.
            tools: List of tool names the agent may use.
            level: Maximum permission level.
            ttl_minutes: Minutes until grant expires (max 120).
            granted_by: Who granted the permission.
            blocked_extra: Additional blocked paths beyond ALWAYS_BLOCKED.

        Returns:
            The created PermissionGrant.
        """
        ttl_minutes = min(ttl_minutes, 120)
        blocked = list(self.ALWAYS_BLOCKED)
        if blocked_extra:
            blocked.extend(blocked_extra)

        grant = PermissionGrant(
            agent_id=agent_id,
            level=level,
            allowed_paths=list(paths),
            blocked_paths=blocked,
            allowed_tools=list(tools),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes),
            granted_by=granted_by,
            task_description=task,
        )
        self.grants[agent_id] = grant
        return grant

    def check(self, agent_id: str, action: str, target: str) -> bool:
        """Check if agent has permission for an action on a target.

        Logs the check to the audit trail. Returns True if allowed.
        """
        self.cleanup_expired()

        grant = self.grants.get(agent_id)

        # No grant at all
        if grant is None:
            self._log_access(agent_id, action, target, PermissionLevel.NONE, False, "no grant found")
            return False

        # Grant expired
        if datetime.now(timezone.utc) >= grant.expires_at:
            self._log_access(agent_id, action, target, grant.level, False, "grant expired")
            del self.grants[agent_id]
            return False

        # Check permission level
        required_level = _ACTION_LEVELS.get(action, PermissionLevel.ADMIN)
        if grant.level.value < required_level.value:
            self._log_access(
                agent_id,
                action,
                target,
                grant.level,
                False,
                f"insufficient level: {grant.level.name} < {required_level.name}",
            )
            return False

        # Check always-blocked paths
        if self._matches_any_pattern(target, grant.blocked_paths):
            self._log_access(agent_id, action, target, grant.level, False, "path is always-blocked")
            return False

        # Check path allowed
        if not self._matches_any_pattern(target, grant.allowed_paths):
            self._log_access(agent_id, action, target, grant.level, False, "path not in allowed_paths")
            return False

        self._log_access(agent_id, action, target, grant.level, True, "permitted")
        return True

    def check_tool_allowed(self, agent_id: str, tool_name: str) -> bool:
        """Check if an agent is allowed to use a specific tool."""
        grant = self.grants.get(agent_id)
        if grant is None:
            return False
        if datetime.now(timezone.utc) >= grant.expires_at:
            return False
        return tool_name in grant.allowed_tools

    def check_path_allowed(self, agent_id: str, path: str) -> bool:
        """Check if path matches allowed_paths and doesn't match blocked_paths.

        Uses fnmatch for glob pattern matching.
        """
        grant = self.grants.get(agent_id)
        if grant is None:
            return False

        if self._matches_any_pattern(path, grant.blocked_paths):
            return False

        return self._matches_any_pattern(path, grant.allowed_paths)

    def revoke(self, agent_id: str) -> None:
        """Revoke all permissions for an agent (task complete or expired)."""
        if agent_id in self.grants:
            del self.grants[agent_id]

    def revoke_all(self) -> int:
        """Revoke all grants (session cleanup). Returns count revoked."""
        count = len(self.grants)
        self.grants.clear()
        return count

    def cleanup_expired(self) -> int:
        """Remove expired grants. Returns count cleaned."""
        now = datetime.now(timezone.utc)
        expired = [
            aid for aid, g in self.grants.items() if now >= g.expires_at
        ]
        for aid in expired:
            del self.grants[aid]
        return len(expired)

    def get_audit_trail(self, agent_id: Optional[str] = None) -> List[AccessLog]:
        """Get audit trail, optionally filtered by agent."""
        if agent_id is None:
            return list(self._audit_buffer)
        return [log for log in self._audit_buffer if log.agent_id == agent_id]

    def format_permission_summary(self, agent_id: str) -> str:
        """Human-readable summary of what an agent can do."""
        grant = self.grants.get(agent_id)
        if grant is None:
            return f"Agent '{agent_id}': no active permissions."

        now = datetime.now(timezone.utc)
        remaining = grant.expires_at - now
        if remaining.total_seconds() <= 0:
            return f"Agent '{agent_id}': permissions expired."

        minutes_left = int(remaining.total_seconds() / 60)
        lines = [
            f"Agent '{agent_id}' — {grant.level.name} access",
            f"  Task: {grant.task_description}",
            f"  Tools: {', '.join(grant.allowed_tools)}",
            f"  Paths: {', '.join(grant.allowed_paths)}",
            f"  Granted by: {grant.granted_by}",
            f"  Expires in: {minutes_left} minutes",
        ]
        return "\n".join(lines)

    def create_child_grant(
        self,
        parent_id: str,
        child_id: str,
        task: str,
        paths: Optional[List[str]] = None,
        tools: Optional[List[str]] = None,
        level: Optional[PermissionLevel] = None,
        ttl_minutes: int = 30,
    ) -> Optional[PermissionGrant]:
        """Create a child grant that is AT MOST as permissive as the parent.

        Implements monotonic attenuation: child cannot exceed parent permissions.
        Returns None if parent has no grant.
        """
        parent = self.grants.get(parent_id)
        if parent is None:
            return None

        # Child level cannot exceed parent level
        child_level = level if level is not None else parent.level
        if child_level.value > parent.level.value:
            child_level = parent.level

        # Child tools must be subset of parent tools
        child_tools = tools if tools is not None else list(parent.allowed_tools)
        child_tools = [t for t in child_tools if t in parent.allowed_tools]

        # Child paths must be subset of parent paths (intersection)
        child_paths = paths if paths is not None else list(parent.allowed_paths)
        if paths is not None:
            # Only keep child paths that match at least one parent path
            filtered = []
            for cp in child_paths:
                for pp in parent.allowed_paths:
                    if fnmatch.fnmatch(cp, pp) or cp == pp:
                        filtered.append(cp)
                        break
            child_paths = filtered if filtered else child_paths

        # Child TTL cannot exceed parent remaining time
        now = datetime.now(timezone.utc)
        parent_remaining = (parent.expires_at - now).total_seconds() / 60
        child_ttl = min(ttl_minutes, max(1, int(parent_remaining)))

        # Inherit parent blocked paths
        return self.grant(
            agent_id=child_id,
            task=task,
            paths=child_paths,
            tools=child_tools,
            level=child_level,
            ttl_minutes=child_ttl,
            granted_by=f"agent:{parent_id}",
            blocked_extra=list(
                set(parent.blocked_paths) - set(self.ALWAYS_BLOCKED)
            ),
        )

    def flush_audit_log(self) -> int:
        """Write buffered audit entries to the JSONL file. Returns count written."""
        if not self._audit_buffer:
            return 0

        os.makedirs(os.path.dirname(self.audit_log_path), exist_ok=True)
        count = 0
        with open(self.audit_log_path, "a", encoding="utf-8") as f:
            for entry in self._audit_buffer:
                record = {
                    "timestamp": entry.timestamp.isoformat(),
                    "agent_id": entry.agent_id,
                    "action": entry.action,
                    "target": entry.target,
                    "permission_level": entry.permission_level.name,
                    "granted": entry.granted,
                    "reason": entry.reason,
                }
                f.write(json.dumps(record) + "\n")
                count += 1
        self._audit_buffer.clear()
        return count

    # ---- internal helpers ----

    def _matches_any_pattern(self, path: str, patterns: List[str]) -> bool:
        """Check if path matches any of the glob patterns."""
        basename = os.path.basename(path)
        for pattern in patterns:
            if fnmatch.fnmatch(path, pattern):
                return True
            if fnmatch.fnmatch(basename, pattern):
                return True
            # Handle ** patterns by checking if the path contains the suffix
            if pattern.startswith("**/"):
                suffix = pattern[3:]
                if fnmatch.fnmatch(basename, suffix):
                    return True
        return False

    def _log_access(
        self,
        agent_id: str,
        action: str,
        target: str,
        level: PermissionLevel,
        granted: bool,
        reason: str,
    ) -> None:
        """Add an entry to the audit buffer."""
        self._audit_buffer.append(
            AccessLog(
                timestamp=datetime.now(timezone.utc),
                agent_id=agent_id,
                action=action,
                target=target,
                permission_level=level,
                granted=granted,
                reason=reason,
            )
        )


# ---------------------------------------------------------------------------
# Pre-built permission profiles
# ---------------------------------------------------------------------------

PERMISSION_PROFILES: Dict[str, Dict[str, Any]] = {
    "readonly": {
        "level": PermissionLevel.READ,
        "tools": ["Read", "Glob", "Grep"],
        "paths": ["**/*"],
        "ttl_minutes": 60,
    },
    "documentation": {
        "level": PermissionLevel.WRITE,
        "tools": ["Read", "Write", "Edit", "Glob", "Grep"],
        "paths": ["docs/*.md", "*.md", "skills/*/SKILL.md"],
        "ttl_minutes": 30,
    },
    "implementation": {
        "level": PermissionLevel.EXECUTE,
        "tools": ["Read", "Write", "Edit", "Glob", "Grep", "Bash"],
        "paths": ["**/*"],
        "blocked_extra": ["hooks/*", "rules/*", ".claude/*"],
        "ttl_minutes": 60,
    },
    "sdd_phase": {
        "level": PermissionLevel.EXECUTE,
        "tools": ["Read", "Write", "Edit", "Glob", "Grep", "Bash", "Agent"],
        "paths": ["**/*"],
        "ttl_minutes": 120,
    },
    "security_audit": {
        "level": PermissionLevel.READ,
        "tools": ["Read", "Glob", "Grep", "Bash"],
        "paths": ["**/*"],
        "ttl_minutes": 30,
    },
}


def get_profile_for_task(task_description: str) -> str:
    """Auto-detect which permission profile to use based on task description.

    Returns one of: readonly, documentation, implementation, sdd_phase, security_audit.
    """
    desc = task_description.lower()

    # Security / audit tasks
    security_words = ["security", "audit", "scan", "vulnerability", "pentest", "review security"]
    if any(w in desc for w in security_words):
        return "security_audit"

    # SDD phase tasks
    sdd_words = ["sdd-apply", "sdd-verify", "sdd-spec", "sdd-design", "sdd-tasks", "sdd-propose"]
    if any(w in desc for w in sdd_words):
        return "sdd_phase"

    # Documentation tasks
    doc_words = [
        "readme", "documentation", "docs", "doc-sync",
        "update docs", "write docs", "fix typo",
        "document", "changelog",
    ]
    if any(w in desc for w in doc_words):
        return "documentation"

    # Read-only / research tasks
    read_words = ["research", "analyze", "explore", "investigate", "read", "search", "find"]
    if any(w in desc for w in read_words):
        return "readonly"

    # Default: implementation
    return "implementation"


def grant_from_profile(
    manager: AgentPermissionManager,
    agent_id: str,
    task: str,
    profile_name: Optional[str] = None,
    granted_by: str = "orchestrator",
) -> PermissionGrant:
    """Grant permissions using a named profile.

    If profile_name is None, auto-detects from task description.
    """
    if profile_name is None:
        profile_name = get_profile_for_task(task)

    profile = PERMISSION_PROFILES.get(profile_name, PERMISSION_PROFILES["readonly"])

    return manager.grant(
        agent_id=agent_id,
        task=task,
        paths=profile["paths"],
        tools=profile["tools"],
        level=profile["level"],
        ttl_minutes=profile.get("ttl_minutes", 30),
        granted_by=granted_by,
        blocked_extra=profile.get("blocked_extra"),
    )
