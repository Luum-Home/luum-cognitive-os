from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts import cos_task_closure_gate as gate

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "cos_task_closure_gate.py"
WRAPPER = REPO / "scripts" / "cos-task-closure-gate"


def write_ledger(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "closure.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def base_front(**overrides: object) -> dict:
    front = {
        "id": "runtime-api",
        "title": "Runtime API",
        "status": "ready_next_slice",
        "canClaimComplete": False,
        "closureGate": "python3 -c 'raise SystemExit(0)'",
        "doneEvidence": ["bounded parser proof exists"],
        "remaining": ["production scheduler integration"],
        "nextPrimitive": "Add scheduler integration gate.",
    }
    front.update(overrides)
    return front


def base_payload(*fronts: dict, field: str = "fronts") -> dict:
    return {
        "schemaVersion": 1,
        "contract": gate.CONTRACT,
        field: list(fronts) or [base_front()],
    }


def test_open_front_is_valid_but_not_claimable(tmp_path: Path) -> None:
    path = write_ledger(tmp_path, base_payload(base_front()))

    report = gate.build_report(path, project_dir=tmp_path)

    assert report.status == "pass"
    assert report.total_fronts == 1
    assert report.closed_fronts == 0
    assert report.claimable_fronts == 0
    assert [warning.code for warning in report.warnings] == ["front-not-closed"]


def test_require_closed_fails_for_open_front(tmp_path: Path) -> None:
    path = write_ledger(tmp_path, base_payload(base_front()))

    report = gate.build_report(path, project_dir=tmp_path, require_closed=True)

    assert report.status == "fail"
    assert any(item.code == "require-closed-open-front" for item in report.findings)


def test_closed_front_requires_can_claim_complete(tmp_path: Path) -> None:
    path = write_ledger(tmp_path, base_payload(base_front(status="closed", canClaimComplete=False, remaining=[])))

    report = gate.build_report(path, project_dir=tmp_path)

    assert report.status == "fail"
    assert any(item.code == "closed-requires-claimable" for item in report.findings)


def test_can_claim_complete_requires_closed(tmp_path: Path) -> None:
    path = write_ledger(tmp_path, base_payload(base_front(canClaimComplete=True)))

    report = gate.build_report(path, project_dir=tmp_path)

    assert report.status == "fail"
    assert any(item.code == "claimable-requires-closed" for item in report.findings)


def test_closed_front_requires_gate_evidence_when_requested(tmp_path: Path) -> None:
    path = write_ledger(tmp_path, base_payload(base_front(status="closed", canClaimComplete=True, remaining=[])))

    report = gate.build_report(path, project_dir=tmp_path, require_gates_passed=True)

    assert report.status == "fail"
    assert any(item.code == "closed-front-missing-gate-evidence" for item in report.findings)


def test_closed_front_with_gate_evidence_passes_strict(tmp_path: Path) -> None:
    path = write_ledger(
        tmp_path,
        base_payload(base_front(status="closed", canClaimComplete=True, remaining=[], closureGatePassed=True)),
    )

    report = gate.build_report(path, project_dir=tmp_path, require_closed=True, require_gates_passed=True)

    assert report.status == "pass"
    assert report.closed_fronts == 1
    assert report.claimable_fronts == 1


def test_duplicate_ids_fail(tmp_path: Path) -> None:
    path = write_ledger(tmp_path, base_payload(base_front(id="same"), base_front(id="same")))

    report = gate.build_report(path, project_dir=tmp_path)

    assert report.status == "fail"
    assert any(item.code == "duplicate-front-id" for item in report.findings)


def test_items_alias_is_accepted_with_warning(tmp_path: Path) -> None:
    path = write_ledger(tmp_path, base_payload(base_front(), field="items"))

    report = gate.build_report(path, project_dir=tmp_path)

    assert report.status == "pass"
    assert any(item.code == "items-alias-used" for item in report.warnings)


def test_run_closure_gates_executes_closed_fronts_only_by_default(tmp_path: Path) -> None:
    pass_marker = tmp_path / "pass.txt"
    skip_marker = tmp_path / "skip.txt"
    path = write_ledger(
        tmp_path,
        base_payload(
            base_front(
                id="closed",
                status="closed",
                canClaimComplete=True,
                remaining=[],
                closureGate=f"python3 -c \"from pathlib import Path; Path('{pass_marker}').write_text('ok')\"",
            ),
            base_front(
                id="open",
                closureGate=f"python3 -c \"from pathlib import Path; Path('{skip_marker}').write_text('bad')\"",
            ),
        ),
    )

    report = gate.build_report(path, project_dir=tmp_path, run_closure_gates=True)

    assert report.status == "pass"
    assert pass_marker.read_text() == "ok"
    assert not skip_marker.exists()
    assert [run.front_id for run in report.gate_runs] == ["closed"]


def test_run_all_gates_fails_on_open_gate_failure(tmp_path: Path) -> None:
    path = write_ledger(tmp_path, base_payload(base_front(closureGate="python3 -c 'raise SystemExit(7)'")))

    report = gate.build_report(path, project_dir=tmp_path, run_closure_gates=True, run_all_gates=True)

    assert report.status == "fail"
    assert report.gate_runs[0].returncode == 7
    assert any(item.code == "closure-gate-command-failed" for item in report.findings)


def test_cli_json_and_wrapper(tmp_path: Path) -> None:
    path = write_ledger(tmp_path, base_payload(base_front()))

    cp = subprocess.run([sys.executable, str(SCRIPT), str(path), "--json"], text=True, capture_output=True, check=False)
    wrapper = subprocess.run([str(WRAPPER), str(path), "--json"], text=True, capture_output=True, check=False)

    assert cp.returncode == 0
    assert wrapper.returncode == 0
    assert json.loads(cp.stdout)["schema_version"] == gate.SCHEMA_VERSION
    assert json.loads(wrapper.stdout)["status"] == "pass"


def test_cli_require_closed_exits_nonzero(tmp_path: Path) -> None:
    path = write_ledger(tmp_path, base_payload(base_front()))

    cp = subprocess.run([sys.executable, str(SCRIPT), str(path), "--require-closed"], text=True, capture_output=True, check=False)

    assert cp.returncode == 1
    assert "require-closed requested" in cp.stderr
