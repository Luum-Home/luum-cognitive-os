#!/usr/bin/env python3
# SCOPE: os-only
"""Idempotently standardize primitive file structure without reclassifying scope.

Current safe operations:
- SKILL.md: move an existing SCOPE marker after YAML frontmatter, ensure YAML is
  byte-zero, and add minimal triggers when missing.
- Rules: add a Contextual Trigger section when absent for normal rule files
  using existing routing metadata or title-derived fallback.

This tool preserves existing SCOPE values. It does not infer os-only/project/both.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.primitive_parser import detect_primitive_kind

LEADING_HTML_COMMENT_RE = re.compile(r"^\s*<!--.*?-->\s*\n", re.DOTALL)
SCOPE_COMMENT_RE = re.compile(r"<!--\s*SCOPE:\s*([A-Za-z0-9_-]+)\s*-->", re.IGNORECASE)
HEADING_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)


def _yaml_block(text: str) -> tuple[dict[str, Any], int, int] | None:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            raw = "".join(lines[1:index])
            data = yaml.safe_load(raw) or {}
            if not isinstance(data, dict):
                data = {}
            end = sum(len(item) for item in lines[: index + 1])
            return data, 0, end
    return None


def _dump_frontmatter(data: dict[str, Any]) -> str:
    return "---\n" + yaml.safe_dump(data, sort_keys=False, allow_unicode=True).strip() + "\n---\n"


def _skill_trigger_values(path: Path, data: dict[str, Any], body: str) -> list[str]:
    values: list[str] = []
    name = str(data.get("name") or path.parent.name).strip()
    if name:
        values.extend([name, f"/{name}"])
    match = HEADING_RE.search(body)
    if match:
        title = match.group(1).strip()
        if title and title.lower() != name.lower():
            values.append(title)
    summary = data.get("summary_line") or data.get("description")
    if isinstance(summary, str) and summary.strip():
        values.append(summary.strip().split(".")[0][:120])
    deduped: list[str] = []
    for value in values:
        if value and value not in deduped:
            deduped.append(value)
    return deduped[:4]


def standardize_skill(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    original = text
    scope_line = ""
    preserved_comments: list[str] = []
    while True:
        match = LEADING_HTML_COMMENT_RE.match(text)
        if not match:
            break
        comment = match.group(0)
        scope_match = SCOPE_COMMENT_RE.search(comment)
        if scope_match:
            scope_line = f"<!-- SCOPE: {scope_match.group(1).lower()} -->\n"
        else:
            preserved_comments.append(comment.strip() + "\n")
        text = text[match.end():]
    block = _yaml_block(text)
    if block is None:
        # Do not synthesize a full skill frontmatter from prose in this pass; it
        # risks inventing metadata. Existing COS skills normally have YAML after
        # the leading SCOPE marker, so moving that marker is the safe operation.
        return False
    data, _start, end = block
    body = text[end:]
    if not scope_line:
        existing = re.search(r"<!--\s*SCOPE:\s*([A-Za-z0-9_-]+)\s*-->", body, re.IGNORECASE)
        if existing:
            scope_line = f"<!-- SCOPE: {existing.group(1).lower()} -->\n"
            body = body[: existing.start()] + body[existing.end():]
    if "triggers" not in data:
        data["triggers"] = _skill_trigger_values(path, data, body)
    if "version" not in data:
        data["version"] = "0.1.0"
    new_text = _dump_frontmatter(data) + (scope_line or "") + "".join(preserved_comments) + body.lstrip("\n")
    if new_text != original:
        path.write_text(new_text, encoding="utf-8")
        return True
    return False


def _rule_trigger_values(data: dict[str, Any], text: str, path: Path) -> list[str]:
    values: list[str] = []
    for item in data.get("routing_patterns") or []:
        if isinstance(item, dict) and item.get("pattern"):
            values.append(f"Pattern: `{item['pattern']}`")
    for item in data.get("routing_intents") or []:
        if isinstance(item, dict) and item.get("description"):
            values.append(str(item["description"]).strip())
    match = HEADING_RE.search(text)
    if match:
        values.append(f"When work relates to {match.group(1).strip()}.")
    if not values:
        values.append(f"When `{path.name}` is referenced or its governed behavior is relevant.")
    deduped: list[str] = []
    for value in values:
        if value and value not in deduped:
            deduped.append(value)
    return deduped[:5]


def _frontmatter_anywhere_near_top(text: str) -> dict[str, Any]:
    lines = text.splitlines()
    try:
        start = lines.index("---")
    except ValueError:
        return {}
    for end in range(start + 1, min(len(lines), start + 120)):
        if lines[end] == "---":
            try:
                data = yaml.safe_load("\n".join(lines[start + 1 : end])) or {}
                return data if isinstance(data, dict) else {}
            except yaml.YAMLError:
                return {}
    return {}


def standardize_rule(path: Path) -> bool:
    if path.name in {"RULES-COMPACT.md", "ROADMAP.md"}:
        return False
    text = path.read_text(encoding="utf-8")
    if re.search(r"^##\s+Contextual Trigger\s*$", text, re.MULTILINE):
        return False
    data = _frontmatter_anywhere_near_top(text)
    triggers = _rule_trigger_values(data, text, path)
    section = "\n\n## Contextual Trigger\n\n" + "\n".join(f"- {item}" for item in triggers) + "\n"
    path.write_text(text.rstrip() + section, encoding="utf-8")
    return True


def iter_candidate_files(root: Path) -> list[Path]:
    paths: list[Path] = []
    paths.extend(root.glob("skills/**/SKILL.md"))
    paths.extend(root.glob("packages/*/skills/*/SKILL.md"))
    paths.extend(root.glob("rules/*.md"))
    return sorted(paths)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    root = Path(args.project_dir).resolve()
    changed: list[str] = []
    for path in iter_candidate_files(root):
        kind = detect_primitive_kind(path, root)
        before = path.read_text(encoding="utf-8")
        did_change = False
        if kind == "skill":
            did_change = standardize_skill(path)
        elif kind == "rule":
            did_change = standardize_rule(path)
        if did_change:
            changed.append(path.relative_to(root).as_posix())
            if not args.write:
                path.write_text(before, encoding="utf-8")
    print(yaml.safe_dump({"changed_count": len(changed), "changed": changed}, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
