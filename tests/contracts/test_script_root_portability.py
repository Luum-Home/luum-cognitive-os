from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

REPO = Path(__file__).resolve().parents[2]
FORBIDDEN = "git rev-parse --show-toplevel"

# Pattern: git rev-parse --show-toplevel followed immediately by a fallback (portable).
# e.g. `git rev-parse --show-toplevel 2>/dev/null || ...`
_PORTABLE_PATTERN = re.compile(
    r"git rev-parse --show-toplevel\s+2>/dev/null\s+\|\|"
)

# Scripts that embed git-hook template blocks with portable rev-parse fallback.
# These are known to use `git rev-parse --show-toplevel 2>/dev/null || fallback`
# and are exempt from the hard-dependency check.
_PORTABLE_ALLOWLIST = {
    "scripts/setup-git-hooks.sh",
}


def test_product_scripts_do_not_depend_on_git_checkout_root() -> None:
    offenders: list[str] = []
    for path in sorted((REPO / "scripts").iterdir()):
        if not path.is_file() or path.name.startswith("__"):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if FORBIDDEN not in text:
            continue
        rel = str(path.relative_to(REPO))
        if rel in _PORTABLE_ALLOWLIST and _PORTABLE_PATTERN.search(text):
            # Uses portable fallback pattern — not a hard dependency
            continue
        offenders.append(rel)
    assert offenders == []


def test_cos_root_documents_install_safe_precedence() -> None:
    text = (REPO / "scripts" / "cos-root").read_text(encoding="utf-8")
    assert "COGNITIVE_OS_PROJECT_DIR" in text
    assert "CODEX_PROJECT_DIR" in text
    assert "CLAUDE_PROJECT_DIR" in text
    assert "install_root" in text
