# scope: both
"""smart_access.py — Token-efficient targeted file access helpers."""

from __future__ import annotations

import json
import re


class SmartAccess:
    """Helpers for token-efficient file access. All methods are resilient:
    missing files return empty/None and never raise."""

    @staticmethod
    def get_active_tasks(
        tasks_path: str = ".cognitive-os/tasks/active-tasks.json",
    ) -> list[dict]:
        """Return ONLY in_progress and failed tasks (skip completed)."""
        try:
            with open(tasks_path) as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return []
        tasks = data if isinstance(data, list) else data.get("tasks", [])
        return [t for t in tasks if t.get("status") in ("in_progress", "failed")]

    @staticmethod
    def get_task_by_id(
        task_id: str,
        tasks_path: str = ".cognitive-os/tasks/active-tasks.json",
    ) -> dict | None:
        """Return a single task by ID."""
        try:
            with open(tasks_path) as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return None
        tasks = data if isinstance(data, list) else data.get("tasks", [])
        return next((t for t in tasks if t.get("id") == task_id), None)

    @staticmethod
    def get_plan_status(plan_path: str) -> str:
        """Read ONLY the Status line from a plan file (first 20 lines).
        Returns 'APPROVED', 'COMPLETED', 'IN_PROGRESS', or 'UNKNOWN'."""
        try:
            with open(plan_path) as f:
                for i, line in enumerate(f):
                    if i >= 20:
                        break
                    m = re.search(r"\bstatus[:\s]+(\w+)", line, re.IGNORECASE)
                    if m:
                        val = m.group(1).upper()
                        if val in ("APPROVED", "COMPLETED", "IN_PROGRESS"):
                            return val
        except (FileNotFoundError, OSError):
            pass
        return "UNKNOWN"

    @staticmethod
    def get_skill_frontmatter(skill_path: str) -> dict:
        """Read ONLY the YAML frontmatter from a SKILL.md (stop at closing ---)."""
        result: dict = {}
        try:
            with open(skill_path) as f:
                lines = iter(f)
                if next(lines, "").rstrip() != "---":
                    return result
                for line in lines:
                    line = line.rstrip()
                    if line == "---":
                        break
                    if ":" in line:
                        k, _, v = line.partition(":")
                        result[k.strip()] = v.strip().strip('"').strip("'")
        except (FileNotFoundError, OSError, StopIteration):
            pass
        return result

    @staticmethod
    def get_config_value(key_path: str, config_path: str = "cognitive-os.yaml"):
        """Read a config value by dot-path (e.g. 'project.phase').
        Line-by-line YAML parser; no external library. Returns None if missing."""
        keys = key_path.split(".")
        try:
            with open(config_path) as f:
                lines = f.readlines()
        except (FileNotFoundError, OSError):
            return None

        def _ind(ln: str) -> int:
            return len(ln) - len(ln.lstrip(" \t"))

        scope, min_ind = lines, -1
        for depth, key in enumerate(keys):
            found_i = key_ind = None
            key_val = ""
            for i, ln in enumerate(scope):
                s = ln.strip()
                if not s or s.startswith("#"):
                    continue
                ind = _ind(ln)
                if min_ind >= 0:
                    if ind < min_ind:
                        break
                    if ind != min_ind:
                        continue
                m = re.match(r"[ \t]*" + re.escape(key) + r"\s*:\s*(.*)", ln)
                if m:
                    found_i, key_ind, key_val = i, ind, m.group(1).strip().strip('"').strip("'")
                    break
            if found_i is None:
                return None
            if depth == len(keys) - 1:
                return key_val or None
            # Descend: detect child indent from next non-empty line
            child_ind = key_ind + 2
            for ln in scope[found_i + 1:]:
                s = ln.strip()
                if s and not s.startswith("#"):
                    child_ind = _ind(ln)
                    break
            block = []
            for ln in scope[found_i + 1:]:
                s = ln.strip()
                if not s or s.startswith("#"):
                    block.append(ln)
                elif _ind(ln) >= child_ind:
                    block.append(ln)
                else:
                    break
            scope, min_ind = block, child_ind
        return None

    @staticmethod
    def count_lines(file_path: str) -> int:
        """Count lines without loading file content into context."""
        try:
            with open(file_path, "rb") as f:
                return sum(1 for _ in f)
        except (FileNotFoundError, OSError):
            return 0

    @staticmethod
    def read_section(file_path: str, section_header: str, max_lines: int = 50) -> str:
        """Read a specific markdown section by heading. Returns only that section."""
        m = re.match(r"(#+)\s*(.*)", section_header)
        level, title = (len(m.group(1)), m.group(2).strip()) if m else (2, section_header.strip())
        try:
            with open(file_path) as f:
                lines = f.readlines()
        except (FileNotFoundError, OSError):
            return ""
        stop = re.compile(r"^#{1," + str(level) + r"}\s")
        in_sec, collected = False, []
        for ln in lines:
            if not in_sec:
                hm = re.match(r"(#+)\s+(.*)", ln)
                if hm and len(hm.group(1)) == level and hm.group(2).strip() == title:
                    in_sec = True
                continue
            if stop.match(ln) and ln.strip() != section_header.strip():
                break
            collected.append(ln)
            if len(collected) >= max_lines:
                break
        return "".join(collected).rstrip()

    @staticmethod
    def files_never_fully_read() -> list[str]:
        """Files that should NEVER be fully read — use the helpers above instead.
        - active-tasks.json  → get_active_tasks()
        - cognitive-os.yaml  → get_config_value()
        - CATALOG.md         → get_skill_frontmatter() per skill
        - RULES-COMPACT.md   → loaded automatically, never read manually
        - *.jsonl metrics    → use grep/tail
        """
        return [
            ".cognitive-os/tasks/active-tasks.json",
            "cognitive-os.yaml",
            ".cognitive-os/CATALOG.md",
            ".cognitive-os/rules/RULES-COMPACT.md",
            ".cognitive-os/metrics/*.jsonl",
        ]
