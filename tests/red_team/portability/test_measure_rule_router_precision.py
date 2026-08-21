# SCOPE: os-only
"""Portability: the router-precision harness must not hardcode one machine.

The sibling script scripts/audit_contextual_rule_channel.py shipped with a
hardcoded project slug. On any other checkout the transcript glob matched
nothing, the replay corpus came back EMPTY, and the script reported
"0 rules named in practice" -- indistinguishable from having looked and found
none. A zero from an empty corpus is the false reading this repo hunts.

This test proves the successor derives its paths from __file__ and refuses to
report a zero it cannot justify.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "scripts" / "measure_rule_router_precision.py"


def test_script_exists_and_declares_scope():
    assert SCRIPT.is_file(), f"{SCRIPT} missing"
    head = SCRIPT.read_text(encoding="utf-8").splitlines()[:3]
    assert any(l.startswith("# SCOPE:") for l in head), (
        f"# SCOPE: must appear in the first 3 lines, got {head!r}")


def test_no_hardcoded_home_or_project_slug():
    src = SCRIPT.read_text(encoding="utf-8")
    # The exact failure mode that broke the predecessor.
    assert not re.search(r"-Users-[A-Za-z0-9.-]+-Projects", src), (
        "hardcoded project slug — the glob would be empty on any other checkout")
    assert "/Users/" not in src, "hardcoded absolute home path"
    assert "__file__" in src, "repo root must be derived from __file__"


def test_repo_root_is_derived_not_assumed():
    src = SCRIPT.read_text(encoding="utf-8")
    assert re.search(r"REPO\s*=\s*Path\(__file__\)\.resolve\(\)\.parent", src)


def test_empty_corpus_errors_instead_of_reporting_zero():
    """A corpus that matched nothing must exit 2, never print a confident 0."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--transcripts",
         "/nonexistent-path-for-portability-test/*.jsonl"],
        capture_output=True, text=True, cwd=str(REPO),
        env={**os.environ, "PYTHONPATH": str(REPO)},
    )
    assert proc.returncode == 2, (
        f"empty corpus must exit 2, got {proc.returncode}\n{proc.stdout}\n{proc.stderr}")
    assert "empty replay corpus" in proc.stderr
