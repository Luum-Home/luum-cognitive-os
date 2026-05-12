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


def test_audit_adrs_enforces_future_frontmatter_contract_for_new_adrs(tmp_path: Path) -> None:
    from scripts.audit_adrs import audit_file

    adr = tmp_path / "ADR-276-missing-contract.md"
    adr.write_text(
        "---\nadr: 276\ntitle: Missing Contract\nstatus: accepted\nimplementation_status: partial\ndate: 2026-05-12\n---\n# ADR-276\n",
        encoding="utf-8",
    )

    result = audit_file(adr, {276})
    assert result["level"] == "FAIL"
    assert result["code"] == "MISSING_REQUIRED_FRONTMATTER"
    assert "classification_basis" in result["message"]


def test_audit_adrs_requires_not_applicable_prefix_for_new_adrs(tmp_path: Path) -> None:
    from scripts.audit_adrs import audit_file

    adr = tmp_path / "ADR-276-bad-na.md"
    adr.write_text(
        "---\n"
        "adr: 276\n"
        "title: Bad NA\n"
        "status: accepted\n"
        "implementation_status: not-applicable\n"
        "classification_basis: no work here\n"
        "implementation_files: []\n"
        "tier: maintainer\n"
        "tags: []\n"
        "---\n# ADR-276\n",
        encoding="utf-8",
    )

    result = audit_file(adr, {276})
    assert result["level"] == "FAIL"
    assert result["code"] == "INVALID_CLASSIFICATION_BASIS"
    assert "governance-only" in result["message"]


def test_audit_adrs_rejects_new_accepted_empty_files_without_policy_basis(tmp_path: Path) -> None:
    from scripts.audit_adrs import audit_file

    adr = tmp_path / "ADR-276-empty-files.md"
    adr.write_text(
        "---\n"
        "adr: 276\n"
        "title: Empty Files\n"
        "status: accepted\n"
        "implementation_status: partial\n"
        "classification_basis: 'partial: implementation remains pending'\n"
        "implementation_files: []\n"
        "tier: maintainer\n"
        "tags: []\n"
        "---\n# ADR-276\n",
        encoding="utf-8",
    )

    result = audit_file(adr, {276})
    assert result["level"] == "FAIL"
    assert result["code"] == "INVALID_STATUS_TRANSITION"
    assert "empty implementation_files" in result["message"]


def test_audit_adrs_rejects_new_implemented_with_in_scope_future_work(tmp_path: Path) -> None:
    from scripts.audit_adrs import audit_file

    proof = tmp_path / "proof.txt"
    proof.write_text("proof", encoding="utf-8")
    adr = tmp_path / "ADR-276-future-work.md"
    adr.write_text(
        "---\n"
        "adr: 276\n"
        "title: Future Work\n"
        "status: proposed\n"
        "implementation_status: implemented\n"
        "classification_basis: 'implemented with tests'\n"
        f"implementation_files:\n  - {proof}\n"
        "tier: maintainer\n"
        "tags: []\n"
        "---\n# ADR-276\n\nFuture work remains for runtime enforcement.\n",
        encoding="utf-8",
    )

    result = audit_file(adr, {276})
    assert result["level"] == "FAIL"
    assert result["code"] == "INVALID_STATUS_TRANSITION"
    assert "future" in result["message"]



def test_audit_adrs_verifies_declared_implementation_files_for_accepted_implemented(tmp_path: Path) -> None:
    from scripts.audit_adrs import audit_file

    adr = tmp_path / "ADR-188-accepted-implemented-missing-file.md"
    adr.write_text(
        "---\n"
        "adr: 188\n"
        "title: Accepted Implemented Missing File\n"
        "status: accepted\n"
        "implementation_status: implemented\n"
        "implementation_files:\n  - lib/missing.py\n"
        "tier: maintainer\n"
        "tags: []\n"
        "---\n# ADR-188\n",
        encoding="utf-8",
    )

    result = audit_file(adr, {188})
    assert result["level"] == "FAIL"
    assert result["code"] == "STATUS_REALITY_MISMATCH"
    assert result["implementation_status"] == "implemented"
    assert result["missing_files"] == ["lib/missing.py"]


def test_audit_adrs_verifies_declared_implementation_files_for_partial_too(tmp_path: Path) -> None:
    from scripts.audit_adrs import audit_file

    adr = tmp_path / "ADR-241-partial-missing-file.md"
    adr.write_text(
        "---\n"
        "adr: 241\n"
        "title: Partial Missing File\n"
        "status: accepted\n"
        "implementation_status: partial\n"
        "implementation_files:\n  - hooks/missing.sh\n"
        "tier: maintainer\n"
        "tags: []\n"
        "---\n# ADR-241\n",
        encoding="utf-8",
    )

    result = audit_file(adr, {241})
    assert result["level"] == "FAIL"
    assert result["code"] == "STATUS_REALITY_MISMATCH"
    assert result["implementation_status"] == "partial"
    assert result["missing_files"] == ["hooks/missing.sh"]


def test_operational_guide_alone_is_not_implementation_evidence_for_new_adrs(tmp_path: Path) -> None:
    from scripts.audit_adrs import audit_file

    adr = tmp_path / "ADR-276-og-only.md"
    adr.write_text(
        "---\n"
        "adr: 276\n"
        "title: OG Only\n"
        "status: proposed\n"
        "implementation_status: implemented\n"
        "classification_basis: 'Operational Guide rendered from Decision prose'\n"
        "implementation_files: []\n"
        "tier: maintainer\n"
        "tags: []\n"
        "---\n# ADR-276\n\n## Decision\n\nDo the thing.\n\n## Operational Guide\n\nUse the thing.\n",
        encoding="utf-8",
    )

    result = audit_file(adr, {276})
    assert result["level"] == "FAIL"
    assert result["code"] == "INVALID_STATUS_TRANSITION"
    assert "implemented ADRs require" in result["message"]

def test_adr_partial_ledger_is_generated() -> None:
    result = subprocess.run(
        ["python3", "scripts/cos-adr-partial-ledger", "--check"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
