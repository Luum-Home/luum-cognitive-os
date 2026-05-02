#!/usr/bin/env python3
# @manual-trigger: run to idempotently align SKILL.md frontmatter across all skills; safe to re-run anytime
"""
align_skill_frontmatter.py — Idempotent SKILL.md frontmatter alignment.

Adds missing optional fields (version, platforms, prerequisites) to every
skills/*/SKILL.md file with safe defaults per the Hermes spec documented in
.claude/plugins/hermes-agent/tools/skills_tool.py lines 28-46.

Idempotent: existing fields are never overwritten.
"""

import re
import sys
from pathlib import Path

# Defaults per Hermes spec + COS context
DEFAULTS = {
    "version": '"1.0.0"',
    "platforms": '["claude-code"]',
    "prerequisites": "[]",
}

FIELDS_ORDER = ["version", "platforms", "prerequisites"]


def add_missing_fields(content: str) -> tuple[str, list[str]]:
    """
    Parse frontmatter from content, add missing fields, return updated content
    and list of added field names.
    """
    # Match optional HTML comment + frontmatter block
    # Pattern: optional <!-- ... --> then optional whitespace/newlines, then ---...---
    fm_pattern = re.compile(
        r"^((?:<!--.*?-->\s*)?)(-{3}\n)(.*?)(\n-{3})(.*)",
        re.DOTALL,
    )
    m = fm_pattern.match(content)
    if not m:
        # No frontmatter — skip
        return content, []

    prefix = m.group(1)   # HTML comment if any
    open_fence = m.group(2)
    fm_body = m.group(3)
    close_fence = m.group(4)
    rest = m.group(5)

    added = []
    lines = fm_body.split("\n")

    for field in FIELDS_ORDER:
        # Check if field already exists (case-insensitive key match)
        exists = any(
            re.match(rf"^\s*{re.escape(field)}\s*:", line)
            for line in lines
        )
        if not exists:
            lines.append(f"{field}: {DEFAULTS[field]}")
            added.append(field)

    new_fm_body = "\n".join(lines)
    new_content = f"{prefix}{open_fence}{new_fm_body}{close_fence}{rest}"
    return new_content, added


def main() -> int:
    check_only = "--check" in sys.argv[1:]
    skills_dir = Path(__file__).parent.parent / "skills"
    if not skills_dir.exists():
        print(f"ERROR: skills directory not found at {skills_dir}", file=sys.stderr)
        return 1

    skill_files = sorted(skills_dir.glob("*/SKILL.md"))
    total = len(skill_files)
    updated = 0
    skipped = 0
    errors = 0

    for path in skill_files:
        try:
            original = path.read_text(encoding="utf-8")
            new_content, added = add_missing_fields(original)
            if added:
                if check_only:
                    print(f"MISSING {path.relative_to(skills_dir.parent)}: {added}")
                    errors += 1
                    continue
                path.write_text(new_content, encoding="utf-8")
                print(f"UPDATED {path.relative_to(skills_dir.parent)}: added {added}")
                updated += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"ERROR {path}: {e}", file=sys.stderr)
            errors += 1

    mode = "checked" if check_only else "scanned"
    print(f"\nDone. {total} files {mode}: {updated} updated, {skipped} already complete, {errors} errors.")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
