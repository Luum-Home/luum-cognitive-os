"""Integrity tests for packages, squads, and agents.

Read-only audit tests. Verifies:
- Every package directory has at least 1 documentation file.
- Every symlink under lib/, hooks/, skills/, rules/ resolves (no broken links).
- Every squad YAML references existing skills (or documents the gap).
- Every agent YAML's model field is in a recognized set.

All tests are marked with @pytest.mark.audit and parameterized per component.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

# Prefer PyYAML when available; fall back to minimal parser for `model:` / `skills:` lines.
try:
    import yaml as _yaml  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - pyyaml is in requirements.txt but guard anyway
    _yaml = None


# ── Paths ──────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGES_DIR = REPO_ROOT / "packages"
SQUADS_DIR = REPO_ROOT / "squads"
AGENTS_DIR = REPO_ROOT / "agents"
LIB_DIR = REPO_ROOT / "lib"
HOOKS_DIR = REPO_ROOT / "hooks"
SKILLS_DIR = REPO_ROOT / "skills"
RULES_DIR = REPO_ROOT / "rules"


# ── Discovery helpers ──────────────────────────────────────────────────────


def _list_package_dirs() -> list[Path]:
    if not PACKAGES_DIR.is_dir():
        return []
    return sorted(p for p in PACKAGES_DIR.iterdir() if p.is_dir())


def _list_squad_yamls() -> list[Path]:
    if not SQUADS_DIR.is_dir():
        return []
    return sorted(SQUADS_DIR.glob("*.yaml"))


def _list_agent_files() -> list[Path]:
    if not AGENTS_DIR.is_dir():
        return []
    return sorted(AGENTS_DIR.glob("*.md"))


def _find_symlinks(roots: list[Path]) -> list[Path]:
    found: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            # Skip caches / venvs that pollute symlink walks.
            dirnames[:] = [
                d
                for d in dirnames
                if d not in {"__pycache__", ".venv", "node_modules", ".pytest_cache"}
            ]
            for name in list(dirnames) + list(filenames):
                p = Path(dirpath) / name
                if p.is_symlink():
                    found.append(p)
    return sorted(set(found))


def _read_frontmatter(md_path: Path) -> dict[str, str]:
    """Extract YAML frontmatter from a markdown file as a flat dict of strings."""
    text = md_path.read_text(encoding="utf-8", errors="replace")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, flags=re.DOTALL)
    if not m:
        return {}
    block = m.group(1)
    if _yaml is not None:
        try:
            parsed = _yaml.safe_load(block) or {}
            if isinstance(parsed, dict):
                return {str(k): v for k, v in parsed.items()}
        except Exception:
            pass
    # Minimal parser for simple `key: value` lines.
    out: dict[str, str] = {}
    for line in block.splitlines():
        m2 = re.match(r"^([A-Za-z_][A-Za-z0-9_\-]*)\s*:\s*(.+?)\s*$", line)
        if m2:
            out[m2.group(1)] = m2.group(2)
    return out


def _load_yaml(path: Path) -> dict:
    if _yaml is None:
        pytest.skip("PyYAML not installed")
    return _yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _all_skill_names() -> set[str]:
    """Collect every skill directory name under skills/ and packages/*/skills/."""
    names: set[str] = set()
    if SKILLS_DIR.is_dir():
        for d in SKILLS_DIR.iterdir():
            if d.is_dir():
                names.add(d.name)
    if PACKAGES_DIR.is_dir():
        for pkg in PACKAGES_DIR.iterdir():
            pkg_skills = pkg / "skills"
            if pkg_skills.is_dir():
                for d in pkg_skills.iterdir():
                    if d.is_dir():
                        names.add(d.name)
    return names


# ── Recognized model aliases ───────────────────────────────────────────────
# Short aliases used in agent frontmatter + full Claude model IDs used in squad YAMLs.
RECOGNIZED_MODELS: set[str] = {
    "opus",
    "sonnet",
    "haiku",
    "claude-opus-4-6",
    "claude-opus-4-7",
    "claude-sonnet-4",
    "claude-sonnet-4-6",
    "claude-haiku-3.5",
    "claude-haiku-4-5",
    "openrouter/free",
}


# ── Tests ──────────────────────────────────────────────────────────────────


@pytest.mark.audit
@pytest.mark.parametrize(
    "pkg_dir",
    _list_package_dirs(),
    ids=lambda p: p.name,
)
def test_every_package_has_readme_or_skill_md(pkg_dir: Path) -> None:
    """Each package directory must have at least one top-level documentation file.

    Accepts README.md, README.rst, SKILL.md, or cos-package.yaml as evidence that
    the package is documented. A directory with none is likely a placeholder / stub.
    """
    candidates = ["README.md", "README.rst", "SKILL.md", "cos-package.yaml"]
    present = [name for name in candidates if (pkg_dir / name).is_file()]
    assert present, (
        f"Package {pkg_dir.name} has no top-level documentation "
        f"(none of {candidates} present)."
    )


@pytest.mark.audit
@pytest.mark.parametrize(
    "symlink",
    _find_symlinks([LIB_DIR, HOOKS_DIR, SKILLS_DIR, RULES_DIR]),
    ids=lambda p: str(p.relative_to(REPO_ROOT)) if p else "none",
)
def test_symlink_targets_exist(symlink: Path) -> None:
    """Every symlink under lib/, hooks/, skills/, rules/ must resolve to an existing file.

    Handles the project-gotchas warning: `lib/` contains many symlinks that point
    into `../packages/*/lib/*.py`. If any symlink is broken, packages and the
    orchestrator will silently fail at import time.
    """
    # Path.exists() follows symlinks → returns False if target is missing.
    assert symlink.exists(), (
        f"Broken symlink: {symlink} -> {os.readlink(symlink)} "
        f"(target does not exist)."
    )


@pytest.mark.audit
@pytest.mark.parametrize(
    "squad_yaml",
    _list_squad_yamls(),
    ids=lambda p: p.name,
)
def test_every_squad_references_existing_skills(squad_yaml: Path) -> None:
    """Every `skills:` entry in a squad YAML must resolve to a known skill directory.

    A squad YAML that references a missing skill is either broken, or documents
    a runtime gap. This test makes the gap visible.

    Note: squads are currently ornamental (no runtime loader). This test still
    enforces cross-reference integrity so that when a loader is added, the
    references are already valid.
    """
    data = _load_yaml(squad_yaml)
    spec = (data or {}).get("spec", {}) or {}
    skills = spec.get("skills") or []
    if not skills:
        pytest.skip(f"{squad_yaml.name} declares no skills")
    known = _all_skill_names()
    missing = [s for s in skills if isinstance(s, str) and s not in known]
    assert not missing, (
        f"{squad_yaml.name} references unknown skills: {missing}. "
        f"Known skill count: {len(known)}. "
        f"Either add the skill or remove the reference."
    )


@pytest.mark.audit
@pytest.mark.parametrize(
    "agent_file",
    _list_agent_files(),
    ids=lambda p: p.name,
)
def test_every_agent_model_is_recognized(agent_file: Path) -> None:
    """Each agent's `model:` field (if present) must be in the recognized alias set.

    Agents may omit `model:` (model is then resolved via the squad YAML that
    references them). But if present, it must match a known alias to avoid
    silent mis-routing.
    """
    fm = _read_frontmatter(agent_file)
    if "model" not in fm:
        pytest.skip(f"{agent_file.name} has no `model` in frontmatter")
    model = str(fm["model"]).strip()
    assert model in RECOGNIZED_MODELS, (
        f"{agent_file.name} declares unknown model {model!r}. "
        f"Recognized: {sorted(RECOGNIZED_MODELS)}"
    )


@pytest.mark.audit
def test_counts_match_expected_shape() -> None:
    """Sanity check: at least 1 package, at least 1 squad, at least 1 agent exist.

    The orchestrator HALTS if zero packages/squads are found. This test ensures
    future refactors never silently empty these directories.
    """
    packages = _list_package_dirs()
    squads = _list_squad_yamls()
    agents = _list_agent_files()
    assert len(packages) >= 1, f"No packages found under {PACKAGES_DIR}"
    assert len(squads) >= 1, f"No squad YAMLs found under {SQUADS_DIR}"
    assert len(agents) >= 1, f"No agent MD files found under {AGENTS_DIR}"
