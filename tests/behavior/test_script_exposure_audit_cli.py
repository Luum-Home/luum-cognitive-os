from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "scripts" / "cos-script-exposure-audit"


def _write_ledger(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": "primitive-readiness-ledger/v1",
                "scripts": [
                    {
                        "path": "scripts/no-skill-agentic",
                        "role": "agentic-primitive",
                        "skill_consumers": 0,
                        "total_consumers": 0,
                        "consumer_families": {},
                        "consumers": [],
                    },
                    {
                        "path": "scripts/internal-maintainer",
                        "role": "maintainer-tool",
                        "skill_consumers": 0,
                        "total_consumers": 1,
                        "consumer_families": {"test": 1},
                        "consumers": [{"family": "test", "path": "tests/test_internal.py"}],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


def test_cli_outputs_json_report(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.json"
    _write_ledger(ledger)

    result = subprocess.run(
        [str(CLI), "--project-dir", str(ROOT), "--ledger", str(ledger), "--json"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report["schema_version"] == "script-exposure-audit/v1"
    assert report["summary"]["by_priority"]["P0"] == 1
    assert report["summary"]["by_exposure_class"]["P0-unrouted"] == 1
    assert report["summary"]["by_priority"]["P2"] == 1


def test_cli_fail_p0_exits_two(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.json"
    _write_ledger(ledger)

    result = subprocess.run(
        [str(CLI), "--project-dir", str(ROOT), "--ledger", str(ledger), "--fail-p0", "--json"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 2
    assert json.loads(result.stdout)["summary"]["by_priority"]["P0"] == 1
