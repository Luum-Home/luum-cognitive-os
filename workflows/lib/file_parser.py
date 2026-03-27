"""Parse outputs from Claude Code (markdown, JSON)."""

import json
import os
import re
from typing import List, Optional


def extract_plan_file(
    output: str,
    jsonl_path: Optional[str] = None,
) -> Optional[str]:
    """Extract plan file path from planner output.

    Tries three strategies in order:
    1. Text output lines starting with .cognitive-os/plans/
    2. Text output lines containing .cognitive-os/plans/ embedded
    3. JSONL Write tool calls targeting .cognitive-os/plans/ (fallback)
    """
    # --- Strategy 1 & 2: parse text output ---
    lines = output.strip().split("\n")
    # First pass: line starts with path
    for line in reversed(lines):
        cleaned = line.strip().strip("`")
        if cleaned.startswith(".cognitive-os/plans/"):
            return cleaned
    # Second pass: path embedded in text
    path_pattern = re.compile(r"(.cognitive-os/plans/[a-zA-Z0-9_./-]+\.md)")
    for line in reversed(lines):
        match = path_pattern.search(line)
        if match:
            return match.group(1)

    # --- Strategy 3: scan JSONL for Write tool calls ---
    if jsonl_path:
        result = _extract_plan_from_jsonl(jsonl_path)
        if result:
            return result

    return None


def _extract_plan_from_jsonl(jsonl_path: str) -> Optional[str]:
    """Scan JSONL output for Write tool calls targeting .cognitive-os/plans/."""
    if not os.path.exists(jsonl_path):
        return None

    path_pattern = re.compile(r"(.cognitive-os/plans/[a-zA-Z0-9_./-]+\.md)")
    matches: List[str] = []

    try:
        with open(jsonl_path, "r") as f:
            for line in f:
                try:
                    msg = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue

                if msg.get("type") != "assistant":
                    continue

                content = msg.get("message", {}).get("content", [])
                for block in content:
                    if block.get("type") != "tool_use":
                        continue
                    if block.get("name") not in ("Write", "write"):
                        continue
                    file_path = block.get("input", {}).get("file_path", "")
                    m = path_pattern.search(file_path)
                    if m:
                        matches.append(m.group(1))
    except Exception:
        return None

    return matches[-1] if matches else None


def extract_evaluation_info(evaluation_path: str) -> dict:
    """Extract score and verdict from an evaluation markdown file."""
    default = {"score": None, "verdict": None, "plan_file": None}

    try:
        with open(evaluation_path, "r") as f:
            content = f.read()
    except (OSError, IOError):
        return default

    score_match = re.search(
        r"\*\*Overall Rating:\*\*\s*(\d+)/50", content
    )
    verdict_match = re.search(
        r"\*\*Status:\*\*\s*(APPROVED|NEEDS_REVISION)", content
    )
    plan_match = re.search(
        r"\*\*Plan File:\*\*\s*`([^`]+)`", content
    )

    return {
        "score": int(score_match.group(1)) if score_match else None,
        "verdict": verdict_match.group(1) if verdict_match else None,
        "plan_file": plan_match.group(1) if plan_match else None,
    }
