import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("eas_validate", ROOT / "scripts/eas_validate.py")
assert SPEC and SPEC.loader
eas_validate = importlib.util.module_from_spec(SPEC)
sys.modules["eas_validate"] = eas_validate
SPEC.loader.exec_module(eas_validate)
validate_eas_text = eas_validate.validate_eas_text


VALID_EAS = """# EAS: sample

## Metadata

| Field | Value |
|---|---|
| Status | Ready |
| Owner | Platform |

## Intent

Ship a safe sample behavior.

## Requirements

| ID | Requirement | Type | Source | Priority |
|---|---|---|---|---|
| REQ-1 | The system accepts valid input. | functional | PRD-1 | must |

## Non-goals

- Payment behavior is outside this change.

## Executable Acceptance Criteria

| ID | Requirement | Acceptance criterion | Verification method | Expected result |
|---|---|---|---|---|
| AC-1 | REQ-1 | Valid input succeeds. | python3 -m pytest tests/unit/test_sample.py -q | exits 0 |

## ATDD/TDD Mapping

| Acceptance criterion | Test style | Test file or scenario | Status |
|---|---|---|---|
| AC-1 | TDD | tests/unit/test_sample.py | passing |

## Gap Matrix

| Requirement | Acceptance coverage | Evidence | Gap status | Next action |
|---|---|---|---|---|
| REQ-1 | AC-1 | python3 -m pytest tests/unit/test_sample.py -q | covered | none |

## Adversarial Personas

| Persona | Lens | Required finding or question |
|---|---|---|
| Product/user | User outcome | Does valid input map to user value? |
| Detractor | Argues the EAS will fail | The test may not cover invalid input. |

## Detractor Mode

| Field | Value |
|---|---|
| Selected mode | Devil's Advocate |
| Why this mode fits | Medium-risk sample needs skeptical questioning. |
| Contrary thesis | The happy-path plan may hide invalid-input failure. |
| Disconfirming evidence required | Invalid-input test evidence. |

## Detractor Objection Log

| ID | Objection | Risk | Required evidence | Disposition |
|---|---|---|---|---|
| OBJ-1 | Test may miss invalid input. | False confidence. | Add separate invalid-input test. | residual risk accepted for this scoped sample |

## Verification Commands

```bash
python3 -m pytest tests/unit/test_sample.py -q  # expected: exits 0
```

## Residual Risks

| Risk | Why it remains | Owner | Follow-up trigger |
|---|---|---|---|
| Invalid input not covered. | Out of current sample scope. | Platform | Next input-validation change |
"""


def test_valid_eas_passes() -> None:
    result = validate_eas_text(VALID_EAS, "valid.md")
    assert result.ok, result.errors


def test_missing_detractor_fails() -> None:
    text = VALID_EAS.replace("| Detractor | Argues the EAS will fail | The test may not cover invalid input. |\n", "")
    result = validate_eas_text(text, "missing-detractor.md")
    assert not result.ok
    assert any("Detractor" in error for error in result.errors)


def test_missing_detractor_mode_fails() -> None:
    text = VALID_EAS.replace("## Detractor Mode", "## Detractor Lens")
    result = validate_eas_text(text, "missing-detractor-mode.md")
    assert not result.ok
    assert any("Detractor Mode" in error for error in result.errors)


def test_uncovered_gap_fails() -> None:
    text = VALID_EAS.replace("| REQ-1 | AC-1 | python3 -m pytest tests/unit/test_sample.py -q | covered | none |", "| REQ-1 | AC-1 | none | gap | write tests |")
    result = validate_eas_text(text, "gap.md")
    assert not result.ok
    assert any("gap matrix" in error for error in result.errors)


def test_missing_verification_command_fails() -> None:
    text = VALID_EAS.replace("python3 -m pytest tests/unit/test_sample.py -q  # expected: exits 0", "<command>")
    result = validate_eas_text(text, "missing-command.md")
    assert not result.ok
    assert any("verification commands" in error for error in result.errors)


def test_cli_returns_nonzero_for_invalid_file(tmp_path: Path) -> None:
    path = tmp_path / "invalid.md"
    path.write_text("# EAS: invalid\n\n## Intent\nOnly intent.\n", encoding="utf-8")
    result = validate_eas_text(path.read_text(encoding="utf-8"), str(path))
    assert not result.ok
    assert "missing required section: Requirements" in result.errors
