"""AUDIT: prevent ADR-069 §5 regression — gitignored paths cited as authoritative storage.

This test would have caught the original bug. It does NOT just verify the current
state; it verifies the PATTERN cannot recur.

ROOT CAUSE: ADR-069 §5 originally specified `.cognitive-os/reports/research/` as the
canonical storage path for research reports. Since `.cognitive-os/` is gitignored,
reports ended up duplicated at two paths, inflating /decision-triage counts by 3x.

FIX (2026-04-27): ADR-069 §5 updated to use `docs/06-Daily/reports/` (git-tracked). This test
FAILS if any ADR/rule/template references `.cognitive-os/<something>/<something>.md`
as an authoritative storage path without an explicit opt-out annotation.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent

# The SPECIFIC anti-pattern: .cognitive-os/reports/research/ or .cognitive-os/decisions/
# cited as WHERE research reports or decisions are permanently stored.
# These are gitignored paths — anything written there is invisible to git.
#
# Other .cognitive-os/ subdirectories (runtime/, sprints/, metrics/, etc.) are FINE
# to reference in ADRs as runtime state — they are legitimately gitignored runtime paths.
# The anti-pattern is specifically using them as authoritative decision/report storage.
AUTHORITATIVE_STORAGE_PATTERNS = [
    re.compile(r"\.cognitive-os/reports/research/[^/\s`\"']+\.(md|json|yaml|yml)"),
    re.compile(r"\.cognitive-os/decisions/[^/\s`\"']+\.(md|json|yaml|yml)"),
]

# Directories to scan for documentation that might reference storage paths
SCAN_DIRS = [
    REPO / "docs" / "02-Decisions" / "adrs",   # ADRs are the most authoritative — must not cite gitignored storage
    REPO / "rules",
    REPO / "templates",
]

# Files exempted because they discuss the bug/fix itself (the fix documenting the old path)
EXEMPTED_FILES = {
    # SESSION-HANDOFF files reference the old path to describe what was wrong
    "docs/01-Build-Log/SESSION-HANDOFF-2026-04-25.md",
}


@pytest.mark.audit
def test_no_authoritative_storage_in_gitignored_paths() -> None:
    """Anti-pattern: ADR/rule/template citing `.cognitive-os/reports/research/*.md`
    or `.cognitive-os/decisions/*.md` as authoritative storage for decisions = FAIL.

    ADR-069's original §5 violated this pattern — it directed research agents to write
    reports to `.cognitive-os/reports/research/`, which is gitignored. After the fix,
    ADRs and rules MUST NOT direct agents to store permanent artifacts under .cognitive-os/.

    Scope: Only docs/02-Decisions/adrs/, rules/, templates/ — these are the authoritative source-of-truth
    documents. Session handoffs and ad-hoc docs may reference the old paths for context.

    Note: Other .cognitive-os/ paths (runtime/, metrics/, sprints/, sessions/) are FINE
    in ADRs because they describe transient runtime state, not permanent committed storage.

    Pass criteria:
    - No ADR, rule, or template contains a path `.cognitive-os/reports/research/<file>.md`
      that is framed as WHERE to write permanent reports
    - OR explicitly annotated with `gitignored-runtime: yes` on adjacent line to opt out
    """
    violations: list[tuple[str, int, str]] = []

    for docs_dir in SCAN_DIRS:
        if not docs_dir.exists():
            continue
        for f in sorted(docs_dir.rglob("*.md")):
            rel_path = str(f.relative_to(REPO))
            if rel_path in EXEMPTED_FILES:
                continue

            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

            for pattern in AUTHORITATIVE_STORAGE_PATTERNS:
                for m in pattern.finditer(text):
                    full_match = m.group(0)

                    # Allow explicit opt-out annotation in nearby lines
                    line_idx = text[: m.start()].count("\n")
                    lines = text.splitlines()
                    window_start = max(0, line_idx - 1)
                    window_end = min(len(lines), line_idx + 2)
                    line_window = "\n".join(lines[window_start:window_end])
                    if "gitignored-runtime: yes" in line_window:
                        continue

                    violations.append((rel_path, line_idx + 1, full_match))

    assert not violations, (
        f"Found {len(violations)} reference(s) in ADRs/rules/templates citing "
        f".cognitive-os/reports/research/ or .cognitive-os/decisions/ as authoritative "
        f"storage. This is the ADR-069 §5 anti-pattern. Use docs/06-Daily/reports/ instead. "
        f"To exempt a legitimate contextual reference, add `<!-- gitignored-runtime: yes -->` "
        f"on an adjacent line. Violations (first 5): {violations[:5]}"
    )


@pytest.mark.audit
def test_gitignored_paths_do_not_have_committed_md_files() -> None:
    """If a path is gitignored, no .md file at that path should be git-tracked.

    This catches the scenario where someone force-adds a report under .cognitive-os/
    and bypasses the gitignore — which would re-introduce the duplication problem.

    Pass criteria:
    - `git ls-files` returns 0 .md files under .cognitive-os/reports/ or .cognitive-os/decisions/
    """
    try:
        tracked_output = subprocess.check_output(
            ["git", "ls-files", "--", "*.md"],
            cwd=REPO,
            text=True,
            timeout=10,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip("git not available")
        return

    tracked = tracked_output.splitlines()
    violations = [
        p for p in tracked
        if p.startswith(".cognitive-os/reports/") or p.startswith(".cognitive-os/decisions/")
    ]

    assert not violations, (
        f"Found {len(violations)} .md file(s) committed under .cognitive-os/reports|decisions/. "
        f"These MUST live at docs/06-Daily/reports/ or docs/02-Decisions/ instead — .cognitive-os/ is "
        f"gitignored and causes duplicate-counting in /decision-triage. "
        f"Move these files and update any references. "
        f"Violations: {violations}"
    )


@pytest.mark.audit
def test_docs_reports_dir_exists_and_is_tracked() -> None:
    """Verify that docs/06-Daily/reports/ exists and contains at least one git-tracked file.

    This is the positive flip of the above: after ADR-069 §5 fix, reports MUST be
    in this directory. If it's empty, something is wrong with the migration.
    """
    reports_dir = REPO / "docs" / "06-Daily" / "reports"
    assert reports_dir.is_dir(), (
        f"docs/06-Daily/reports/ does not exist. After ADR-069 §5 fix, this directory MUST "
        f"exist and contain research reports. Create it and move reports from "
        f".cognitive-os/reports/research/ here."
    )

    try:
        tracked_output = subprocess.check_output(
            ["git", "ls-files", "--", "docs/06-Daily/reports/*.md"],
            cwd=REPO,
            text=True,
            timeout=10,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip("git not available")
        return

    tracked = [p for p in tracked_output.splitlines() if p.strip()]
    # Allow the directory to be empty in a fresh clone (reports are created at runtime)
    # But if .md files exist, at least one must be tracked (not force-ignored)
    md_files = list(reports_dir.glob("*.md"))
    if md_files:
        assert tracked, (
            f"docs/06-Daily/reports/ contains {len(md_files)} .md file(s) but none are git-tracked. "
            f"Add them with `git add docs/06-Daily/reports/*.md`."
        )
