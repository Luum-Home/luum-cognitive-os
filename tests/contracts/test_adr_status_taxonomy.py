"""Contract tests for ADR status taxonomy and the canonical ambiguous cases."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
ADRS = REPO_ROOT / "docs" / "adrs"

EXPECTED = {
    "ADR-044-context-payload-slimming.md": ("accepted", "partial-blocked"),
    "ADR-132-solo-swarm-vs-multi-maintainer-fork.md": ("exploration", "not-applicable"),
    "ADR-174b-prevention-followup.md": ("accepted", "implemented"),
    "ADR-174c-validator-blocking-promotion.md": ("proposed", "deferred"),
    "ADR-238-tier-1-4-followup-bug-tracking.md": ("resolved", "resolved"),
    "ADR-253-tombstone-squads.md": ("tombstone", "not-applicable"),
}


def _frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path.name} must have YAML frontmatter"
    raw = text.split("\n---\n", 1)[0].removeprefix("---\n")
    data = yaml.safe_load(raw)
    assert isinstance(data, dict), f"{path.name} frontmatter must be a mapping"
    return data


def test_status_taxonomy_artifact_defines_three_separate_dimensions() -> None:
    text = (ADRS / "STATUS-TAXONOMY.md").read_text(encoding="utf-8")

    assert "Decision status" in text
    assert "Implementation status" in text
    assert "Index bucket" in text
    assert "A single ADR file must not use a map or list as `status`" in text
    assert "Every ADR that has YAML frontmatter must include `implementation_status`" in text


def test_ambiguous_adr_statuses_are_normalized_to_scalar_decision_statuses() -> None:
    for filename, (decision_status, implementation_status) in EXPECTED.items():
        fm = _frontmatter(ADRS / filename)
        assert fm["status"] == decision_status
        assert isinstance(fm["status"], str)
        assert fm["implementation_status"] == implementation_status


def test_adr_174c_owns_only_future_blocking_promotion() -> None:
    fm = _frontmatter(ADRS / "ADR-174c-validator-blocking-promotion.md")
    text = (ADRS / "ADR-174c-validator-blocking-promotion.md").read_text(encoding="utf-8")

    assert fm["parent_adr"] == "ADR-174b"
    assert fm["status"] == "proposed"
    assert "Do not promote automatically" in text
    assert "operator explicitly approves promotion" in text


def test_adr_index_is_generated_from_current_taxonomy() -> None:
    expected = subprocess.run(
        ["python3", "scripts/generate_adr_index.py", "--check"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert expected.returncode == 0, expected.stdout + expected.stderr

    index = (ADRS / "INDEX.md").read_text(encoding="utf-8")
    assert "[STATUS-TAXONOMY.md](STATUS-TAXONOMY.md)" in index
    assert "| [044](ADR-044-context-payload-slimming.md) | Context Payload Slimming" in index
    assert "| [132](ADR-132-solo-swarm-vs-multi-maintainer-fork.md)" in index
    assert "| [174c](ADR-174c-validator-blocking-promotion.md)" in index
    assert "| [238](ADR-238-tier-1-4-followup-bug-tracking.md)" in index
    assert "| [253](ADR-253-tombstone-squads.md)" in index
    assert "### Active / Implemented (" in index
    assert "### Active / Partial (" in index
    assert "### Active / Deferred (" in index
    assert "### Active / Unclassified (" not in index


def test_audit_adrs_rejects_nested_status_maps(tmp_path: Path) -> None:
    from scripts.audit_adrs import audit_file

    adr = tmp_path / "ADR-999-mixed.md"
    adr.write_text(
        "---\nadr: 999\ntitle: Mixed\nstatus:\n  part_a: accepted\n  part_b: proposed\nimplementation_status: implemented\ndate: 2026-05-12\n---\n# ADR-999 — Mixed\n",
        encoding="utf-8",
    )

    result = audit_file(adr, {999})
    assert result["level"] == "FAIL"
    assert result["code"] == "INVALID_STATUS"
    assert "scalar string" in result["message"]


def test_audit_adrs_requires_implementation_status_for_frontmatter(tmp_path: Path) -> None:
    from scripts.audit_adrs import audit_file

    adr = tmp_path / "ADR-998-missing-implementation-status.md"
    adr.write_text(
        "---\nadr: 998\ntitle: Missing Impl Status\nstatus: accepted\ndate: 2026-05-12\n---\n# ADR-998 — Missing Impl Status\n",
        encoding="utf-8",
    )

    result = audit_file(adr, {998})
    assert result["level"] == "FAIL"
    assert result["code"] == "INVALID_IMPLEMENTATION_STATUS"
    assert "implementation_status is required" in result["message"]
