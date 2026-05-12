from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

REPO = Path(__file__).resolve().parents[2]
TUI = REPO / "scripts" / "cos-tui"


def _write_stub_project(root: Path) -> None:
    scripts = root / "scripts"
    reports = root / "docs" / "reports"
    scripts.mkdir(parents=True)
    reports.mkdir(parents=True)
    (reports / "primitive-harness-coverage-latest.json").write_text(
        json.dumps(
            {
                "summary": {
                    "total_primitives": 1,
                    "gaps": 0,
                    "unclassified_gaps": 0,
                    "surface_projected_or_wired": {"tui": 1},
                },
                "surfaces": [{"surface_id": "tui", "surface_kind": "ui"}],
            }
        ),
        encoding="utf-8",
    )
    (reports / "primitive-harness-partials-latest.json").write_text(
        json.dumps({"summary": {"partial_count": 0}}),
        encoding="utf-8",
    )
    for name in ["primitive_harness_coverage.py", "primitive_harness_partials.py"]:
        path = scripts / name
        path.write_text(
            "#!/usr/bin/env python3\nfrom pathlib import Path\nPath('docs/06-Daily/reports/stub-ran.txt').write_text('ran')\nprint('ok')\n",
            encoding="utf-8",
        )
        path.chmod(0o755)


def test_tui_operable_action_requires_confirmation(tmp_path: Path) -> None:
    _write_stub_project(tmp_path)
    result = subprocess.run(
        ["python3", str(TUI), "--project-dir", str(tmp_path), "--operate", "refresh-all"],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "without --confirm" in result.stderr


def test_tui_operable_action_runs_only_whitelisted_commands_and_emits_receipt(tmp_path: Path) -> None:
    _write_stub_project(tmp_path)
    result = subprocess.run(
        ["python3", str(TUI), "--project-dir", str(tmp_path), "--operate", "refresh-all", "--confirm"],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    receipt_path = tmp_path / ".cognitive-os" / "metrics" / "tui-actions.jsonl"
    receipts = [json.loads(line) for line in receipt_path.read_text(encoding="utf-8").splitlines()]
    assert receipts[-1]["schema_version"] == "cos-tui-action-receipt.v1"
    assert receipts[-1]["surface_id"] == "tui"
    assert receipts[-1]["mode"] == "operable"
    assert receipts[-1]["action"] == "refresh-all"
    assert receipts[-1]["outcome"] == "success"
    assert receipts[-1]["whitelisted"] is True
    assert all(command[0] == "python3" for command in receipts[-1]["commands"])


def test_tui_dry_run_emits_receipt_without_running_commands(tmp_path: Path) -> None:
    _write_stub_project(tmp_path)
    result = subprocess.run(
        ["python3", str(TUI), "--project-dir", str(tmp_path), "--operate", "refresh-coverage", "--dry-run"],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["outcome"] == "dry-run"
    assert not (tmp_path / "docs" / "reports" / "stub-ran.txt").exists()


def test_tui_receipts_report_has_schema_and_counts(tmp_path: Path) -> None:
    _write_stub_project(tmp_path)
    subprocess.run(
        ["python3", str(TUI), "--project-dir", str(tmp_path), "--operate", "refresh-coverage", "--dry-run"],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=True,
    )
    result = subprocess.run(
        ["python3", str(TUI), "--project-dir", str(tmp_path), "--receipts", "--json"],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "cos-tui-action-receipt-stats.v1"
    assert payload["receipt_schema_version"] == "cos-tui-action-receipt.v1"
    assert payload["total"] == 1
    assert payload["by_action"] == {"refresh-coverage": 1}
    assert payload["by_outcome"] == {"dry-run": 1}


def test_tui_receipt_jsonl_rows_follow_schema(tmp_path: Path) -> None:
    _write_stub_project(tmp_path)
    subprocess.run(
        ["python3", str(TUI), "--project-dir", str(tmp_path), "--operate", "refresh-all", "--confirm"],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=True,
    )
    receipt_path = tmp_path / ".cognitive-os" / "metrics" / "tui-actions.jsonl"
    for raw in receipt_path.read_text(encoding="utf-8").splitlines():
        row = json.loads(raw)
        assert set(["schema_version", "timestamp", "surface_kind", "surface_id", "mode", "action", "outcome", "project_dir", "commands", "whitelisted", "details"]) <= set(row)
        assert row["schema_version"] == "cos-tui-action-receipt.v1"
        assert row["surface_kind"] == "ui"
        assert row["surface_id"] == "tui"
        assert row["mode"] == "operable"
        assert row["whitelisted"] is True
