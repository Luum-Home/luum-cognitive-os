"""Tests for lib/reinvention_guard.py — Reinvention Prevention Guard.

Covers upstream searches (Hermes, Pi), adoption registry checks,
competitive-docs search, report formatting, and relevance ordering.

Run with: pytest tests/unit/test_reinvention_guard.py -v
"""

import os
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.xdist_group("optional_deps")

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from lib.reinvention_guard import ReinventionGuard


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_fake_project(base: Path) -> Path:
    """Populate base with a minimal fake project structure."""
    # Fake hermes submodule
    hermes = base / ".claude/plugins/hermes-agent/agent"
    hermes.mkdir(parents=True)
    (hermes / "context_compressor.py").write_text(
        "# Hermes context compressor\n"
        "def compress(trajectory): pass\n"
        "def compaction_summary(): pass\n"
    )

    # Fake pi submodule
    pi_src = (
        base
        / ".claude/plugins/pi-mono/packages/coding-agent/src/core/tools"
    )
    pi_src.mkdir(parents=True)
    (pi_src / "file-mutation-queue.ts").write_text(
        "// file mutex and mutation queue\n"
        "export class FileMutationQueue {\n"
        "  async acquire(path: string) {}\n"
        "}\n"
    )

    # Fake lib/
    lib = base / "lib"
    lib.mkdir(exist_ok=True)
    (lib / "cost_dashboard.py").write_text("# cost dashboard — unrelated\n")

    # Fake adoption registry
    cognitive = base / ".cognitive-os"
    cognitive.mkdir(exist_ok=True)
    (cognitive / "adoption-registry.yaml").write_text(
        "upstream_repos:\n"
        "  hermes-agent:\n"
        "    url: https://github.com/example/hermes\n"
        "    license: MIT\n"
        "    submodule_path: .claude/plugins/hermes-agent\n"
        "    last_sync: '2026-04-01'\n"
        "adoptions:\n"
        "  - id: hermes-context-compressor\n"
        "    source: hermes-agent\n"
        "    source_file: agent/context_compressor.py\n"
        "    our_file: lib/context_compressor.py\n"
        "    adapted: true\n"
        "    adaptation_notes: Adapted for COS pipeline\n"
        "    adopted_date: '2026-04-02'\n"
    )

    # Fake competitive-landscape doc
    docs = base / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "competitive-landscape.md").write_text(
        "# Competitive Landscape\n\n"
        "## OpenClaw\n"
        "OpenClaw provides context compressor and resilience features.\n"
        "Evaluated: 2026-03-10. Decision: adopt patterns, not the library (AGPL).\n\n"
        "## Hermes\n"
        "Rate limiting and tool-loop detection already integrated.\n"
    )

    return base


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def fake_root(tmp_path: Path) -> Path:
    """Resolved tmp_path populated with fake project files."""
    # resolve() ensures consistent paths on macOS (/var -> /private/var)
    resolved = tmp_path.resolve()
    return _make_fake_project(resolved)


@pytest.fixture()
def fake_guard(fake_root: Path) -> ReinventionGuard:
    """ReinventionGuard pointing at the fake project."""
    return ReinventionGuard(str(fake_root))


@pytest.fixture()
def real_guard() -> ReinventionGuard:
    """Guard pointing at the real project root."""
    root = Path(__file__).resolve().parent.parent.parent
    return ReinventionGuard(str(root))


# ---------------------------------------------------------------------------
# Tests — fake project tree
# ---------------------------------------------------------------------------


def test_finds_hermes_compressor(fake_guard: ReinventionGuard) -> None:
    """Searching 'compaction' should surface hermes context_compressor.py."""
    results = fake_guard.check(
        "context compressor with LLM summarization",
        keywords=["compaction", "compress", "summarize"],
    )
    paths = [r.file_path for r in results]
    assert any("context_compressor" in p for p in paths), (
        f"Expected context_compressor in results, got: {paths}"
    )


def test_finds_pi_mutation_queue(fake_guard: ReinventionGuard) -> None:
    """Searching 'file mutex' should surface pi-mono file-mutation-queue.ts."""
    results = fake_guard.check(
        "file locking with mutex queue",
        keywords=["mutex", "mutation", "queue"],
    )
    paths = [r.file_path for r in results]
    assert any("file-mutation-queue" in p for p in paths), (
        f"Expected file-mutation-queue in results, got: {paths}"
    )


def test_finds_nothing_for_unique_feature(fake_guard: ReinventionGuard) -> None:
    """A completely novel feature should return an empty list."""
    results = fake_guard.check(
        "quantum teleportation matrix",
        keywords=["quantum_teleportation", "teleport", "wormhole_matrix"],
    )
    assert results == [], f"Expected no results, got: {results}"


def test_searches_adoption_registry(fake_guard: ReinventionGuard) -> None:
    """The registry check should find the hermes-context-compressor adoption entry."""
    results = fake_guard._check_registry(
        keywords=["compress", "compressor", "hermes"]
    )
    assert len(results) >= 1
    assert any("hermes-context-compressor" in r.file_path for r in results)
    assert all(r.recommendation == "reference" for r in results)


def test_searches_competitive_docs(fake_guard: ReinventionGuard) -> None:
    """competitive-landscape.md mentions 'compressor' — should be found."""
    results = fake_guard._search_docs(keywords=["compressor", "openclaw"])
    assert len(results) >= 1
    assert any("competitive-landscape" in r.file_path for r in results)
    assert all(r.source == "docs" for r in results)


def test_format_report_with_results(fake_guard: ReinventionGuard) -> None:
    """format_report should include source tags and the decision ladder."""
    results = fake_guard.check(
        "context compressor",
        keywords=["compress", "compaction"],
    )
    report = fake_guard.format_report(results)
    assert "REINVENTION CHECK" in report
    assert any(word in report.lower() for word in ("adopt", "adapt", "reference"))
    assert "adoption-registry.yaml" in report


def test_format_report_empty(fake_guard: ReinventionGuard) -> None:
    """format_report with no results should say 'Safe to build'."""
    report = fake_guard.format_report([])
    assert "Safe to build" in report
    assert "REINVENTION CHECK" in report


def test_relevance_ordering(fake_guard: ReinventionGuard) -> None:
    """Files matching more keywords should rank higher (or equal)."""
    results = fake_guard.check(
        "context compressor and compaction",
        keywords=["compress", "compaction", "context"],
    )
    if len(results) >= 2:
        assert results[0].relevance >= results[1].relevance, (
            "Results should be ordered by descending relevance"
        )


# ---------------------------------------------------------------------------
# Tests — real project (submodules may or may not be present)
# ---------------------------------------------------------------------------


def test_real_guard_gracefully_handles_missing_submodules(
    real_guard: ReinventionGuard,
) -> None:
    """Guard should return [] (not crash) when submodule dirs don't exist."""
    real_guard.hermes_path = Path("/nonexistent/hermes")
    real_guard.pi_path = Path("/nonexistent/pi")
    results = real_guard.check("any feature", keywords=["something"])
    assert isinstance(results, list)


def test_real_hermes_compressor_if_present(
    real_guard: ReinventionGuard,
) -> None:
    """If Hermes is fully cloned with context_compressor.py present, it should be discoverable."""
    # Skip when Hermes is absent OR partially-cloned without the specific file
    # we're asserting on. The previous skip-if-not-exists check accepted a stub
    # directory and then failed the assertion when the file wasn't there.
    if not real_guard.hermes_path.exists():
        pytest.skip("Hermes submodule not cloned — skipping integration check")
    expected = real_guard.hermes_path / "agent" / "context_compressor.py"
    if not expected.is_file():
        pytest.skip(
            f"Hermes cloned but {expected.relative_to(real_guard.hermes_path)} "
            f"missing — partial install, skipping integration check"
        )
    results = real_guard.check(
        "context compressor",
        keywords=["compaction", "compress"],
    )
    paths = [r.file_path for r in results]
    assert any("context_compressor" in p for p in paths)


def test_real_pi_mutation_queue_if_present(
    real_guard: ReinventionGuard,
) -> None:
    """If Pi is fully cloned with file-mutation-queue.ts present, it should be discoverable."""
    if not real_guard.pi_path.exists():
        pytest.skip("Pi submodule not cloned — skipping integration check")
    expected = (
        real_guard.pi_path
        / "packages" / "coding-agent" / "src" / "core" / "tools"
        / "file-mutation-queue.ts"
    )
    if not expected.is_file():
        pytest.skip(
            f"Pi cloned but {expected.name} missing — partial install, skipping"
        )
    # "mutation" and "queue" both appear in file-mutation-queue.ts; "FileMutationQueue"
    # is the exported class name, so search for the actual terms in the file
    results = real_guard.check(
        "file mutation queue",
        keywords=["FileMutationQueue", "mutation", "queue"],
    )
    paths = [r.file_path for r in results]
    assert any("file-mutation-queue" in p for p in paths)
