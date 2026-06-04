# SCOPE: os-only
"""Portability proof for scripts/provenance_scan.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCANNER = REPO_ROOT / "scripts" / "provenance_scan.py"


def test_scanner_uses_cognitive_os_policy_in_adopted_repo(tmp_path: Path) -> None:
    project = tmp_path / "consumer"
    policy_dir = project / ".cognitive-os"
    policy_dir.mkdir(parents=True)
    (policy_dir / "provenance-scan.yaml").write_text(
        "schema_version: provenance-scan/v1\n"
        "provenance:\n"
        "  forbidden_terms: [SourceLeak]\n",
        encoding="utf-8",
    )
    (project / "README.md").write_text("SourceLeak\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCANNER), "--root", str(project), "--json", "README.md"],
        cwd=project,
        text=True,
        capture_output=True,
        check=False,
        timeout=20,
    )

    assert result.returncode == 1
    assert '"config": ".cognitive-os/provenance-scan.yaml"' in result.stdout
    assert '"category": "forbidden-term"' in result.stdout
