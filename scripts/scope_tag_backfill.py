#!/usr/bin/env python3
# SCOPE: os-only
# @manual-trigger: run with --apply to add SCOPE: headers to files missing them; dry-run by default
"""
scope_tag_backfill.py — Add SCOPE: header to files that lack one.

Usage:
  python3 scripts/scope_tag_backfill.py          # dry-run (default)
  python3 scripts/scope_tag_backfill.py --apply  # write changes

Heuristic:
  - scripts/cos-* or scripts/aspirational-* → os-only
  - hooks/_lib/*                             → both
  - hooks/aspirational-*                     → os-only
  - everything else (lib/, rules/, skills/)  → both
"""
import argparse
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

SEARCH_DIRS = ["hooks", "lib", "scripts", "rules", "skills"]
INCLUDE_EXTS = {"*.sh", "*.py", "*.md"}


def find_untagged_files() -> list[Path]:
    """Use grep -rL to find files missing SCOPE: tag."""
    cmd = ["grep", "-rL", "SCOPE:"]
    for d in SEARCH_DIRS:
        cmd.append(str(REPO_ROOT / d))
    for ext in INCLUDE_EXTS:
        cmd += ["--include", ext]
    result = subprocess.run(cmd, capture_output=True, text=True)
    paths = [Path(p.strip()) for p in result.stdout.splitlines() if p.strip()]
    return paths


def classify(path: Path) -> str:
    """Return 'os-only' or 'both' for a given file path."""
    rel = path.relative_to(REPO_ROOT)
    parts = rel.parts

    # scripts/cos-* or scripts/aspirational-* → os-only
    if parts[0] == "scripts":
        name = parts[-1]
        if name.startswith("cos-") or name.startswith("aspirational-"):
            return "os-only"
        # scope-tag-backfill.py itself is os-only
        if name == "scope_tag_backfill.py":
            return "os-only"

    # hooks/aspirational-*
    if parts[0] == "hooks" and parts[-1].startswith("aspirational-"):
        return "os-only"

    # packages/cognitive_os_core/** → os-only
    if "cognitive_os_core" in parts:
        return "os-only"

    return "both"


def comment_prefix(path: Path) -> str:
    """Return the comment prefix for a given file type."""
    suffix = path.suffix.lower()
    if suffix == ".md":
        return "<!-- SCOPE: {scope} -->"
    # .sh, .py, and anything else
    return "# SCOPE: {scope}"


def insert_scope_tag(path: Path, scope: str, apply: bool) -> tuple[bool, str]:
    """Insert SCOPE tag into a file. Returns (changed, reason)."""
    try:
        content = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, PermissionError) as e:
        return False, f"skip (read error: {e})"

    template = comment_prefix(path)
    tag_line = template.format(scope=scope)

    lines = content.splitlines(keepends=True)
    if not lines:
        return False, "skip (empty file)"

    # Find insertion point: after shebang (#!) if present, else top
    insert_idx = 0
    if lines and lines[0].startswith("#!"):
        insert_idx = 1

    # For markdown files, tag goes at very top (index 0)
    if path.suffix.lower() == ".md":
        insert_idx = 0

    new_lines = lines[:insert_idx] + [tag_line + "\n"] + lines[insert_idx:]
    new_content = "".join(new_lines)

    if apply:
        path.write_text(new_content, encoding="utf-8")
        return True, "tagged"
    else:
        return True, "would tag (dry-run)"


def main():
    parser = argparse.ArgumentParser(description="Backfill SCOPE: tags")
    parser.add_argument("--apply", action="store_true", help="Write changes (default: dry-run)")
    args = parser.parse_args()

    untagged = find_untagged_files()
    print(f"Found {len(untagged)} untagged file(s).\n")

    changed = 0
    skipped = 0
    for path in sorted(untagged):
        scope = classify(path)
        modified, reason = insert_scope_tag(path, scope, args.apply)
        rel = path.relative_to(REPO_ROOT)
        status = "APPLY" if (modified and args.apply) else ("DRY" if modified else "SKIP")
        print(f"  [{status}] {rel}  → SCOPE: {scope}  ({reason})")
        if modified:
            changed += 1
        else:
            skipped += 1

    print(f"\nTotal: {changed} changed, {skipped} skipped.")
    if not args.apply:
        print("Run with --apply to write changes.")


if __name__ == "__main__":
    main()
