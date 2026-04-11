"""memory_first.py — Enforce the memory-first principle.

Check what you already know before searching Engram or reading files.
Pure logic, no LLM calls, session-scoped cache.
"""
from __future__ import annotations
import fnmatch
from lib.smart_access import SmartAccess

_SMART_HINTS: dict[str, str] = {
    ".cognitive-os/tasks/active-tasks.json": "SmartAccess.get_active_tasks()",
    "cognitive-os.yaml": "SmartAccess.get_config_value()",
    ".cognitive-os/CATALOG.md": "SmartAccess.get_skill_frontmatter()",
    ".cognitive-os/rules/RULES-COMPACT.md": "loaded automatically — never read manually",
}


class MemoryFirst:
    """Enforces the memory-first principle: check what you know before searching."""

    def __init__(self) -> None:
        self._cache: dict[str, str] = {}

    def remember(self, key: str, value: str) -> None:
        """Cache something learned during this session."""
        self._cache[key] = value

    def recall(self, key: str) -> str | None:
        """Return the cached value or None."""
        return self._cache.get(key)

    def has(self, key: str) -> bool:
        """Return True if key is cached."""
        return key in self._cache

    def should_search_engram(self, query: str) -> bool:
        """Return False if the query matches a cached key (already known)."""
        return query not in self._cache

    def should_read_file(self, file_path: str, reason: str = "") -> dict:
        """Pre-read checklist. Returns {action, reason, suggestion}."""
        for pattern in SmartAccess.files_never_fully_read():
            if fnmatch.fnmatch(file_path, pattern) or file_path == pattern:
                if file_path.endswith(".jsonl") or "*.jsonl" in pattern:
                    return {
                        "action": "skip",
                        "reason": "JSONL metrics file — full read wastes tokens",
                        "suggestion": "Use grep/tail to extract relevant lines",
                    }
                hint = _SMART_HINTS.get(pattern, "a targeted SmartAccess helper")
                return {
                    "action": "skip",
                    "reason": f"{file_path} is on the never-fully-read list",
                    "suggestion": f"Use {hint} instead",
                }
        if file_path.endswith(".jsonl"):
            return {
                "action": "skip",
                "reason": "JSONL file — full read wastes tokens",
                "suggestion": "Use grep/tail to extract relevant lines",
            }
        return {"action": "read_full", "reason": "File is not restricted", "suggestion": ""}

    def pre_action_check(self, action: str, target: str) -> str | None:
        """Return a warning string if the action is wasteful, else None."""
        if action in ("mem_search", "mem_get_observation"):
            if target in self._cache:
                return f"Already known: {self._cache[target]}"
        if action == "Read":
            rec = self.should_read_file(target)
            if rec["action"] == "skip":
                return f"{rec['reason']} — {rec['suggestion']}"
        if action == "Bash" and "cat " in target and target.endswith(".jsonl"):
            return "Use Read with offset/limit or grep/tail instead of cat on JSONL"
        return None

    def format_cache_summary(self) -> str:
        """Show what's cached: '{N} items: key1, key2, ...'"""
        n = len(self._cache)
        if n == 0:
            return "0 items"
        keys = ", ".join(list(self._cache.keys())[:5])
        suffix = f", +{n - 5} more" if n > 5 else ""
        return f"{n} items: {keys}{suffix}"

    def to_dict(self) -> dict:
        """Serialize for heartbeat."""
        return {"cache": dict(self._cache)}

    @classmethod
    def from_dict(cls, data: dict) -> "MemoryFirst":
        """Restore from heartbeat."""
        instance = cls()
        instance._cache = dict(data.get("cache", {}))
        return instance
