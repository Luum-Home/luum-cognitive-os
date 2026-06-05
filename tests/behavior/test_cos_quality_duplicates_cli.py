from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "cos-quality-duplicates"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_cli_writes_report_and_baseline_then_fail_on_new(tmp_path: Path) -> None:
    body = "\n".join([f"line_{i} = normalize(value_{i})" for i in range(30)])
    write(tmp_path / "src" / "a.py", body)
    write(tmp_path / "src" / "b.py", body)

    first = subprocess.run([str(SCRIPT), "--project-root", str(tmp_path), "--include", "src", "--threshold", "0.5", "--write-baseline", "--json"], text=True, capture_output=True, check=False)
    assert first.returncode == 0, first.stderr
    payload = json.loads(first.stdout)
    assert payload["ratchet"]["status"] == "pass"
    assert (tmp_path / ".cognitive-os" / "reports" / "quality-duplicates" / "latest.json").exists()
    assert (tmp_path / ".cognitive-os" / "baselines" / "quality-duplicates.json").exists()

    same = subprocess.run([str(SCRIPT), "--project-root", str(tmp_path), "--include", "src", "--threshold", "0.5", "--fail-on-new"], text=True, capture_output=True, check=False)
    assert same.returncode == 0, same.stderr

    write(tmp_path / "src" / "c.py", body)
    changed = subprocess.run([str(SCRIPT), "--project-root", str(tmp_path), "--include", "src", "--threshold", "0.5", "--fail-on-new"], text=True, capture_output=True, check=False)
    assert changed.returncode == 1
