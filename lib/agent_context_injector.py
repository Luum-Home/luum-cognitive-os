"""Agent Context Injector — helps orchestrators decide what context to pass to sub-agents."""

from __future__ import annotations

import re
import subprocess
import json
from typing import Any

# Token budget and search permission per task type
_TASK_CONFIG: dict[str, dict[str, Any]] = {
    "implementation": {"budget": 500,  "search": False},
    "research":       {"budget": 200,  "search": True},
    "debugging":      {"budget": 1000, "search": True},
    "review":         {"budget": 300,  "search": False},
    "documentation":  {"budget": 300,  "search": False},
}

_DEFAULT_CONFIG = {"budget": 300, "search": False}

# Regex to find file paths mentioned in task descriptions
_FILE_PATH_RE = re.compile(r"(?:^|\s)([\w./\-]+\.(?:py|go|ts|js|md|yaml|yml|json|sh|toml))")


class AgentContextInjector:
    """Prepares context blocks for sub-agent prompts."""

    def __init__(self, project_root: str = ".") -> None:
        self.project_root = project_root

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def prepare_context(self, task_description: str, task_type: str = "implementation") -> dict:
        """Return a context dict the orchestrator can inject into a sub-agent prompt."""
        cfg = _TASK_CONFIG.get(task_type, _DEFAULT_CONFIG)

        engram_results = self._search_engram(task_description) if task_description else []
        file_hints = self._extract_file_hints(task_description)
        decisions = [r for r in engram_results if r.get("type") in ("decision", "architecture")]

        return {
            "engram_results": engram_results,
            "file_hints": file_hints,
            "decisions": decisions,
            "token_budget": cfg["budget"],
            "search_permission": cfg["search"],
        }

    def format_context_block(self, context: dict) -> str:
        """Format a context dict as a prompt block."""
        lines: list[str] = ["CONTEXT (from orchestrator):"]

        for decision in context.get("decisions", []):
            title = decision.get("title", "")
            summary = decision.get("summary", "")
            lines.append(f"- Decision: {title}" + (f" — {summary}" if summary else ""))

        for hint in context.get("file_hints", []):
            lines.append(f"- File hint: {hint}")

        for obs in context.get("engram_results", []):
            if obs.get("type") in ("decision", "architecture"):
                continue  # already shown above
            title = obs.get("title", "")
            summary = obs.get("summary", "")
            lines.append(f"- Prior work: {title}" + (f" — {summary}" if summary else ""))

        if len(lines) == 1:
            lines.append("(none)")

        search_ok = context.get("search_permission", False)
        reason = "agent may search Engram for additional context" if search_ok else "all needed context is in the prompt"
        lines.append(f"\nSEARCH PERMISSION: {'yes' if search_ok else 'no'} — {reason}")

        return "\n".join(lines)

    def estimate_context_tokens(self, context_block: str) -> int:
        """Rough token estimate: chars / 4."""
        return max(1, len(context_block) // 4)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _search_engram(self, query: str) -> list[dict]:
        """Search Engram via subprocess; return at most 3 summarised results."""
        keywords = " ".join(query.split()[:8])
        cmd = [
            "python3", "-c",
            f"""
from lib.memory import mem_search
results = mem_search(query={keywords!r}, max_results=3)
import json, sys
json.dump(results if isinstance(results, list) else [], sys.stdout)
""",
        ]
        try:
            out = subprocess.check_output(cmd, cwd=self.project_root, timeout=10, stderr=subprocess.DEVNULL)
            raw: list[dict] = json.loads(out)
        except Exception:
            return []

        summarised = []
        for item in raw[:3]:
            content = item.get("content", "")
            summary = content[:400] if len(content) > 400 else content
            summarised.append({
                "title": item.get("title", ""),
                "type": item.get("type", ""),
                "summary": summary,
            })
        return summarised

    def _extract_file_hints(self, task_description: str) -> list[str]:
        """Extract file path mentions from the task description."""
        matches = _FILE_PATH_RE.findall(task_description)
        return list(dict.fromkeys(m.strip() for m in matches))
