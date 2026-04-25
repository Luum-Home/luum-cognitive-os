"""Audit: bash scripts use kebab-case filenames per rules/bash-naming.md."""
import re
import pytest
from pathlib import Path

REPO = Path(__file__).parent.parent.parent

# Private subdirs are exempt — convention for helper libs not invoked directly.
ALLOWLIST_DIRS = {"_lib", "_archived"}

# Valid kebab-case filename: lowercase letters/digits, optional hyphens in the
# middle, ends with .sh.  Single-word names (e.g. "setup.sh") are also valid.
KEBAB_RE = re.compile(r"^[a-z0-9][a-z0-9-]*\.sh$")


def _scan(root: Path) -> list[Path]:
    """Return paths of .sh files under *root* that violate the kebab-case rule."""
    if not root.exists():
        return []
    bad: list[Path] = []
    for p in root.rglob("*.sh"):
        # Skip files inside any allowlisted private subdirectory.
        if any(part in ALLOWLIST_DIRS for part in p.parts):
            continue
        if not KEBAB_RE.match(p.name):
            bad.append(p.relative_to(REPO))
    return bad


@pytest.mark.audit
def test_scripts_are_kebab_case() -> None:
    """scripts/*.sh must use kebab-case filenames (rules/bash-naming.md)."""
    bad = _scan(REPO / "scripts")
    assert not bad, (
        "Bash scripts MUST use kebab-case filenames "
        "(see rules/bash-naming.md). "
        f"Offending files: {[str(p) for p in bad]}"
    )


@pytest.mark.audit
def test_hooks_are_kebab_case() -> None:
    """hooks/*.sh must use kebab-case filenames (rules/bash-naming.md)."""
    bad = _scan(REPO / "hooks")
    assert not bad, (
        "Bash hooks MUST use kebab-case filenames "
        "(see rules/bash-naming.md). "
        f"Offending files: {[str(p) for p in bad]}"
    )


@pytest.mark.audit
def test_packages_bash_are_kebab_case() -> None:
    """packages/*/hooks/*.sh and packages/*/scripts/*.sh must use kebab-case."""
    bad: list[Path] = []
    packages_root = REPO / "packages"
    if not packages_root.exists():
        return
    for p in packages_root.rglob("*.sh"):
        # Only enforce files explicitly inside hooks/ or scripts/ subdirs.
        parts = p.parts
        if not any(seg in ("hooks", "scripts") for seg in parts):
            continue
        if any(part in ALLOWLIST_DIRS for part in parts):
            continue
        if not KEBAB_RE.match(p.name):
            bad.append(p.relative_to(REPO))
    assert not bad, (
        "Package bash files MUST use kebab-case filenames "
        "(see rules/bash-naming.md). "
        f"Offending files: {[str(p) for p in bad]}"
    )
