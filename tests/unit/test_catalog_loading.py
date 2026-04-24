"""Unit tests for the 2-tier skill catalog (compact + full).

Behavioral tests: they execute scripts/generate_compact_catalog.py and assert on
its output. They verify consistency between the committed skills/CATALOG-COMPACT.md
and the SKILL.md files on disk.
"""
from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
GENERATOR = PROJECT_ROOT / "scripts" / "generate_compact_catalog.py"
COMPACT_CATALOG = PROJECT_ROOT / "skills" / "CATALOG-COMPACT.md"
FULL_CATALOG = PROJECT_ROOT / "skills" / "CATALOG.md"


def _load_generator_module():
    """Import scripts/generate_compact_catalog.py as a module for direct use."""
    spec = importlib.util.spec_from_file_location("gen_compact_catalog", GENERATOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _parse_compact_entries(text: str) -> dict:
    """Parse CATALOG-COMPACT.md into {name: {audience, description}}.

    Expects sections like:
        ## audience (N)
        | Skill | Description |
        |-------|-------------|
        | name | description |
    """
    entries: dict[str, dict] = {}
    current_audience: str | None = None
    section_re = re.compile(r"^##\s+(\S+)\s+\(")
    row_re = re.compile(r"^\|\s*([A-Za-z0-9][A-Za-z0-9_\-]*)\s*\|\s*(.*?)\s*\|\s*$")
    for line in text.splitlines():
        m = section_re.match(line)
        if m:
            current_audience = m.group(1)
            continue
        if current_audience is None:
            continue
        if line.startswith("| Skill"):
            continue
        if line.startswith("|---"):
            continue
        m = row_re.match(line)
        if m:
            name = m.group(1)
            desc = m.group(2)
            entries[name] = {"audience": current_audience, "description": desc}
    return entries


# ---------------------------------------------------------------------------
# Generator correctness
# ---------------------------------------------------------------------------


class TestGenerator:

    def test_generator_script_runs(self):
        """The generator runs end-to-end and produces a file."""
        result = subprocess.run(
            [sys.executable, str(GENERATOR)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"generator failed: {result.stderr}"
        assert COMPACT_CATALOG.exists()

    def test_generator_is_deterministic(self):
        """Running twice produces identical output."""
        subprocess.run([sys.executable, str(GENERATOR)], check=True, capture_output=True)
        first = COMPACT_CATALOG.read_text()
        subprocess.run([sys.executable, str(GENERATOR)], check=True, capture_output=True)
        second = COMPACT_CATALOG.read_text()
        assert first == second, "generator is not deterministic"

    def test_compact_catalog_has_auto_generated_header(self):
        """Header identifies file as auto-generated."""
        text = COMPACT_CATALOG.read_text()
        assert "AUTO-GENERATED" in text
        assert "generate_compact_catalog.py" in text

    def test_compact_smaller_than_full(self):
        """Compact catalog must be smaller than full catalog."""
        compact_size = len(COMPACT_CATALOG.read_text())
        full_size = len(FULL_CATALOG.read_text())
        assert compact_size < full_size, (
            f"compact ({compact_size}) must be smaller than full ({full_size})"
        )


# ---------------------------------------------------------------------------
# Consistency: every entry in COMPACT has a real SKILL.md
# ---------------------------------------------------------------------------


class TestConsistency:

    def test_no_phantom_entries(self):
        """Every entry in CATALOG-COMPACT.md must have a real SKILL.md on disk."""
        entries = _parse_compact_entries(COMPACT_CATALOG.read_text())
        assert entries, "compact catalog appears to be empty"

        mod = _load_generator_module()
        real_skills = {s["name"] for s in mod.collect_skills(PROJECT_ROOT)}

        phantom = [name for name in entries if name not in real_skills]
        assert not phantom, (
            "Phantom entries in CATALOG-COMPACT.md (no SKILL.md on disk):\n  "
            + "\n  ".join(sorted(phantom))
        )

    def test_every_skill_in_compact(self):
        """Every SKILL.md on disk must appear in CATALOG-COMPACT.md."""
        entries = _parse_compact_entries(COMPACT_CATALOG.read_text())

        mod = _load_generator_module()
        real_names = sorted({s["name"] for s in mod.collect_skills(PROJECT_ROOT)})

        missing = [n for n in real_names if n not in entries]
        assert not missing, (
            "SKILL.md files not in CATALOG-COMPACT.md — regenerate catalog:\n  "
            + "\n  ".join(missing)
        )

    def test_audience_grouping_matches_frontmatter(self):
        """The audience section a skill appears under must match its SKILL.md frontmatter."""
        entries = _parse_compact_entries(COMPACT_CATALOG.read_text())
        mod = _load_generator_module()
        real_skills = mod.collect_skills(PROJECT_ROOT)
        unique = mod.dedupe(real_skills)

        expected = {s["name"]: s["audience"] for s in unique}
        mismatches = []
        for name, entry in entries.items():
            if name not in expected:
                continue
            if entry["audience"] != expected[name]:
                mismatches.append(
                    f"{name}: catalog={entry['audience']} frontmatter={expected[name]}"
                )
        assert not mismatches, (
            "audience grouping diverged from SKILL.md frontmatter:\n  "
            + "\n  ".join(mismatches)
        )

    def test_regeneration_is_idempotent_against_committed_file(self):
        """Regenerating the compact catalog reproduces the committed file exactly.

        If this fails, someone added/renamed a skill but forgot to regenerate the
        compact catalog. Run: python3 scripts/generate_compact_catalog.py
        """
        committed = COMPACT_CATALOG.read_text()
        result = subprocess.run(
            [sys.executable, str(GENERATOR)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        regenerated = COMPACT_CATALOG.read_text()
        assert committed == regenerated, (
            "CATALOG-COMPACT.md is stale — regenerate:\n"
            "  python3 scripts/generate_compact_catalog.py"
        )


# ---------------------------------------------------------------------------
# Loader wiring: session-init and context-optimization.md point to COMPACT
# ---------------------------------------------------------------------------


class TestLoaderWiring:

    def test_session_init_points_to_compact(self):
        """session-init.sh references CATALOG-COMPACT.md, not only CATALOG.md."""
        content = (PROJECT_ROOT / "hooks" / "session-init.sh").read_text()
        assert "CATALOG-COMPACT.md" in content, (
            "hooks/session-init.sh must reference CATALOG-COMPACT.md"
        )

    def test_context_optimization_references_compact(self):
        """rules/context-optimization.md mentions CATALOG-COMPACT.md."""
        content = (PROJECT_ROOT / "rules" / "context-optimization.md").read_text()
        assert "CATALOG-COMPACT.md" in content

    def test_catalog_full_skill_exists(self):
        """The /catalog-full skill exists and references CATALOG.md."""
        skill_path = PROJECT_ROOT / "skills" / "catalog-full" / "SKILL.md"
        assert skill_path.exists(), "skills/catalog-full/SKILL.md must exist"
        content = skill_path.read_text()
        assert "skills/CATALOG.md" in content
        assert "/catalog-full" in content
