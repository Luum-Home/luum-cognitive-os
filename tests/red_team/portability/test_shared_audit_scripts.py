"""Family-specific portability proof for reviewed shared audit scripts."""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SHARED_AUDIT_SCRIPTS = [
    "scripts/credibility-audit.sh",
    "scripts/doctor.sh",
    "scripts/license-audit-syft-grype.sh",
    "scripts/license-audit-trivy.sh",
]


def test_shared_audit_scripts_are_project_relative_and_source_checkout_free() -> None:
    for rel in SHARED_AUDIT_SCRIPTS:
        text = (REPO / rel).read_text(encoding="utf-8")
        assert "SCOPE: both" in "\n".join(text.splitlines()[:8]), rel
        assert "/Users/" not in text, rel
        assert "SCOPE: both" in text, rel
