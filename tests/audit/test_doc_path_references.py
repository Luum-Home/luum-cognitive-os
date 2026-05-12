from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from scripts import cos_doc_path_audit

REPO = Path(__file__).resolve().parent.parent.parent


@pytest.mark.audit
def test_doc_path_audit_detects_missing_legacy_and_allowed_references(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    canonical = docs / "06-Daily" / "reports"
    canonical.mkdir(parents=True)
    (canonical / "ok.md").write_text("ok", encoding="utf-8")
    (docs / "99-Archive" / "archived").mkdir(parents=True)
    (docs / "99-Archive" / "archived" / "legacy.md").write_text("old", encoding="utf-8")

    script = tmp_path / "scripts" / "runner.py"
    script.parent.mkdir()
    script.write_text(
        "Path('docs/06-Daily/reports/ok.md')\n"
        "Path('docs/reports/missing.md')\n"
        "Path('docs/06-Daily/reports/*.missing')\n",
        encoding="utf-8",
    )
    archived = tmp_path / "docs" / "99-Archive" / "note.md"
    archived.write_text(
        "Historical docs/reports/old.md  # doc-path-audit: historical\n",
        encoding="utf-8",
    )

    payload = cos_doc_path_audit.audit(
        tmp_path,
        tracked_files=[
            "scripts/runner.py",
            "docs/99-Archive/note.md",
            "docs/06-Daily/reports/ok.md",
            "docs/99-Archive/archived/legacy.md",
        ],
    )

    assert payload["counts"]["missing_exact"] == 1
    assert payload["counts"]["missing_glob"] == 1
    assert payload["counts"]["legacy_runtime"] == 0
    assert payload["counts"]["historical_allowed"] == 1
    codes = {finding["code"] for finding in payload["findings"]}
    assert {"missing-exact", "missing-glob", "historical-allowed"} <= codes


@pytest.mark.audit
def test_current_repo_doc_path_references_pass_strict_gate() -> None:
    proc = subprocess.run(
        [
            "python3",
            "scripts/cos_doc_path_audit.py",
            "--json",
            "--fail-on",
            "legacy-runtime",
        ],
        cwd=REPO,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
    )
    payload = json.loads(proc.stdout)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert payload["counts"]["legacy_runtime"] == 0
    assert "missing_exact" in payload["counts"]
    assert "missing_glob" in payload["counts"]
