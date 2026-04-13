# scope: both
"""
commit_classifier.py — Classify changed files into thematic commit groups.

Used by the /smart-commit skill to propose conventional commits split by concern.
"""

from __future__ import annotations

import os
import re
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# Theme definitions — ordered, first match wins
# ---------------------------------------------------------------------------

_THEME_RULES: List[Tuple[str, str, str]] = [
    # (theme_key, display_name, conventional_prefix)
    ("tests",     "test changes",      "test"),
    ("lib",       "library changes",   "feat"),
    ("hooks",     "hook changes",      "chore"),
    ("skills",    "skill changes",     "feat"),
    ("rules",     "rule changes",      "docs"),
    ("docs",      "documentation",     "docs"),
    ("packages",  "package changes",   "feat"),
    ("templates", "template changes",  "chore"),
    ("config",    "configuration",     "chore"),
    ("misc",      "misc changes",      "chore"),
]

_THEME_DISPLAY: Dict[str, str] = {k: v for k, v, _ in _THEME_RULES}
_THEME_PREFIX:  Dict[str, str] = {k: p for k, _, p in _THEME_RULES}

# Regex patterns for test files
_TEST_FILE_RE = re.compile(r"(^tests/|_test\.py$|^test_.*\.py$|\.spec\.[tj]s$|_spec\.[tj]s$)")

# Config file extensions / names
_CONFIG_EXTS = {".yaml", ".yml", ".json", ".toml", ".ini", ".env"}
_CONFIG_NAMES = {"settings", "cognitive-os", ".cognitivos"}


def _classify_single(path: str) -> str:
    """Return the theme key for a single file path."""
    norm = path.replace("\\", "/")
    basename = os.path.basename(norm)
    name_no_ext, ext = os.path.splitext(basename)

    # Test files (highest priority — a test inside lib/ is still a test)
    # Check both the full path (for tests/ directory) and the basename (for test_*.py / *_test.py)
    basename_re = re.compile(r"(^test_.*\.py$|_test\.py$|\.spec\.[tj]s$|_spec\.[tj]s$)")
    if _TEST_FILE_RE.search(norm) or basename_re.search(basename):
        return "tests"

    # Directory-based rules
    parts = norm.split("/")
    top = parts[0] if parts else ""
    if top in ("lib",):
        return "lib"
    if top in ("hooks",):
        return "hooks"
    if top in ("skills", ".cognitive-os") and len(parts) > 1 and parts[1] == "skills":
        return "skills"
    if norm.startswith(".cognitive-os/skills/"):
        return "skills"
    if top in ("rules", ".cognitive-os") and len(parts) > 1 and parts[1] == "rules":
        return "rules"
    if norm.startswith(".cognitive-os/rules/"):
        return "rules"
    if top in ("docs",):
        return "docs"
    if top in ("packages",):
        return "packages"
    if top in ("templates", ".cognitive-os") and len(parts) > 1 and parts[1] == "templates":
        return "templates"
    if norm.startswith(".cognitive-os/templates/"):
        return "templates"

    # Markdown files not already caught → documentation
    if ext == ".md":
        return "docs"

    # Config files
    if ext.lower() in _CONFIG_EXTS:
        return "config"
    if any(basename.startswith(n) for n in _CONFIG_NAMES):
        return "config"

    return "misc"


def classify_files(file_list: List[str]) -> Dict[str, List[str]]:
    """
    Group files by theme.

    Returns a dict mapping theme key → list of file paths.
    Only themes with at least one file are included.

    Example
    -------
    >>> classify_files(["lib/foo.py", "hooks/bar.sh", "tests/unit/test_foo.py"])
    {'lib': ['lib/foo.py'], 'hooks': ['hooks/bar.sh'], 'tests': ['tests/unit/test_foo.py']}
    """
    result: Dict[str, List[str]] = {}
    for path in file_list:
        theme = _classify_single(path)
        result.setdefault(theme, []).append(path)
    return result


def detect_related_files(file_list: List[str]) -> List[Tuple[str, str]]:
    """
    Find source↔test file pairs that should travel together in one commit.

    Returns a list of (source_file, test_file) tuples.

    Heuristic: strip leading path segments and ``test_`` / ``_test`` affixes,
    compare base names.
    """
    pairs: List[Tuple[str, str]] = []

    sources = [f for f in file_list if not _TEST_FILE_RE.search(f.replace("\\", "/"))]
    tests   = [f for f in file_list if     _TEST_FILE_RE.search(f.replace("\\", "/"))]

    def _stem(path: str) -> str:
        base = os.path.basename(path)
        name, _ = os.path.splitext(base)
        name = re.sub(r"^test_", "", name)
        name = re.sub(r"_test$", "", name)
        return name.lower()

    test_stems = {_stem(t): t for t in tests}

    for src in sources:
        stem = _stem(src)
        if stem in test_stems:
            pairs.append((src, test_stems[stem]))

    return pairs


def propose_commits(classified: Dict[str, List[str]]) -> List[Dict]:
    """
    Generate a list of commit proposals from a classified file dict.

    Each proposal is a dict with keys:
      - ``theme``:   theme key (e.g. "lib")
      - ``message``: full conventional commit message (e.g. "feat: update library changes")
      - ``files``:   list of file paths for this commit
      - ``prefix``:  conventional prefix without colon (e.g. "feat")

    Related source+test pairs are merged into a single commit using the
    source file's theme.
    """
    if not classified:
        return []

    # Build initial proposals per theme
    proposals: List[Dict] = []
    for theme_key, theme_files in classified.items():
        display = _THEME_DISPLAY.get(theme_key, theme_key.replace("_", " "))
        prefix  = _THEME_PREFIX.get(theme_key, "chore")
        proposals.append({
            "theme":   theme_key,
            "prefix":  prefix,
            "message": f"{prefix}: {display}",
            "files":   list(theme_files),
        })

    # Merge test commits into their matching source theme when a related pair
    # exists and the source theme already has a proposal
    all_files = [f for p in proposals for f in p["files"]]
    pairs = detect_related_files(all_files)

    if pairs and len(proposals) > 1:
        # Build a reverse lookup: test_file → source_file
        test_to_source = {t: s for s, t in pairs}

        # Find which theme owns each source
        file_to_theme: Dict[str, str] = {}
        for prop in proposals:
            for f in prop["files"]:
                file_to_theme[f] = prop["theme"]

        # Re-key proposals for easy lookup
        theme_map = {p["theme"]: p for p in proposals}

        for test_file, source_file in test_to_source.items():
            src_theme = file_to_theme.get(source_file)
            if src_theme and src_theme != "tests" and "tests" in theme_map:
                # Move test_file from tests proposal to src_theme proposal
                test_prop = theme_map["tests"]
                if test_file in test_prop["files"]:
                    test_prop["files"].remove(test_file)
                    theme_map[src_theme]["files"].append(test_file)

        # Remove empty test proposal if all tests were moved
        proposals = [p for p in proposals if p["files"]]

    # Sort proposals in a logical commit order: lib → tests → hooks → skills → rules → docs → rest
    order = ["lib", "hooks", "skills", "rules", "tests", "docs", "packages", "templates", "config", "misc"]
    proposals.sort(key=lambda p: order.index(p["theme"]) if p["theme"] in order else 99)

    return proposals
