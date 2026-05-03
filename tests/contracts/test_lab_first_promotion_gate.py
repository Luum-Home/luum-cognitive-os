from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts.lab_first_promotion_gate import evaluate

pytestmark = pytest.mark.contract

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "lab_first_promotion_gate.py"


def primitive(pid: str, distribution: str = "lab", maturity: str = "advisory", state: str = "sandbox") -> dict[str, object]:
    return {
        "id": pid,
        "kind": "hook",
        "owner_adr": "ADR-133",
        "lifecycle_state": state,
        "maturity": maturity,
        "distribution": distribution,
        "risk_class": "blocking" if maturity == "blocking" else "advisory",
    }


def test_new_core_primitive_requires_boring_reliability_evidence() -> None:
    current = {"primitives": [primitive("hooks/new-core.sh", distribution="core", maturity="blocking", state="blocking")]}

    findings = evaluate({"primitives": []}, current)

    assert len(findings) == 1
    assert findings[0].field == "promotion_evidence"


def test_new_core_primitive_passes_with_boring_reliability_evidence() -> None:
    promoted = primitive("hooks/new-core.sh", distribution="core", maturity="blocking", state="blocking")
    promoted["promotion_evidence"] = {
        "boring_reliability_command": "scripts/cos-boring-reliability --profile core --json",
        "window_days": 30,
    }

    findings = evaluate({"primitives": []}, {"primitives": [promoted]})

    assert findings == []


def test_existing_unchanged_core_primitive_is_grandfathered() -> None:
    existing = primitive("hooks/existing-core.sh", distribution="core", maturity="blocking", state="blocking")

    findings = evaluate({"primitives": [existing]}, {"primitives": [existing]})

    assert findings == []


def test_demotion_does_not_require_promotion_evidence() -> None:
    old = primitive("hooks/team-task.sh", distribution="team", maturity="blocking", state="blocking")
    new = primitive("hooks/team-task.sh", distribution="team", maturity="blocking", state="demoted")

    findings = evaluate({"primitives": [old]}, {"primitives": [new]})

    assert findings == []


def test_cli_passes_against_current_branch_delta() -> None:
    result = subprocess.run(
        ["python3", str(SCRIPT), "--json"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=20,
    )

    assert result.returncode == 0, result.stdout + result.stderr
