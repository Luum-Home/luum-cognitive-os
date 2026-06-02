# SCOPE: os-only
"""KD6 enforcement: portability coverage contract (W6, os-only).

Walks all files with ``SCOPE: both`` or ``<!-- SCOPE: both -->`` markers
that are part of the red-team harness artifact set, and asserts:
  1. A paired portability test exists in tests/red_team/portability/
  2. The portability test has ≥4 test cases
  3. The portability test has ≥1 falsification keyword

Also enforces the template contract:
  - templates/contracts/test_redteam_baseline.template.py has
    ``<!-- SCOPE: both -->`` and is paired with a portability test.

This is Layer 2 of R10 mitigation (design §7.1). Layer 1 is the
pre-commit hook ``hooks/scope-marker-portability-gate.sh``.

Lane: red_team (parallel-safe — read-only file walk, no shared mutation)
Scope: os-only
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = [pytest.mark.contract, pytest.mark.red_team]

ROOT = Path(__file__).resolve().parents[2]
PORTABILITY_DIR = ROOT / "tests" / "red_team" / "portability"

# ── Red-team harness artifact set ─────────────────────────────────────────────
# Files in the red-team harness that carry SCOPE: both.
# These are the files that KD6 mandates have paired portability tests.
# Relative to ROOT.
REDTEAM_BOTH_ARTIFACTS: list[tuple[str, str]] = [
    # (relative_source_path, expected_portability_test_name)
    ("scripts/verify-archived.sh",             "verify-archived.bats"),
    ("scripts/run-redteam-scenario.sh",         "run-redteam-scenario.bats"),
    ("hooks/plan-claim-validator.sh",           "plan-claim-validator.bats"),
    # Template artifact (both)
    ("templates/contracts/test_redteam_baseline.template.py",   "template-test-redteam-baseline.bats"),
]

# Minimum test case count per portability file
MIN_TEST_CASES = 4

# Regex patterns for counting test cases
_BATS_TEST_RE = re.compile(r'^@test\s+"', re.MULTILINE)
_PY_TEST_RE = re.compile(r'^def test_', re.MULTILINE)
_FALSIFICATION_RE = re.compile(r'falsification', re.IGNORECASE)


def _count_test_cases(portability_file: Path) -> int:
    content = portability_file.read_text(encoding="utf-8")
    if portability_file.suffix == ".bats":
        return len(_BATS_TEST_RE.findall(content))
    if portability_file.suffix == ".py":
        return len(_PY_TEST_RE.findall(content))
    # Unknown format — count nothing (will fail min-test-case assertion)
    return 0


def _has_falsification_keyword(portability_file: Path) -> bool:
    content = portability_file.read_text(encoding="utf-8")
    return bool(_FALSIFICATION_RE.search(content))


def _scope_marker_present(source_path: Path) -> bool:
    """Return True if source file carries a SCOPE: both marker."""
    if not source_path.exists():
        return False
    content = source_path.read_text(encoding="utf-8", errors="replace")
    return "SCOPE: both" in content


# ── Parametrized tests ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("rel_source,portability_name", REDTEAM_BOTH_ARTIFACTS)
def test_source_file_has_scope_both_marker(rel_source: str, portability_name: str) -> None:
    """Source file must carry the SCOPE: both marker."""
    source_path = ROOT / rel_source
    assert source_path.exists(), (
        f"SCOPE: both artifact missing: {rel_source}. "
        "Was the artifact created in W3-W5?"
    )
    assert _scope_marker_present(source_path), (
        f"{rel_source} is expected to have 'SCOPE: both' marker but doesn't. "
        "Update REDTEAM_BOTH_ARTIFACTS if scope changed."
    )


@pytest.mark.parametrize("rel_source,portability_name", REDTEAM_BOTH_ARTIFACTS)
def test_paired_portability_test_exists(rel_source: str, portability_name: str) -> None:
    """Every SCOPE: both red-team artifact must have a paired portability test."""
    portability_path = PORTABILITY_DIR / portability_name
    assert portability_path.exists(), (
        f"Missing portability test: tests/red_team/portability/{portability_name}\n"
        f"Required for SCOPE: both artifact: {rel_source}\n"
        f"KD6 gate violation (design §2.3 Layer 2, §R10 Layer 2)."
    )


@pytest.mark.parametrize("rel_source,portability_name", REDTEAM_BOTH_ARTIFACTS)
def test_portability_test_has_minimum_cases(rel_source: str, portability_name: str) -> None:
    """Portability test must have ≥4 test cases (design §2.2, §7.1)."""
    portability_path = PORTABILITY_DIR / portability_name
    if not portability_path.exists():
        pytest.skip(f"Portability file missing (caught by paired-test check): {portability_name}")
    count = _count_test_cases(portability_path)
    assert count >= MIN_TEST_CASES, (
        f"tests/red_team/portability/{portability_name} has only {count} test cases "
        f"(need ≥{MIN_TEST_CASES}). "
        f"Add more test cases per design §2.2 invariants."
    )


@pytest.mark.parametrize("rel_source,portability_name", REDTEAM_BOTH_ARTIFACTS)
def test_portability_test_has_falsification_keyword(rel_source: str, portability_name: str) -> None:
    """Portability test must contain the word 'falsification' (anti-rubber-stamp, design §2.4)."""
    portability_path = PORTABILITY_DIR / portability_name
    if not portability_path.exists():
        pytest.skip(f"Portability file missing (caught by paired-test check): {portability_name}")
    assert _has_falsification_keyword(portability_path), (
        f"tests/red_team/portability/{portability_name} has no 'falsification' keyword.\n"
        f"Every portability test MUST include at least one falsification probe (design §2.4).\n"
        f"This prevents rubber-stamp tests that always pass. Add a @test starting with\n"
        f"'falsification:' or containing the word 'falsification'."
    )


# ── Whole-repo scan (catches drift) ───────────────────────────────────────────

class TestScopeBothRegistryScan:
    """Scan the repo for SCOPE: both markers and ensure no unregistered red-team artifacts."""

    # Directories to scan for SCOPE: both markers in red-team-related files
    _REDTEAM_DIRS = [
        "tests/red_team/scenarios",
        "tests/red_team/portability",
        "scripts",
        "hooks",
        "skills/redteam-harness",
        "templates/contracts",
    ]

    # Registered source names (base names without extension, normalised)
    _REGISTERED_SOURCES = frozenset(
        Path(rel_src).name for rel_src, _ in REDTEAM_BOTH_ARTIFACTS
    )

    def _redteam_both_files(self) -> list[Path]:
        """Find all SCOPE: both files under red-team harness directories."""
        results = []
        for subdir in self._REDTEAM_DIRS:
            d = ROOT / subdir
            if not d.exists():
                continue
            for f in d.iterdir():
                if f.is_file() and not f.name.startswith("."):
                    try:
                        content = f.read_text(encoding="utf-8", errors="replace")
                    except OSError:
                        continue
                    if "SCOPE: both" in content:
                        results.append(f)
        return results

    def test_no_unregistered_redteam_both_artifacts(self) -> None:
        """All red-team SCOPE: both files must be in REDTEAM_BOTH_ARTIFACTS registry."""
        # This catches new files added without updating the registry (W6+ drift)
        unregistered = []
        for f in self._redteam_both_files():
            # Skip portability tests themselves (they're test files, not source artifacts)
            if f.parent.name == "portability":
                continue
            if f.name not in self._REGISTERED_SOURCES:
                # Not every SCOPE: both file in scripts/ needs portability — only
                # red-team-harness-specific ones do. We check only the harness artifact
                # dirs that are tightly coupled to the harness.
                harness_dirs = {"scenarios", "redteam-harness", "contracts"}
                parent = f.parent.name
                if parent in harness_dirs:
                    unregistered.append(f.relative_to(ROOT))
        assert not unregistered, (
            f"Found SCOPE: both files not registered in REDTEAM_BOTH_ARTIFACTS:\n"
            + "\n".join(f"  {p}" for p in unregistered)
            + "\nAdd them to REDTEAM_BOTH_ARTIFACTS and create paired portability tests."
        )
