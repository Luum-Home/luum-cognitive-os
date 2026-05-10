#!/usr/bin/env python3
# SCOPE: os-only
"""Migrate SKILL.md frontmatter descriptions to start with `Use when`.

This is a deterministic H6 migration helper. It preserves the body and most
frontmatter ordering while replacing the `description` field with a single-line
YAML-safe value that answers the routing trigger first.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"


def normalize_ws(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().strip('"\'')


def extract_description(frontmatter: str) -> str | None:
    lines = frontmatter.splitlines()
    for idx, line in enumerate(lines):
        if not line.startswith("description:"):
            continue
        rest = line.split(":", 1)[1].strip()
        if rest in {">", "|", ">-", "|-"}:
            block: list[str] = []
            for nxt in lines[idx + 1 :]:
                if nxt.startswith(" ") or nxt.startswith("\t") or not nxt.strip():
                    block.append(nxt.strip())
                    continue
                break
            return normalize_ws(" ".join(block))
        return normalize_ws(rest)
    return None


def use_when_description(current: str) -> str:
    text = normalize_ws(current)
    if not text:
        return "Use when this skill is explicitly requested; do not use when a narrower skill directly matches the task."
    lower = text.lower()
    if lower.startswith("use when"):
        return text
    marker = text.find("Use when")
    if marker >= 0:
        trigger = text[marker:].strip()
        purpose = text[:marker].strip(" .—-")
        if purpose and "purpose:" not in trigger.lower():
            return f"{trigger} Purpose: {purpose}."
        return trigger
    return f"Use when you need this Cognitive OS skill: {text}; do not use when a narrower skill directly matches the task."


def replace_description(frontmatter: str, new_description: str) -> str:
    lines = frontmatter.splitlines()
    out: list[str] = []
    idx = 0
    replaced = False
    while idx < len(lines):
        line = lines[idx]
        if line.startswith("description:"):
            out.append(f"description: {json.dumps(new_description, ensure_ascii=False)}")
            replaced = True
            idx += 1
            rest = line.split(":", 1)[1].strip()
            if rest in {">", "|", ">-", "|-"}:
                while idx < len(lines) and (lines[idx].startswith((" ", "\t")) or not lines[idx].strip()):
                    idx += 1
            continue
        out.append(line)
        idx += 1
    if not replaced:
        insert_at = 1 if lines and lines[0].startswith("name:") else 0
        out.insert(insert_at, f"description: {json.dumps(new_description, ensure_ascii=False)}")
    # ``split_frontmatter`` captures the YAML body without the newline before
    # the closing fence, so rewritten frontmatter must always restore it.
    return "\n".join(out) + "\n"


def split_frontmatter(text: str) -> tuple[str, str, str, str] | None:
    match = re.match(r"(?s)^(?P<prefix>(?:<!--.*?-->\s*)?)---\n(?P<frontmatter>.*?)\n---\n(?P<body>.*)$", text)
    if not match:
        return None
    return match.group("prefix"), "---\n", match.group("frontmatter"), "---\n" + match.group("body")


def migrate_file(path: Path, *, check: bool = False) -> bool:
    text = path.read_text(encoding="utf-8")
    parts = split_frontmatter(text)
    if parts is None:
        return False
    prefix, start, frontmatter, suffix = parts
    current = extract_description(frontmatter) or ""
    new_description = use_when_description(current)
    if current == new_description and current.lower().startswith("use when"):
        return False
    new_frontmatter = replace_description(frontmatter, new_description)
    new_text = prefix + start + new_frontmatter + suffix
    if new_text == text:
        return False
    if not check:
        path.write_text(new_text, encoding="utf-8")
    return True


def skill_files() -> Iterable[Path]:
    return sorted(SKILLS.glob("**/SKILL.md"))


def nonconforming() -> list[str]:
    bad: list[str] = []
    for path in skill_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        parts = split_frontmatter(text)
        desc = extract_description(parts[2]) if parts else None
        if not desc or not desc.startswith("Use when"):
            bad.append(path.relative_to(ROOT).as_posix())
    return bad


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Validate convention without writing.")
    parser.add_argument("--write", action="store_true", help="Rewrite non-conforming SKILL.md descriptions.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if not args.check and not args.write:
        parser.error("choose --check or --write")
    changed = [path.relative_to(ROOT).as_posix() for path in skill_files() if migrate_file(path, check=not args.write)] if args.write else []
    bad = nonconforming()
    payload = {"schema_version": "skill-description-use-when-migration.v1", "changed": changed, "changed_count": len(changed), "nonconforming": bad, "nonconforming_count": len(bad), "status": "pass" if not bad else "fail"}
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"skill-description-use-when: {payload['status']} changed={len(changed)} nonconforming={len(bad)}")
        for item in bad[:50]:
            print(item)
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
