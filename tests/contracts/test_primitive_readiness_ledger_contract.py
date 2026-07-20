from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.contract, pytest.mark.timeout(180)]

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "primitive_readiness_ledger.py"

# Import the generator module directly so the expected script count is derived
# from the SAME file-discovery function the generator uses to build the
# ledger (including its suffix/ignore filtering), instead of a hand-rolled
# re-implementation in the test that can silently drift out of sync (that
# drift previously caused a non-deterministic 738 vs 739 failure).
_SPEC = importlib.util.spec_from_file_location("primitive_readiness_ledger", SCRIPT)
assert _SPEC and _SPEC.loader
primitive_readiness_ledger = importlib.util.module_from_spec(_SPEC)
sys.modules["primitive_readiness_ledger"] = primitive_readiness_ledger
_SPEC.loader.exec_module(primitive_readiness_ledger)


def test_repository_script_ledger_classifies_every_script(tmp_path: Path) -> None:
    json_out = tmp_path / "primitive-readiness-ledger-scripts-latest.json"
    md_out = tmp_path / "primitive-readiness-ledger-scripts-latest.md"
    backlog_json_out = tmp_path / "primitive-readiness-lifecycle-backlog-scripts-latest.json"
    backlog_md_out = tmp_path / "primitive-readiness-lifecycle-backlog-scripts-latest.md"

    result = subprocess.run(
        [
            "python3",
            str(SCRIPT),
            "--project-dir",
            str(REPO_ROOT),
            "--json-out",
            str(json_out),
            "--md-out",
            str(md_out),
            "--lifecycle-backlog-json-out",
            str(backlog_json_out),
            "--lifecycle-backlog-md-out",
            str(backlog_md_out),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=90,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(json_out.read_text())

    expected_script_count = len(primitive_readiness_ledger.script_files(REPO_ROOT))
    assert payload["summary"]["total_scripts"] == expected_script_count
    assert "consumer_accessibility" in payload["summary"]
    assert all(row["role"] in payload["allowed_roles"] for row in payload["scripts"])
    assert all(row["consumer_accessibility"] for row in payload["scripts"])
    assert all(row["consumer_access_next_action"] for row in payload["scripts"])
    assert not any(row["role"] == "unknown" for row in payload["scripts"])
    backlog = json.loads(backlog_json_out.read_text())
    assert backlog["summary"]["total"] == 0
