# SCOPE: os-only
"""Portability probes for packages/agent-lifecycle/lib/harness_adapter/agentapi_msgfmt.py.

Bilateral assertion: summarize_fixtures() reports a stable v1 payload describing
the vendored agentapi msgfmt fixtures on any harness that has python3 + the
package on disk. The summary depends only on directory contents, not on
harness-specific runtime state.

Falsification probes:
  - When pointed at an empty/non-existent directory, the summary must reflect
    zero harnesses and zero cases (a stub returning hard-coded counts would
    fail this).
  - The reported harness list must match the actual on-disk subdirectory names
    (not invented harnesses).
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PKG_LIB = REPO_ROOT / "packages" / "agent-lifecycle" / "lib"
if str(PKG_LIB) not in sys.path:
    sys.path.insert(0, str(PKG_LIB))

from harness_adapter.agentapi_msgfmt import (  # noqa: E402
    ROOT as FIXTURES_ROOT,
    summarize_fixtures,
)


def test_summarize_default_fixtures_returns_versioned_payload() -> None:
    """Bilateral: vendored fixtures yield a v1 summary on any harness."""
    summary = summarize_fixtures().to_dict()
    assert summary["schema_version"] == "agentapi-msgfmt-fixtures/v1"
    assert summary["fixture_root"] == str(FIXTURES_ROOT)
    assert isinstance(summary["harnesses"], list)
    assert summary["format_case_count"] >= 0
    assert summary["initialization_case_count"] >= 0


def test_summary_harnesses_match_on_disk_subdirs() -> None:
    """Falsification: harness list must reflect real subdirs, not invention."""
    summary = summarize_fixtures().to_dict()
    on_disk: set[str] = set()
    for sub in ("format", "initialization"):
        d = FIXTURES_ROOT / sub
        if d.exists():
            on_disk |= {p.name for p in d.iterdir() if p.is_dir()}
    assert sorted(summary["harnesses"]) == sorted(on_disk), (
        f"falsification: harnesses {summary['harnesses']} diverge from disk {sorted(on_disk)}"
    )


def test_summary_against_empty_root_reports_zero(tmp_path: Path) -> None:
    """Falsification: empty (but well-formed) root must produce zero counts."""
    # The implementation expects format/ and initialization/ subdirs to exist
    # whenever root.exists(); seed an empty-but-valid layout to exercise the
    # zero-count path without tripping on a missing subdir.
    (tmp_path / "format").mkdir()
    (tmp_path / "initialization").mkdir()
    summary = summarize_fixtures(tmp_path).to_dict()
    assert summary["harnesses"] == []
    assert summary["format_case_count"] == 0
    assert summary["initialization_case_count"] == 0
    assert summary["fixture_root"] == str(tmp_path)
