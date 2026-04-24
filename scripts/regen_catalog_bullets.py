#!/usr/bin/env python3
# ONE-SHOT SCRIPT — regen bullet list in skills/CATALOG.md
# Run from repo root: uv run python3 scripts/regen_catalog_bullets.py
#
# Rewrites the auto-generated "- **name** — description" bullet section at
# the end of CATALOG.md (from the first such bullet onward), preserving every
# line above it.  Uses the fixed _fm() from lib/session_hygiene to extract
# descriptions, including from SKILL.md files that start with an HTML comment
# and those that use multi-line YAML block scalars (description: >).

from __future__ import annotations

import sys
from pathlib import Path

# Allow running from repo root without installing the package
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.session_hygiene import _fm  # noqa: E402


REPO_ROOT = Path(__file__).parent.parent
CATALOG = REPO_ROOT / "skills" / "CATALOG.md"
SKILLS_DIR = REPO_ROOT / "skills"

# Bullet pattern: lines that start the auto-generated section
BULLET_PREFIX = "- **"


def build_bullets() -> list[str]:
    entries: list[tuple[str, str]] = []
    for sf in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        try:
            text = sf.read_text()
        except OSError:
            continue
        name = _fm(text, "name") or sf.parent.name
        desc = _fm(text, "description") or "No description"
        # Collapse multi-line descriptions to a single line capped at 200 chars
        desc_single = " ".join(desc.split())
        if len(desc_single) > 200:
            desc_single = desc_single[:197] + "..."
        entries.append((name, desc_single))
    entries.sort(key=lambda x: x[0].lower())
    return [f"- **{n}** — {d}\n" for n, d in entries]


def regen() -> None:
    if not CATALOG.exists():
        print(f"ERROR: {CATALOG} not found", file=sys.stderr)
        sys.exit(1)

    lines = CATALOG.read_text().splitlines(keepends=True)

    # Find where the first bullet line starts — that is where the auto section begins
    first_bullet = next(
        (i for i, line in enumerate(lines) if line.startswith(BULLET_PREFIX)), None
    )

    if first_bullet is None:
        # No existing bullets — append after last non-empty line
        header = lines
    else:
        header = lines[:first_bullet]

    new_bullets = build_bullets()

    content = "".join(header).rstrip("\n") + "\n" + "".join(new_bullets)
    CATALOG.write_text(content)

    no_desc_count = sum(1 for b in new_bullets if "No description" in b)
    print(
        f"Regenerated {len(new_bullets)} bullets in {CATALOG.relative_to(REPO_ROOT)}"
    )
    print(f"Skills with 'No description': {no_desc_count}")


if __name__ == "__main__":
    regen()
