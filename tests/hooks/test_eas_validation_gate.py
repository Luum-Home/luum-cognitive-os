"""Behavioral tests for hooks/eas-validation-gate.sh.

Tests verify:
- No-op when COS_REVIEW_SURFACE and COS_EAS_PATH are not set (fast path).
- Pass (exit 0, no block JSON) when EAS file is valid.
- Block (exit 0, JSON with decision=block) when EAS file has uncovered rows.
- Runtime disable via DISABLE_HOOK_EAS_VALIDATION_GATE=true.
- Kill-switch via COS_DISABLE_ALL_GOVERNANCE=1.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from textwrap import dedent

import pytest

from tests.hooks.conftest import PROJECT_ROOT


HOOKS_DIR = PROJECT_ROOT / "hooks"
HOOK_PATH = HOOKS_DIR / "eas-validation-gate.sh"

pytestmark = [pytest.mark.behavior]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_EAS = dedent("""\
    # EAS: test-change

    ## Intent
    Test EAS artifact for validation gate behavioral tests.

    ## Requirements

    | ID | Requirement | Type | Source | Priority |
    |---|---|---|---|---|
    | REQ-1 | WHEN the system starts THE SYSTEM SHALL emit a ready signal | functional | ADR-324 | must |

    ## Non-goals
    - Out of scope item.

    ## Executable Acceptance Criteria

    | ID | Requirement | Acceptance criterion | Verification method | Expected result |
    |---|---|---|---|---|
    | AC-1 | REQ-1 | Ready signal observed in log | pytest | exit 0 |

    ## ATDD/TDD Mapping

    | Acceptance criterion | Test style | Test file or scenario | Status |
    |---|---|---|---|
    | AC-1 | unit | tests/unit/test_ready.py | planned |

    ## Gap Matrix

    | Requirement | Acceptance coverage | Evidence | Gap status | Next action |
    |---|---|---|---|---|
    | REQ-1 | AC-1 | pytest tests/unit/test_ready.py | covered | none |

    ## Adversarial Personas

    | Persona | Lens | Required finding or question |
    |---|---|---|
    | Detractor | Tenth-Man reviewer | Will the ready signal always be emitted? |

    ## Detractor Mode

    | Field | Value |
    |---|---|
    | Selected mode | Devil's Advocate |
    | Why this mode fits | Medium change with convergence risk |
    | Contrary thesis | Signal might be suppressed on error paths |
    | Disconfirming evidence required | Error path tests showing signal still emitted |

    ## Detractor Objection Log

    | ID | Objection | Risk | Required evidence | Disposition |
    |---|---|---|---|---|
    | OBJ-1 | Signal may be suppressed | high | Error path tests | resolved |

    ## Verification Commands

    ```bash
    pytest tests/unit/test_ready.py -q  # expected: all pass
    ```

    ## Residual Risks

    | Risk | Likelihood | Impact | Mitigation |
    |---|---|---|---|
    | Error path gap | low | medium | Covered by OBJ-1 resolution |
""")


INVALID_EAS = dedent("""\
    # EAS: broken-change

    ## Intent
    Broken EAS missing most required sections.

    ## Requirements

    | ID | Requirement | Type |
    |---|---|---|
    | REQ-1 | THE SYSTEM SHALL do something | functional |

    ## Non-goals
    - Nothing.
""")


@pytest.fixture
def valid_eas_file(tmp_path: Path) -> Path:
    """Write a valid EAS Markdown file to a temp path."""
    eas = tmp_path / "eas.md"
    eas.write_text(VALID_EAS, encoding="utf-8")
    return eas


@pytest.fixture
def invalid_eas_file(tmp_path: Path) -> Path:
    """Write an invalid EAS Markdown file (missing sections) to a temp path."""
    eas = tmp_path / "eas.md"
    eas.write_text(INVALID_EAS, encoding="utf-8")
    return eas


def _run_hook(env_overrides: dict[str, str] | None = None, stdin: str = "") -> subprocess.CompletedProcess:
    """Run eas-validation-gate.sh and return CompletedProcess."""
    if not HOOK_PATH.exists():
        pytest.skip("eas-validation-gate.sh not found")

    run_env = os.environ.copy()
    run_env.update(
        {
            "CLAUDE_PROJECT_DIR": str(PROJECT_ROOT),
            "COGNITIVE_OS_PROJECT_DIR": str(PROJECT_ROOT),
            "COGNITIVE_OS_HOOK_HEARTBEAT": "false",
        }
    )
    if env_overrides:
        run_env.update(env_overrides)

    return subprocess.run(
        ["bash", str(HOOK_PATH)],
        input=stdin,
        capture_output=True,
        text=True,
        env=run_env,
        timeout=15,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestNoOpWhenNoSurface:
    """Hook must exit 0 silently when no review surface is active."""

    def test_no_env_vars_is_noop(self) -> None:
        result = _run_hook(
            env_overrides={
                "COS_REVIEW_SURFACE": "",
                "COS_EAS_PATH": "",
            }
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_noop_is_fast(self) -> None:
        import time

        start = time.perf_counter()
        _run_hook(env_overrides={"COS_REVIEW_SURFACE": "", "COS_EAS_PATH": ""})
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 500, f"No-op took {elapsed_ms:.0f}ms (must be <500ms)"


class TestKillSwitches:
    """Kill-switches must exit 0 immediately."""

    def test_global_governance_killswitch(self) -> None:
        result = _run_hook(
            env_overrides={
                "COS_DISABLE_ALL_GOVERNANCE": "1",
                "COS_REVIEW_SURFACE": "sdd-verify",
                "COS_EAS_PATH": "/tmp/does-not-exist.md",
            }
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_hook_specific_disable(self) -> None:
        result = _run_hook(
            env_overrides={
                "DISABLE_HOOK_EAS_VALIDATION_GATE": "true",
                "COS_REVIEW_SURFACE": "sdd-verify",
                "COS_EAS_PATH": "/tmp/does-not-exist.md",
            }
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""


class TestValidEAS:
    """Hook must exit 0 without a block payload when EAS file is valid."""

    def test_valid_eas_passes(self, valid_eas_file: Path) -> None:
        result = _run_hook(
            env_overrides={
                "COS_REVIEW_SURFACE": "sdd-verify",
                "COS_EAS_PATH": str(valid_eas_file),
            }
        )
        assert result.returncode == 0
        stdout = result.stdout.strip()
        # Must not emit a block decision
        if stdout:
            payload = json.loads(stdout)
            assert payload.get("decision") != "block", (
                f"Hook blocked on valid EAS: {stdout}"
            )

    def test_valid_eas_all_review_surfaces(self, valid_eas_file: Path) -> None:
        for surface in ("sdd-verify", "pr-review", "code-review", "doc-review"):
            result = _run_hook(
                env_overrides={
                    "COS_REVIEW_SURFACE": surface,
                    "COS_EAS_PATH": str(valid_eas_file),
                }
            )
            assert result.returncode == 0, f"Failed on surface={surface}: {result.stderr}"
            stdout = result.stdout.strip()
            if stdout:
                payload = json.loads(stdout)
                assert payload.get("decision") != "block", (
                    f"Blocked on valid EAS for surface={surface}"
                )


class TestInvalidEAS:
    """Hook must emit a block JSON payload when EAS file has validation errors."""

    def test_invalid_eas_emits_block(self, invalid_eas_file: Path) -> None:
        result = _run_hook(
            env_overrides={
                "COS_REVIEW_SURFACE": "sdd-verify",
                "COS_EAS_PATH": str(invalid_eas_file),
            }
        )
        assert result.returncode == 0  # Stop hooks always exit 0
        stdout = result.stdout.strip()
        assert stdout, "Expected block JSON output but got empty stdout"

        payload = json.loads(stdout)
        assert payload.get("decision") == "block", f"Expected block, got: {payload}"
        assert "reason" in payload
        assert "hookSpecificOutput" in payload
        ctx = payload["hookSpecificOutput"]["additionalContext"]
        assert "EAS" in ctx or "eas" in ctx.lower()
        assert "sdd-verify" in ctx

    def test_block_payload_schema(self, invalid_eas_file: Path) -> None:
        """Block payload must have decision, reason, hookSpecificOutput.additionalContext."""
        result = _run_hook(
            env_overrides={
                "COS_REVIEW_SURFACE": "code-review",
                "COS_EAS_PATH": str(invalid_eas_file),
            }
        )
        stdout = result.stdout.strip()
        assert stdout, "Expected block JSON"
        payload = json.loads(stdout)

        assert isinstance(payload.get("decision"), str)
        assert isinstance(payload.get("reason"), str)
        assert isinstance(payload.get("hookSpecificOutput"), dict)
        assert isinstance(
            payload["hookSpecificOutput"].get("additionalContext"), str
        )

    def test_missing_eas_file_is_noop(self) -> None:
        """If COS_EAS_PATH points to a non-existent file, hook must not block."""
        result = _run_hook(
            env_overrides={
                "COS_REVIEW_SURFACE": "sdd-verify",
                "COS_EAS_PATH": "/tmp/nonexistent-eas-file-xyz.md",
            }
        )
        assert result.returncode == 0
        stdout = result.stdout.strip()
        if stdout:
            payload = json.loads(stdout)
            assert payload.get("decision") != "block"

    def test_idempotent_multiple_runs(self, invalid_eas_file: Path) -> None:
        """Running the hook twice must produce identical block output."""
        env = {
            "COS_REVIEW_SURFACE": "pr-review",
            "COS_EAS_PATH": str(invalid_eas_file),
        }
        r1 = _run_hook(env_overrides=env)
        r2 = _run_hook(env_overrides=env)

        assert r1.returncode == r2.returncode
        p1 = json.loads(r1.stdout.strip())
        p2 = json.loads(r2.stdout.strip())
        assert p1.get("decision") == p2.get("decision")
