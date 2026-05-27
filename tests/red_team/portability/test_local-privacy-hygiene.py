# SCOPE: os-only
"""Portability proof for rules/local-privacy-hygiene.md."""

from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
RULE = REPO_ROOT / "rules" / "local-privacy-hygiene.md"
GUARD = REPO_ROOT / "scripts" / "check-local-privacy.sh"


def test_local_privacy_hygiene_documented_private_policy_blocks_fixture(tmp_path: Path) -> None:
    """The shared rule's private-policy location must drive real guard behavior."""
    private_dir = tmp_path / ".cognitive-os" / "private"
    private_dir.mkdir(parents=True)
    (private_dir / "local-privacy-patterns.txt").write_text(
        "literal:fictional-internal-repo\n",
        encoding="utf-8",
    )
    doc = tmp_path / "README.md"
    doc.write_text("Do not leak fictional-internal-repo.\n", encoding="utf-8")

    result = subprocess.run(
        [str(GUARD), "--root", str(tmp_path), str(doc)],
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )

    assert result.returncode == 1
    assert "private literal pattern" in result.stderr
    assert "fictional-internal-repo" in result.stderr


def test_local_privacy_hygiene_rule_names_the_gitignored_private_policy() -> None:
    text = RULE.read_text(encoding="utf-8")

    assert ".cognitive-os/private/local-privacy-patterns.txt" in text
    assert "scripts/check-local-privacy.sh --all" in text
