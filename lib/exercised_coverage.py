"""exercised_coverage — ADR-041 exercised-coverage pipeline library.

Classifies agentic primitives into 4 tiers based on observed evidence:

  TIER 0 (CI tests)      — covered by behavioral/unit tests (grep test files)
  TIER 1 (manual exercise) — invoked in a real session (.cognitive-os/metrics/*.jsonl)
  TIER 2 (declared only)  — in manifests/primitive-contracts.yaml or primitive-lifecycle.yaml
                             but no test coverage and no session invocation
  TIER 3 (aspirational/dead) — no tests, no invocation, no contract declaration

Tier assignment is waterfall: 0 beats 1, 1 beats 2, 2 beats 3.

Public API:
  classify_primitive(name, project_dir) -> int  (0-3)
  compute_tiers(project_dir)            -> dict[str, int]
  scan_primitives(project_dir)          -> list[str]
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _iter_test_files(project_dir: Path):
    """Yield paths to all Python test files in the project."""
    tests_dir = project_dir / "tests"
    if not tests_dir.is_dir():
        return
    for p in tests_dir.rglob("*.py"):
        yield p


def _load_test_tokens(project_dir: Path) -> set[str]:
    """Load behavior/chaos test files once as normalized identifier tokens."""
    tests_dir = project_dir / "tests"
    if not tests_dir.is_dir():
        return set()

    coverage_dirs = [
        tests_dir / "chaos",
        tests_dir / "behavior",
    ]
    tokens: set[str] = set()
    for cdir in coverage_dirs:
        if not cdir.is_dir():
            continue
        for test_file in cdir.rglob("*.py"):
            try:
                text = test_file.read_text(errors="replace")
            except OSError:
                continue
            tokens.update(_coverage_keys(test_file.stem))
            tokens.update(_coverage_keys(text))
    return tokens


def _coverage_keys(text: str) -> set[str]:
    """Return normalized identifier-like keys from text."""
    parts = [part for part in re.split(r"[^a-zA-Z0-9]+", text.lower()) if part]
    keys = {part for part in parts if len(part) >= 5}
    for left, right in zip(parts, parts[1:]):
        joined = left + right
        if len(joined) >= 5:
            keys.add(joined)
    return keys


def _primitive_keys(name: str) -> set[str]:
    stem = Path(name).stem.lower()
    return {stem, stem.replace("-", "_"), stem.replace("_", "-"), stem.replace("-", ""), stem.replace("_", "")}


def _is_covered_by_test_tokens(name: str, tokens: set[str]) -> bool:
    """Return True if *name* appears in preloaded behavior/chaos tokens."""
    stem = Path(name).stem
    if len(stem) < 5:
        return False
    return bool(_primitive_keys(stem) & tokens)


def _is_covered_by_tests(name: str, project_dir: Path) -> bool:
    """Return True if *name* appears referenced in a chaos/behavior test file."""
    return _is_covered_by_test_tokens(name, _load_test_tokens(project_dir))


def _load_invoked_names(project_dir: Path) -> set[str]:
    """Return set of primitive names observed in session metrics JSONL files.

    Scans hook-timing.jsonl, skill-invocations.jsonl, primitive-interventions.jsonl.
    """
    metrics_dir = project_dir / ".cognitive-os" / "metrics"
    invoked: set[str] = set()
    if not metrics_dir.is_dir():
        return invoked

    # hook-timing.jsonl: {"hook": "secret-detector", ...}
    hook_timing = metrics_dir / "hook-timing.jsonl"
    if hook_timing.is_file():
        for line in hook_timing.read_text(errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                hook = row.get("hook", "")
                if hook:
                    invoked.add(hook)
            except json.JSONDecodeError:
                pass

    # skill-invocations.jsonl: {"payload": {"skill_name": "sdd-explore"}, ...}
    skill_invoc = metrics_dir / "skill-invocations.jsonl"
    if skill_invoc.is_file():
        for line in skill_invoc.read_text(errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                skill = (row.get("payload") or {}).get("skill_name", "")
                if skill:
                    invoked.add(skill)
            except json.JSONDecodeError:
                pass

    # primitive-interventions.jsonl: {"primitive_id": "reinvention-check", ...}
    prim_int = metrics_dir / "primitive-interventions.jsonl"
    if prim_int.is_file():
        for line in prim_int.read_text(errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                pid = (row.get("payload") or row).get("primitive_id", "")
                if pid:
                    invoked.add(pid)
                # Also extract from primitive_source path stem
                psrc = (row.get("payload") or row).get("primitive_source", "")
                if psrc:
                    invoked.add(Path(psrc).stem)
            except json.JSONDecodeError:
                pass

    return invoked


def _load_declared_names(project_dir: Path) -> set[str]:
    """Return set of primitive names declared in manifests (contracts + lifecycle)."""
    declared: set[str] = set()
    manifests_dir = project_dir / "manifests"
    if not manifests_dir.is_dir():
        return declared

    id_re = re.compile(r"^\s*-\s+id:\s+(.+)$")
    source_re = re.compile(r"^\s+source:\s+(.+)$")

    for manifest_name in ("primitive-contracts.yaml", "primitive-lifecycle.yaml"):
        mpath = manifests_dir / manifest_name
        if not mpath.is_file():
            continue
        for line in mpath.read_text(errors="replace").splitlines():
            m = id_re.match(line)
            if m:
                raw = m.group(1).strip()
                declared.add(raw)
                declared.add(Path(raw).stem)
                continue
            m = source_re.match(line)
            if m:
                raw = m.group(1).strip()
                declared.add(raw)
                declared.add(Path(raw).stem)

    return declared


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def scan_primitives(project_dir: Optional[Path] = None) -> list[str]:
    """Return sorted list of all agentic primitive identifiers found in the project.

    Collects:
      - hooks/*.sh (non-_lib)
      - scripts/*.sh, scripts/*.py, and extensionless shebanged scripts
        (top-level only, non _archived)
      - packages/*/skills/*/SKILL.md (skill identifiers)
      - IDs from primitive-lifecycle.yaml and primitive-contracts.yaml
    """
    project_dir = Path(project_dir or ".").resolve()
    primitives: set[str] = set()

    # hooks
    hooks_dir = project_dir / "hooks"
    if hooks_dir.is_dir():
        for p in hooks_dir.glob("*.sh"):
            primitives.add(p.stem)
        for p in hooks_dir.glob("*.py"):
            primitives.add(p.stem)

    # scripts (top-level only)
    scripts_dir = project_dir / "scripts"
    if scripts_dir.is_dir():
        for p in scripts_dir.iterdir():
            if not p.is_file() or p.name.startswith("_archived"):
                continue
            if p.suffix in {".sh", ".py"}:
                primitives.add(p.stem)
                continue
            if p.suffix:
                continue
            try:
                first = p.read_text(encoding="utf-8", errors="ignore")[:120]
            except OSError:
                continue
            if first.startswith("#!") and ("python" in first or "bash" in first):
                primitives.add(p.name)

    # packaged skills
    packages_dir = project_dir / "packages"
    if packages_dir.is_dir():
        for skill_md in packages_dir.glob("*/skills/*/SKILL.md"):
            primitives.add(skill_md.parent.name)

    # Named primitives from manifests (only IDs that look like executables, not docs paths)
    manifests_dir = project_dir / "manifests"
    if manifests_dir.is_dir():
        id_re = re.compile(r"^\s*-\s+id:\s+(.+)$")
        # Paths that look like code (hooks/, scripts/, packages/) — not docs or rules
        executable_path_re = re.compile(r"^(hooks|scripts|packages)/")
        for manifest_name in ("primitive-contracts.yaml", "primitive-lifecycle.yaml"):
            mpath = manifests_dir / manifest_name
            if not mpath.is_file():
                continue
            for line in mpath.read_text(errors="replace").splitlines():
                m = id_re.match(line)
                if m:
                    raw = m.group(1).strip()
                    stem = Path(raw).stem
                    # Include: paths that map to code files, or bare identifiers (no extension, no slash)
                    if executable_path_re.match(raw):
                        primitives.add(stem)
                    elif "/" not in raw and "." not in raw:
                        # Bare named primitive like "destructive-git-blocker"
                        primitives.add(raw)

    return sorted(primitives)


def classify_primitive(name: str, project_dir: Optional[Path] = None) -> int:
    """Classify a single primitive by name, returning tier 0-3.

    TIER 0 — covered by CI tests
    TIER 1 — invoked in a real session
    TIER 2 — declared in manifests only
    TIER 3 — aspirational/dead

    Args:
        name: primitive identifier (e.g. "secret-detector", "hooks/secret-detector.sh")
        project_dir: project root; defaults to cwd

    Returns:
        int in range [0, 3]
    """
    project_dir = Path(project_dir or ".").resolve()

    # Normalise: use stem for matching
    stem = Path(name).stem

    # TIER 0: CI tests cover this primitive
    if _is_covered_by_tests(stem, project_dir):
        return 0

    # TIER 1: invoked in a real session (metrics JSONL)
    invoked = _load_invoked_names(project_dir)
    # Match against stem and full name
    if stem in invoked or name in invoked:
        return 1

    # TIER 2: declared in manifests but not exercised
    declared = _load_declared_names(project_dir)
    if stem in declared or name in declared:
        return 2

    # TIER 3: aspirational/dead
    return 3


def compute_tiers(project_dir: Optional[Path] = None) -> dict[str, int]:
    """Classify all discovered primitives and return {name: tier} mapping.

    Uses scan_primitives() to discover and classify_primitive() for each.
    Session-level data (invocations, declarations) is loaded once for efficiency.

    Returns:
        dict mapping primitive identifier to tier (0-3)
    """
    project_dir = Path(project_dir or ".").resolve()

    primitives = scan_primitives(project_dir)

    # Pre-load shared data for efficiency
    test_tokens = _load_test_tokens(project_dir)
    invoked = _load_invoked_names(project_dir)
    declared = _load_declared_names(project_dir)

    result: dict[str, int] = {}
    for name in primitives:
        stem = Path(name).stem
        if _is_covered_by_test_tokens(stem, test_tokens):
            result[name] = 0
        elif stem in invoked or name in invoked:
            result[name] = 1
        elif stem in declared or name in declared:
            result[name] = 2
        else:
            result[name] = 3

    return result


def distribution(tiers: dict[str, int]) -> dict[int, int]:
    """Return {tier: count} distribution from a compute_tiers() result."""
    dist: dict[int, int] = {0: 0, 1: 0, 2: 0, 3: 0}
    for t in tiers.values():
        dist[t] = dist.get(t, 0) + 1
    return dist
