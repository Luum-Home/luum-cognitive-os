from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_stash_quarantine_audit_runs_on_consumer_fixture(tmp_path: Path) -> None:
    unsafe = tmp_path / "unsafe.md"
    unsafe.write_text("Run git stash pop when done.\n", encoding="utf-8")

    result = subprocess.run(
        ["python3", str(ROOT / "scripts" / "stash_quarantine_audit.py"), "--project-dir", str(tmp_path), "--json", "--fail", "unsafe.md"],
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )

    payload = json.loads(result.stdout)
    assert result.returncode == 1
    assert payload["finding_count"] == 1
    assert payload["findings"][0]["code"] == "bare-stash-operation"
