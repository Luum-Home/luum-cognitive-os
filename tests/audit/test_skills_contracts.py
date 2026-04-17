"""Contract tests for skill audit — Capa 3 functional verification.

Every test is marked with @pytest.mark.audit so it is gated out of the default CI run.
Run explicitly with:

    python3 -m pytest tests/audit/test_skills_contracts.py -m audit -v

Each test is parameterized per skill, so failures name the exact skill that violates
the contract. This module is the authoritative source for the scorecard in
`docs/architecture/functional-audit/scorecard-skills.md`.

Contracts under test:

1. test_every_skill_has_valid_frontmatter
   YAML frontmatter must start at line 1 and define at least `name:`.
   Catches: malformed-frontmatter skills where the block is placed after the H1
   heading (invisible to strict parsers).

2. test_every_skill_reference_exists
   Every internal project-path reference (e.g. `hooks/foo.sh`, `lib/bar.py`) and
   every bare hyphenated filename in backticks (e.g. ``` `auto-refine.sh` ```)
   must resolve on disk. Failure = code-dead skill.

3. test_every_skill_in_catalog
   Every skill directory must appear in `skills/CATALOG.md` OR
   `skills/CATALOG-COMPACT.md`. Failure = doc-drift.

4. test_no_skill_has_todo_markers
   SKILL.md must not contain procedural-placeholder markers
   (`TODO: implement`, `not yet implemented`, `aspirational`, `coming soon`, `WIP`).
   Domain references inside fenced code blocks and quoted strings are ignored.

Scope: read-only. No tests mutate the filesystem or invoke external services.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import pytest


# ── Paths ──────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / "skills"
CATALOG_FILES = (SKILLS_DIR / "CATALOG.md", SKILLS_DIR / "CATALOG-COMPACT.md")


# ── Discovery ──────────────────────────────────────────────────────────────


def _skill_dirs() -> list[Path]:
    """Return all skill directories under skills/ (sorted, excludes catalog .md files)."""
    if not SKILLS_DIR.exists():
        return []
    return sorted(d for d in SKILLS_DIR.iterdir() if d.is_dir())


SKILL_DIRS = _skill_dirs()
SKILL_IDS = [d.name for d in SKILL_DIRS]


# ── Helpers ────────────────────────────────────────────────────────────────


_STUB_PATTERNS = [
    (r"^\s*TODO:\s*(implement|finish|complete|build|write)", "procedural TODO"),
    (
        r"(?i)\bthis\s+(skill|procedure|step|section)\s+is\s+(not\s+yet\s+|not\s+)?implemented\b",
        "self-declared not implemented",
    ),
    (r"(?i)\bnot\s+yet\s+implemented\b", "not yet implemented"),
    (r"(?i)\baspirational\b", "aspirational"),
    (r"(?i)^\s*(FIXME|XXX):\s", "FIXME/XXX marker"),
    (r"(?i)\bplaceholder\s+(procedure|implementation|logic|section)\b", "placeholder"),
    (r"(?i)\bstub\s+(implementation|out\s+this)\b", "stub implementation"),
    (r"(?i)\bcoming\s+soon\b", "coming soon"),
    (r"(?i)^\s*WIP\b", "WIP at line start"),
]

_REFERENCE_RE = re.compile(
    r"(?P<path>(?:scripts|hooks|packages|lib|templates|rules)/[A-Za-z0-9_./\-]+)"
)
_BARE_FILE_RE = re.compile(r"`([a-zA-Z0-9_][a-zA-Z0-9_\-]*\.(?:sh|py))`")

# Generic bare-file names that are NOT project artifacts; skip them.
_BARE_IGNORE = {
    "settings.json",
    "config.yaml",
    "cognitive-os.yaml",
    "test.sh",
    "build.sh",
    "run.sh",
    "setup.sh",
    "install.sh",
    "main.py",
    "main.go",
    "index.js",
}

# Obvious placeholder/example prefixes — skip bare refs with these.
_BARE_PLACEHOLDER_PREFIXES = (
    "some-",
    "my-",
    "example-",
    "foo-",
    "bar-",
    "your-",
    "new-",
)

# Skills whose path references are intentionally output paths (files the skill GENERATES
# in a target project), not project artifacts that must exist in this repo.
_OUTPUT_PATH_SKILLS: frozenset[str] = frozenset(
    {
        "scaffold-project",  # generates .claude/rules/*, .claude/hooks/* in target project
    }
)


def _strip_fenced_blocks(text: str) -> str:
    """Replace fenced code blocks with blank lines (preserve line numbers)."""
    out: list[str] = []
    in_fence = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            out.append("")
            continue
        out.append("" if in_fence else line)
    return "\n".join(out)


def _strip_code_and_strings(text: str) -> str:
    """Strip fenced blocks, inline backticks, and quoted string literals."""
    cleaned = _strip_fenced_blocks(text)
    out: list[str] = []
    for line in cleaned.split("\n"):
        line2 = re.sub(r"`[^`]*`", lambda m: " " * len(m.group(0)), line)
        line2 = re.sub(r"""(['"])[^'"]*\1""", lambda m: " " * len(m.group(0)), line2)
        out.append(line2)
    return "\n".join(out)


def _parse_frontmatter(text: str) -> dict | None:
    """Parse YAML frontmatter. Returns dict of top-level keys, or None if malformed
    or the block does not start at line 1."""
    if not text.startswith("---"):
        return None
    lines = text.split("\n")
    if lines[0].strip() != "---":
        return None
    end = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end = i
            break
    if end is None:
        return None
    fm: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip() or line.strip().startswith("#"):
            continue
        # Only top-level (non-indented) keys
        if line.startswith((" ", "\t")):
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip()
    return fm


def _find_references(text: str) -> list[tuple[str, str, int]]:
    """Return list of (kind, reference, line_number). kind is 'path' or 'bare'."""
    refs: list[tuple[str, str, int]] = []

    # Phase 1: path-rooted references from prose (code/strings stripped)
    cleaned = _strip_code_and_strings(text)
    for lineno, line in enumerate(cleaned.split("\n"), start=1):
        for m in _REFERENCE_RE.finditer(line):
            p = m.group("path").rstrip(".,;:)")
            if len(p) < 5:
                continue
            if "{" in p or "}" in p or "<" in p or ">" in p:
                continue
            refs.append(("path", p, lineno))

    # Phase 2: bare hyphenated script/hook filenames in inline backticks
    cleaned_fences_only = _strip_fenced_blocks(text)
    for lineno, line in enumerate(cleaned_fences_only.split("\n"), start=1):
        for m in _BARE_FILE_RE.finditer(line):
            fname = m.group(1)
            if fname in _BARE_IGNORE:
                continue
            # Must look like a project artifact (contains a hyphen)
            if "-" not in fname:
                continue
            # Skip obvious placeholder/example names
            if any(fname.startswith(p) for p in _BARE_PLACEHOLDER_PREFIXES):
                continue
            refs.append(("bare", fname, lineno))

    return refs


def _ref_resolves(kind: str, ref: str) -> bool:
    """Return True if the reference resolves to a file/dir on disk."""
    if kind == "path":
        p = REPO_ROOT / ref
        if p.exists():
            return True
        # Tolerate missing extension
        for ext in (".py", ".sh", ".md", ".go"):
            if (REPO_ROOT / (ref + ext)).exists():
                return True
        return False
    if kind == "bare":
        for subdir in ("hooks", "scripts", "lib", "packages"):
            if (REPO_ROOT / subdir / ref).exists():
                return True
        return False
    return False


def _find_stub_markers(text: str) -> list[tuple[str, int, str]]:
    """Return list of (label, line_number, line_text) for procedural stub markers."""
    hits: list[tuple[str, int, str]] = []
    cleaned = _strip_code_and_strings(text)
    for lineno, line in enumerate(cleaned.split("\n"), start=1):
        for pat, label in _STUB_PATTERNS:
            if re.search(pat, line):
                hits.append((label, lineno, line.strip()[:120]))
                break
    return hits


def _catalog_names() -> set[str]:
    """Parse CATALOG*.md files and return the set of skill names they list."""
    names: set[str] = set()
    for cat in CATALOG_FILES:
        if not cat.exists():
            continue
        for line in cat.read_text(encoding="utf-8", errors="ignore").split("\n"):
            m = re.match(r"\|\s*([a-z0-9][a-z0-9\-_]*)\s*\|", line)
            if m:
                names.add(m.group(1))
    return names


_CATALOG_NAMES = _catalog_names()


# ── Sanity test (should always pass) ───────────────────────────────────────


@pytest.mark.audit
def test_skills_directory_is_discoverable():
    """Sanity: the skills/ directory exists and has at least one skill."""
    assert SKILLS_DIR.exists(), f"skills/ directory not found at {SKILLS_DIR}"
    assert len(SKILL_DIRS) > 0, "skills/ has no subdirectories"


@pytest.mark.audit
def test_catalog_exists():
    """At least one of CATALOG.md or CATALOG-COMPACT.md must exist."""
    assert any(c.exists() for c in CATALOG_FILES), (
        f"Neither CATALOG.md nor CATALOG-COMPACT.md found in {SKILLS_DIR}"
    )


# ── Contract 1: frontmatter ────────────────────────────────────────────────


@pytest.mark.audit
@pytest.mark.parametrize("skill_dir", SKILL_DIRS, ids=SKILL_IDS)
def test_every_skill_has_valid_frontmatter(skill_dir: Path):
    """SKILL.md must start with YAML frontmatter at line 1 with at least `name:`.

    Failures: skills where the frontmatter block was placed after the H1 heading
    (6 known cases as of 2026-04-16) or where SKILL.md is missing entirely.
    """
    skill_md = skill_dir / "SKILL.md"
    assert skill_md.exists(), f"skills/{skill_dir.name}/SKILL.md does not exist"

    text = skill_md.read_text(encoding="utf-8", errors="ignore")
    fm = _parse_frontmatter(text)
    assert fm is not None, (
        f"skills/{skill_dir.name}/SKILL.md has no YAML frontmatter at line 1 "
        f"(check that the `---` block is BEFORE any H1 heading)"
    )
    assert "name" in fm, (
        f"skills/{skill_dir.name}/SKILL.md frontmatter is missing required `name:` key "
        f"(keys found: {sorted(fm.keys())})"
    )
    # `description` is recommended but not strictly enforced here — doc hygiene finding.


# ── Contract 2: references resolve ─────────────────────────────────────────


@pytest.mark.audit
@pytest.mark.parametrize("skill_dir", SKILL_DIRS, ids=SKILL_IDS)
def test_every_skill_reference_exists(skill_dir: Path):
    """Every internal path/hook/script referenced by SKILL.md must exist on disk.

    Failures: code-dead skills. See scorecard for the 5 known cases, including
    `auto-refine` (references archived `auto-refine.sh`).

    Skills in _OUTPUT_PATH_SKILLS are excluded: they intentionally reference paths that
    do not exist in this repo because the skill GENERATES those paths in a target project.
    """
    if skill_dir.name in _OUTPUT_PATH_SKILLS:
        pytest.skip(
            f"skills/{skill_dir.name}/ is in _OUTPUT_PATH_SKILLS — "
            f"references are output paths generated by the skill, not project artifacts"
        )

    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        pytest.fail(f"skills/{skill_dir.name}/SKILL.md does not exist")

    text = skill_md.read_text(encoding="utf-8", errors="ignore")
    refs = _find_references(text)
    broken: list[str] = []
    seen: set[tuple[str, str]] = set()
    for kind, ref, lineno in refs:
        key = (kind, ref)
        if key in seen:
            continue
        seen.add(key)
        if not _ref_resolves(kind, ref):
            broken.append(f"  line {lineno}: [{kind}] {ref}")

    assert not broken, (
        f"skills/{skill_dir.name}/SKILL.md references {len(broken)} path(s) that "
        f"do not exist on disk:\n" + "\n".join(broken)
    )


# ── Contract 3: discoverability via catalog ────────────────────────────────


@pytest.mark.audit
@pytest.mark.parametrize("skill_dir", SKILL_DIRS, ids=SKILL_IDS)
def test_every_skill_in_catalog(skill_dir: Path):
    """Every skill directory must be listed in CATALOG.md OR CATALOG-COMPACT.md.

    Failures: doc-drift skills (orphaned from discovery catalogs).
    """
    assert skill_dir.name in _CATALOG_NAMES, (
        f"skills/{skill_dir.name}/ is not listed in either "
        f"skills/CATALOG.md or skills/CATALOG-COMPACT.md — "
        f"run the catalog generator or add the skill entry"
    )


# ── Contract 4: no procedural placeholder markers ──────────────────────────


@pytest.mark.audit
@pytest.mark.parametrize("skill_dir", SKILL_DIRS, ids=SKILL_IDS)
def test_no_skill_has_todo_markers(skill_dir: Path):
    """SKILL.md must not contain procedural-placeholder markers.

    Domain references inside fenced code blocks and quoted strings are ignored,
    so mentioning "detect TODO comments" in a code-review skill is fine. A bare
    line-start `TODO: implement` is not.
    """
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        pytest.skip(f"skills/{skill_dir.name}/SKILL.md missing (caught by frontmatter test)")

    text = skill_md.read_text(encoding="utf-8", errors="ignore")
    hits = _find_stub_markers(text)
    assert not hits, (
        f"skills/{skill_dir.name}/SKILL.md contains {len(hits)} stub/placeholder marker(s):\n"
        + "\n".join(f"  line {ln}: [{label}] {ctx}" for label, ln, ctx in hits)
    )
