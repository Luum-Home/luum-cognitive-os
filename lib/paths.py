# SCOPE: both
"""Project and runtime path resolvers for the luum-agent-os kernel.

Implements **Pattern A** — the dominant resolution strategy used at 10 sites
across the codebase (as catalogued in the characterisation tests).

Pattern A semantics::

    CLAUDE_PROJECT_DIR  →  COGNITIVE_OS_PROJECT_DIR  →  None (not configured)

``CLAUDE_PROJECT_DIR`` wins when non-empty; ``COGNITIVE_OS_PROJECT_DIR`` is the
fallback; both absent (or empty) yields ``None`` which callers treat as
"no project dir configured".

Canonical spec: ``tests/unit/test_project_dir_resolution.py`` — the Pattern A
section defines the expected behaviour.  ``TestLibPathsProjectRoot`` (added in
Lote-3, R1) mirrors those assertions directly against this module.

**Do NOT** use this helper for:
- Pattern A' (model_router:321 — ``"."`` default, not ``None``/``""``).
- Pattern C  (dispatch_gate_check:22, queue_drainer:316 — CLAUDE only, ``"."``).
- Pattern D  (telemetry._project_root — reversed COGNITIVE_OS-first order).

Those sites intentionally differ from Pattern A and must NOT be migrated.
See ``tests/unit/test_project_dir_resolution.py`` for the rationale.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

__all__ = [
    "project_root",
    "runtime_project_root",
    "runtime_project_root_or_cwd",
    "runtime_session_id",
    "canonical_skills_dir",
    "canonical_rules_dir",
    "claude_skills_projection_dir",
    "claude_rules_projection_dir",
    "skill_lookup_candidates",
    "canonical_first_skill_lookup_candidates",
    "preferred_rules_dirs",
]


def _first_env(*names: str) -> str:
    """Return the first non-empty environment value from ``names``."""
    for name in names:
        value = os.environ.get(name, "")
        if value:
            return value
    return ""


def project_root() -> Optional[Path]:
    """Return the project root as a :class:`pathlib.Path`, or ``None``.

    Precedence (Pattern A, canonical for 10 call-sites):

    1. ``CLAUDE_PROJECT_DIR`` env var, when non-empty.
    2. ``COGNITIVE_OS_PROJECT_DIR`` env var, when non-empty.
    3. ``None`` — both env vars absent or empty.  Callers gate on truthiness
       (``if project_dir:``) so ``None`` correctly signals "not configured"
       without raising.

    Returns
    -------
    pathlib.Path | None
        Resolved project root, or ``None`` when both env vars are absent or
        empty (matches Pattern A's ``or ""`` falsy default at the 10 sites).
    """
    raw = _first_env("CLAUDE_PROJECT_DIR", "COGNITIVE_OS_PROJECT_DIR")
    if not raw:
        return None
    return Path(raw)


def runtime_project_root() -> Optional[Path]:
    """Return the canonical runtime project root for cross-harness execution.

    This resolver is the forward-looking bootstrap/runtime contract used when
    Cognitive OS needs to behave consistently across harnesses such as Codex
    and Claude Code.

    Precedence:

    1. ``COGNITIVE_OS_PROJECT_DIR``
    2. ``CODEX_PROJECT_DIR``
    3. ``CLAUDE_PROJECT_DIR``
    4. ``None``
    """
    raw = _first_env(
        "COGNITIVE_OS_PROJECT_DIR",
        "CODEX_PROJECT_DIR",
        "CLAUDE_PROJECT_DIR",
    )
    if not raw:
        return None
    return Path(raw)


def runtime_project_root_or_cwd() -> Path:
    """Return the canonical runtime project root, defaulting to ``cwd``."""
    return runtime_project_root() or Path.cwd()


def runtime_session_id(default: str = "") -> str:
    """Return the canonical runtime session id across supported harnesses."""
    return _first_env(
        "COGNITIVE_OS_SESSION_ID",
        "CODEX_SESSION_ID",
        "CLAUDE_SESSION_ID",
    ) or default


def _artifact_project_root(project_root: str | Path | None = None) -> Path:
    """Resolve the project root for artifact path helpers.

    Uses the explicit ``project_root`` when provided; otherwise falls back to
    the canonical cross-harness runtime resolver and finally ``cwd``.
    """
    if project_root is not None:
        return Path(project_root)
    return runtime_project_root_or_cwd()


def canonical_skills_dir(project_root: str | Path | None = None) -> Path:
    """Return the canonical Cognitive OS skill directory.

    This is the forward-looking source-of-truth location for portable skills.
    Current harnesses may still require projection into their own driver paths.
    """
    root = _artifact_project_root(project_root)
    return root / ".cognitive-os" / "skills" / "cos"


def canonical_rules_dir(project_root: str | Path | None = None) -> Path:
    """Return the canonical Cognitive OS rules directory."""
    root = _artifact_project_root(project_root)
    return root / ".cognitive-os" / "rules" / "cos"


def claude_skills_projection_dir(project_root: str | Path | None = None) -> Path:
    """Return the Claude projection directory for skill exposure."""
    root = _artifact_project_root(project_root)
    return root / ".claude" / "skills"


def claude_rules_projection_dir(project_root: str | Path | None = None) -> Path:
    """Return the Claude projection directory for rule exposure."""
    root = _artifact_project_root(project_root)
    return root / ".claude" / "rules" / "cos"


def skill_lookup_candidates(skill_name: str, project_root: str | Path | None = None) -> tuple[Path, ...]:
    """Return ordered candidate locations for a skill's ``SKILL.md``.

    The order is intentionally conservative:

    1. repo-local ``skills/{name}/SKILL.md``
    2. package skill exports ``packages/*/skills/{name}/SKILL.md``
    3. Claude driver projection ``.claude/skills/{name}/SKILL.md``
    4. canonical OS skill path ``.cognitive-os/skills/cos/{name}/SKILL.md``

    This preserves current override semantics while introducing a canonical
    fallback for future migrations.
    """
    return _skill_lookup_candidates(skill_name, project_root, prefer_canonical=False)


def canonical_first_skill_lookup_candidates(
    skill_name: str, project_root: str | Path | None = None
) -> tuple[Path, ...]:
    """Return skill lookup candidates with canonical artifacts before drivers.

    Repo-local source skills and package exports still win because they are
    authored source surfaces. The canonical-first switch only changes the
    ordering between installed canonical artifacts and harness projections.
    This lets diagnostics and future runtime paths opt in without breaking
    current Claude projection semantics.
    """
    return _skill_lookup_candidates(skill_name, project_root, prefer_canonical=True)


def _skill_lookup_candidates(
    skill_name: str,
    project_root: str | Path | None = None,
    *,
    prefer_canonical: bool,
) -> tuple[Path, ...]:
    """Build ordered skill lookup candidates."""
    root = _artifact_project_root(project_root)
    candidates: list[Path] = [root / "skills" / skill_name / "SKILL.md"]

    packages_dir = root / "packages"
    if packages_dir.is_dir():
        for pkg in sorted(packages_dir.iterdir()):
            if pkg.is_dir():
                candidates.append(pkg / "skills" / skill_name / "SKILL.md")

    driver_candidate = claude_skills_projection_dir(root) / skill_name / "SKILL.md"
    canonical_candidate = canonical_skills_dir(root) / skill_name / "SKILL.md"
    if prefer_canonical:
        candidates.extend([canonical_candidate, driver_candidate])
    else:
        candidates.extend([driver_candidate, canonical_candidate])
    return tuple(candidates)


def preferred_rules_dirs(project_root: str | Path | None = None) -> tuple[Path, ...]:
    """Return ordered rule directory candidates for context/rule consumers.

    Order:

    1. canonical projected rules in ``.cognitive-os/rules/cos``
    2. Claude namespaced projection in ``.claude/rules/cos``
    3. broader Claude rules directory ``.claude/rules``
    4. repo-local source ``rules/``
    """
    root = _artifact_project_root(project_root)
    return (
        canonical_rules_dir(root),
        claude_rules_projection_dir(root),
        root / ".claude" / "rules",
        root / "rules",
    )
