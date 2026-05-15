from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_eas_validator_accepts_complete_consumer_project_eas(tmp_path: Path) -> None:
    eas = tmp_path / "consumer-eas.md"
    eas.write_text(
        """# EAS: consumer-login-hardening

## Intent
Harden login behavior for consumer repository users.

## Requirements
| ID | Requirement | Type | Source | Priority |
|---|---|---|---|---|
| REQ-1 | IF the password is invalid THEN THE SYSTEM SHALL return a stable authentication error. | functional | PRD | must |

## Non-goals
- This does not change account recovery.

## Executable Acceptance Criteria
| ID | Requirement | Acceptance criterion | Verification method | Expected result |
|---|---|---|---|---|
| AC-1 | REQ-1 | Invalid password returns 401. | pytest tests/test_login.py -q | pass |

## Gap Matrix
| Requirement | Acceptance coverage | Evidence | Gap status | Next action |
|---|---|---|---|---|
| REQ-1 | AC-1 | pytest tests/test_login.py -q | covered | none |

## Adversarial Personas
| Persona | Lens | Required finding or question |
|---|---|---|
| Detractor | Argues the EAS will fail | Missing legacy client coverage? |

## Detractor Mode
| Field | Value |
|---|---|
| Selected mode | Devil's Advocate |
| Why this mode fits | Login hardening needs skeptical compatibility review. |
| Contrary thesis | Stable errors may still break legacy clients. |
| Disconfirming evidence required | Compatibility test evidence. |

## Detractor Objection Log
| ID | Objection | Risk | Required evidence | Disposition |
|---|---|---|---|---|
| OBJ-1 | Legacy clients may see ambiguous errors. | Regression | compatibility test | resolved by AC-1 |

## Verification Commands
```bash
pytest tests/test_login.py -q  # expected: pass
```

## Residual Risks
No residual risks remain after AC-1 passes.
""",
        encoding="utf-8",
    )

    result = subprocess.run(
        ["python3", "scripts/eas_validate.py", "--require-ears", str(eas)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )

    assert result.returncode == 0, result.stdout + result.stderr
