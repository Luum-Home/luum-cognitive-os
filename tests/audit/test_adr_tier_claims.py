from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts import cos_tier_claim_audit

pytestmark = pytest.mark.audit

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "cos-tier-claim-audit"


def test_current_adr_tier_claims_have_boring_reliability_evidence() -> None:
    proc = subprocess.run(
        [str(SCRIPT), "--json"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_core_adr_without_evidence_fails(tmp_path: Path) -> None:
    adr = tmp_path / "ADR-999-core-without-evidence.md"
    adr.write_text(
        "---\nadr: 999\ntitle: Missing evidence\ntier: core\n---\n\n"
        "# ADR-999\n\n## Decision\nMake it core.\n",
        encoding="utf-8",
    )
    report = cos_tier_claim_audit.build_report(tmp_path, tmp_path)
    assert report["status"] == "fail"
    assert report["findings"][0]["path"] == "ADR-999-core-without-evidence.md"


def test_team_adr_with_boring_reliability_evidence_passes(tmp_path: Path) -> None:
    adr = tmp_path / "ADR-998-team-with-evidence.md"
    adr.write_text(
        "tier: team\n\n# ADR-998\n\n## Evidence\n"
        "- Command: `scripts/cos-boring-reliability --profile team --json`\n"
        "- Output: `docs/reports/boring-reliability-audit-2026-05-03.md`\n",
        encoding="utf-8",
    )
    report = cos_tier_claim_audit.build_report(tmp_path, tmp_path)
    assert report["status"] == "pass"


def test_maintainer_adr_does_not_need_profile_purity_evidence(tmp_path: Path) -> None:
    adr = tmp_path / "ADR-997-maintainer.md"
    adr.write_text("tier: maintainer\n\n# ADR-997\n", encoding="utf-8")
    report = cos_tier_claim_audit.build_report(tmp_path, tmp_path)
    assert report["status"] == "pass"
