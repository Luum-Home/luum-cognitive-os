# scope: both
"""DEFER: This module depends on external services not yet configured. Not actively used.

STATUS: Designed and documented but never called from production code.
Wire when complex orchestrator tasks exercise mid-task tool creation.
See: rules/dynamic-tool-creation.md for the design.

Dynamic Tool Creator -- mid-task tool creation for agents.

Agents can create lightweight tools DURING execution when they encounter
capability gaps or repetitive patterns. Tools live in .cognitive-os/dynamic-tools/
and are session-scoped by default. Valuable tools can be promoted to permanent
skills via promote_to_skill().

Inspired by Agent Zero's mid-conversation plugin creation.

Python 3.9+ compatible, stdlib only (no external deps).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import stat
import textwrap
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class DynamicTool:
    """Record of a dynamically created tool."""

    name: str
    description: str
    tool_type: str  # "bash", "python", "skill"
    path: str
    created_at: str
    session_id: str
    invocable: bool
    usage_count: int = 0
    last_used_at: Optional[str] = None
    promoted: bool = False
    promoted_to: Optional[str] = None


def _slugify(name: str) -> str:
    """Convert a name to a filesystem-safe slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower().strip())
    return slug.strip("-")[:64]


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


class DynamicToolCreator:
    """Creates, manages, and promotes dynamic tools during agent execution.

    Dynamic tools are lightweight scripts or skill stubs that agents create
    on-the-fly when they detect a capability gap. They live in
    .cognitive-os/dynamic-tools/ and are cleaned up at session end unless
    promoted to permanent skills.
    """

    DYNAMIC_TOOLS_DIR = ".cognitive-os/dynamic-tools"
    REGISTRY_FILE = "registry.json"

    def __init__(
        self,
        project_root: str = ".",
        session_id: Optional[str] = None,
    ):
        self.project_root = os.path.abspath(project_root)
        self.session_id = session_id or os.environ.get(
            "COS_SESSION_ID", f"session-{int(time.time())}"
        )
        self.tools_dir = os.path.join(self.project_root, self.DYNAMIC_TOOLS_DIR)
        self._registry_path = os.path.join(self.tools_dir, self.REGISTRY_FILE)
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        """Create the dynamic-tools directory if it does not exist."""
        os.makedirs(self.tools_dir, exist_ok=True)

    def _load_registry(self) -> List[Dict[str, Any]]:
        """Load the tool registry from disk."""
        if not os.path.exists(self._registry_path):
            return []
        try:
            with open(self._registry_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

    def _save_registry(self, entries: List[Dict[str, Any]]) -> None:
        """Persist the tool registry to disk."""
        with open(self._registry_path, "w") as f:
            json.dump(entries, f, indent=2)

    def _find_entry(self, name: str, entries: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        slug = _slugify(name)
        for entry in entries:
            if _slugify(entry["name"]) == slug:
                return entry
        return None

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def create_tool(
        self,
        name: str,
        description: str,
        implementation: str,
        tool_type: str = "bash",
    ) -> Dict[str, Any]:
        """Create a tool mid-task that can be used immediately.

        Args:
            name: Human-readable tool name (e.g. "json-validator").
            description: One-line description of what the tool does.
            implementation: The script/code content.
            tool_type: One of "bash", "python", "skill".

        Returns:
            Dict with keys: path, name, type, invocable, created_at.

        Raises:
            ValueError: If tool_type is not supported or name is empty.
        """
        if not name or not name.strip():
            raise ValueError("Tool name cannot be empty")

        valid_types = ("bash", "python", "skill")
        if tool_type not in valid_types:
            raise ValueError(f"tool_type must be one of {valid_types}, got '{tool_type}'")

        slug = _slugify(name)
        if not slug:
            raise ValueError(f"Name '{name}' produces an empty slug")

        now = _timestamp()

        if tool_type == "bash":
            path = self._create_bash_tool(slug, description, implementation)
        elif tool_type == "python":
            path = self._create_python_tool(slug, description, implementation)
        elif tool_type == "skill":
            path = self._create_skill_tool(slug, name, description, implementation)
        else:
            raise ValueError(f"Unsupported tool_type: {tool_type}")

        tool = DynamicTool(
            name=name,
            description=description,
            tool_type=tool_type,
            path=path,
            created_at=now,
            session_id=self.session_id,
            invocable=True,
        )

        # Update registry
        entries = self._load_registry()
        existing = self._find_entry(name, entries)
        if existing:
            entries = [e for e in entries if _slugify(e["name"]) != _slugify(name)]
        entries.append(asdict(tool))
        self._save_registry(entries)

        return {
            "path": path,
            "name": name,
            "type": tool_type,
            "invocable": True,
            "created_at": now,
        }

    def _create_bash_tool(self, slug: str, description: str, implementation: str) -> str:
        """Write a bash script and make it executable."""
        filepath = os.path.join(self.tools_dir, f"{slug}.sh")
        content = f"#!/usr/bin/env bash\n# Dynamic tool: {description}\n# Auto-created by DynamicToolCreator\nset -euo pipefail\n\n{implementation}\n"
        with open(filepath, "w") as f:
            f.write(content)
        os.chmod(filepath, os.stat(filepath).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        return filepath

    def _create_python_tool(self, slug: str, description: str, implementation: str) -> str:
        """Write a Python module."""
        filepath = os.path.join(self.tools_dir, f"{slug}.py")
        content = f'"""{description}\n\nAuto-created by DynamicToolCreator.\n"""\n\n{implementation}\n'
        with open(filepath, "w") as f:
            f.write(content)
        return filepath

    def _create_skill_tool(
        self, slug: str, name: str, description: str, implementation: str
    ) -> str:
        """Write a SKILL.md in a subdirectory."""
        skill_dir = os.path.join(self.tools_dir, slug)
        os.makedirs(skill_dir, exist_ok=True)
        filepath = os.path.join(skill_dir, "SKILL.md")

        content = textwrap.dedent(f"""\
            ---
            name: {slug}
            version: 0.1.0
            auto-generated: true
            dynamic-tool: true
            ---

            # {name}

            > {description}

            ## Trigger

            Created dynamically during session. Invoke manually or via orchestrator.

            ## Steps

            {implementation}
        """)
        with open(filepath, "w") as f:
            f.write(content)
        return filepath

    def list_dynamic_tools(self) -> List[Dict[str, Any]]:
        """List all tools created during this or previous sessions.

        Returns:
            List of tool dicts from the registry.
        """
        return self._load_registry()

    def get_tool(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a single tool by name.

        Returns:
            Tool dict or None if not found.
        """
        entries = self._load_registry()
        return self._find_entry(name, entries)

    def record_usage(self, name: str) -> None:
        """Record that a dynamic tool was used (increments counter)."""
        entries = self._load_registry()
        entry = self._find_entry(name, entries)
        if entry:
            entry["usage_count"] = entry.get("usage_count", 0) + 1
            entry["last_used_at"] = _timestamp()
            self._save_registry(entries)

    def promote_to_skill(self, tool_name: str) -> str:
        """Promote a dynamic tool to a permanent skill.

        Copies the tool to skills/auto-generated/{slug}/ and creates a
        SKILL.md if one does not already exist (bash/python tools get
        wrapped in a skill template).

        Args:
            tool_name: Name of the dynamic tool to promote.

        Returns:
            Path to the promoted skill directory.

        Raises:
            ValueError: If the tool is not found.
        """
        entries = self._load_registry()
        entry = self._find_entry(tool_name, entries)
        if not entry:
            raise ValueError(f"Dynamic tool '{tool_name}' not found")

        slug = _slugify(tool_name)
        skill_dir = os.path.join(
            self.project_root, "skills", "auto-generated", slug
        )
        os.makedirs(skill_dir, exist_ok=True)

        source_path = entry["path"]
        tool_type = entry["tool_type"]

        if tool_type == "skill":
            # Copy the SKILL.md directly
            src_skill = source_path
            if os.path.isfile(src_skill):
                dst = os.path.join(skill_dir, "SKILL.md")
                shutil.copy2(src_skill, dst)
        else:
            # Copy the script
            filename = os.path.basename(source_path)
            shutil.copy2(source_path, os.path.join(skill_dir, filename))

            # Generate a wrapping SKILL.md
            skill_md = os.path.join(skill_dir, "SKILL.md")
            if not os.path.exists(skill_md):
                ext = "bash" if tool_type == "bash" else "python"
                content = textwrap.dedent(f"""\
                    ---
                    name: {slug}
                    version: 0.1.0
                    auto-generated: true
                    promoted-from: dynamic-tool
                    ---

                    # {entry['name']}

                    > {entry['description']}

                    ## Trigger

                    Promoted from dynamic tool. Originally created mid-session.

                    ## Usage

                    ```{ext}
                    # Run the tool script:
                    # {filename}
                    ```

                    ## Steps

                    1. Execute `{filename}` with appropriate arguments.
                    2. Verify the output matches expectations.
                """)
                with open(skill_md, "w") as f:
                    f.write(content)

        # Mark as promoted in registry
        entry["promoted"] = True
        entry["promoted_to"] = skill_dir
        self._save_registry(entries)

        return skill_dir

    def cleanup_session_tools(self, keep_promoted: bool = True) -> int:
        """Remove dynamic tools created during this session.

        Args:
            keep_promoted: If True, skip tools that have been promoted.

        Returns:
            Number of tools removed.
        """
        entries = self._load_registry()
        removed = 0
        remaining = []

        for entry in entries:
            if keep_promoted and entry.get("promoted", False):
                remaining.append(entry)
                continue

            path = entry["path"]
            tool_type = entry.get("tool_type", "")

            if tool_type == "skill":
                # Skill tools live in a subdirectory -- remove the whole directory
                skill_dir = os.path.dirname(path)
                if skill_dir != self.tools_dir and os.path.exists(skill_dir):
                    shutil.rmtree(skill_dir, ignore_errors=True)
                    removed += 1
            elif os.path.isfile(path):
                os.remove(path)
                removed += 1

        self._save_registry(remaining)

        # Clean up empty dynamic-tools dir (but keep registry if tools remain)
        if not remaining:
            # Remove registry too
            if os.path.exists(self._registry_path):
                os.remove(self._registry_path)

        return removed

    def should_create_tool(self, pattern_count: int, threshold: int = 3) -> bool:
        """Heuristic: should the agent create a dynamic tool?

        Returns True if a repetitive pattern has been detected enough times.
        """
        return pattern_count >= threshold

    def format_tool_list(self) -> str:
        """Human-readable list of dynamic tools for agent context."""
        tools = self.list_dynamic_tools()
        if not tools:
            return "No dynamic tools in this session."

        lines = ["DYNAMIC TOOLS AVAILABLE:"]
        for t in tools:
            status = " [promoted]" if t.get("promoted") else ""
            uses = t.get("usage_count", 0)
            lines.append(f"  - {t['name']} ({t['tool_type']}): {t['description']} [used {uses}x]{status}")
        return "\n".join(lines)
