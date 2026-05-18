"""Behavioral tests for scripts/cos-self-improvement-runner.

Phase 4 — Headless Self-Improvement Proposer Plan.

Tests are self-contained: they invoke the runner with --dry-run so no
subprocess fan-out, no network, no file mutation occurs in the repo.
Tests that exercise --write use tmp_path for isolation.

ADR-201 contract verifications:
  1. --propose-only is required; omitting it returns exit 2.
  2. --dry-run produces valid JSON with required envelope fields.
  3. Scheduled artifact written by --write has the four required proposal
     fields (timestamp, source, proposal_text, kind).
  4. Artifact embeds adr_201_guarantee block with propose_only=True.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNNER = PROJECT_ROOT / "scripts" / "cos-self-improvement-runner"

REQUIRED_PROPOSAL_FIELDS = {"timestamp", "source", "proposal_text", "kind"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(args: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(RUNNER)] + args,
        cwd=str(cwd or PROJECT_ROOT),
        capture_output=True,
        text=True,
    )


# ---------------------------------------------------------------------------
# Contract: --propose-only is MANDATORY (ADR-201 gate)
# ---------------------------------------------------------------------------

def test_missing_propose_only_exits_with_code_2() -> None:
    """Runner must hard-fail with exit 2 when --propose-only is absent."""
    result = _run(["--dry-run"])
    assert result.returncode == 2, (
        f"Expected exit 2 when --propose-only is missing, got {result.returncode}.\n"
        f"stderr: {result.stderr}"
    )


def test_propose_only_flag_enforced_in_error_message() -> None:
    """Error message must reference --propose-only (argparse enforces it before ADR-201 check)."""
    result = _run(["--dry-run"])
    # argparse itself will mention --propose-only in the usage error
    assert "--propose-only" in result.stderr


# ---------------------------------------------------------------------------
# Smoke test: --dry-run produces valid JSON
# ---------------------------------------------------------------------------

def test_dry_run_produces_valid_json() -> None:
    """--propose-only --dry-run exits 0 and emits parseable JSON."""
    result = _run(["--propose-only", "--dry-run"])
    assert result.returncode == 0, (
        f"Unexpected exit code {result.returncode}.\nstderr: {result.stderr}"
    )
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        pytest.fail(f"Runner stdout is not valid JSON: {exc}\nstdout: {result.stdout}")
    assert isinstance(data, dict)


def test_dry_run_status_is_ok() -> None:
    """Dry-run output reports status=dry_run_ok."""
    result = _run(["--propose-only", "--dry-run"])
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data.get("status") == "dry_run_ok"


def test_dry_run_mode_field() -> None:
    """Dry-run output includes mode=dry-run."""
    result = _run(["--propose-only", "--dry-run"])
    data = json.loads(result.stdout)
    assert data.get("mode") == "dry-run"


def test_dry_run_propose_only_field_is_true() -> None:
    """Dry-run envelope asserts propose_only=True."""
    result = _run(["--propose-only", "--dry-run"])
    data = json.loads(result.stdout)
    assert data.get("propose_only") is True


def test_dry_run_proposals_is_list() -> None:
    """Dry-run returns proposals as a list (empty in dry-run mode)."""
    result = _run(["--propose-only", "--dry-run"])
    data = json.loads(result.stdout)
    assert isinstance(data.get("proposals"), list)


def test_dry_run_proposal_count_is_zero() -> None:
    """Dry-run returns proposal_count=0 since no audits run."""
    result = _run(["--propose-only", "--dry-run"])
    data = json.loads(result.stdout)
    assert data.get("proposal_count") == 0


# ---------------------------------------------------------------------------
# Schema test: written artifact has required fields + ADR-201 guarantee
# ---------------------------------------------------------------------------

def _make_minimal_plan_and_write(tmp_path: Path) -> tuple[dict, Path]:
    """
    Exercise _write_scheduled_artifact by calling the module directly with a
    synthetic plan, writing to tmp_path. Returns (artifact_dict, artifact_path).
    """
    import importlib.util
    from importlib.machinery import SourceFileLoader

    loader = SourceFileLoader("cos_self_improvement_runner", str(RUNNER))
    spec = importlib.util.spec_from_loader("cos_self_improvement_runner", loader)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)

    synthetic_plan = {
        "profile": "core",
        "status": "proposals_available",
        "proposal_count": 1,
        "proposals": [
            {
                "finding_id": "test-finding-001",
                "source": "test-suite",
                "severity": "warn",
                "title": "Test proposal",
                "summary": "A synthetic proposal for schema validation.",
                "candidate_action": "bounded_fix",
                "allowed_write_paths": ["lib/"],
                "required_tests": ["tests/unit/"],
                "human_approval_required": True,
                "blocked_actions": ["auto_merge", "auto_promote_core_or_team"],
            }
        ],
        "policy": {
            "auto_merge": False,
            "auto_promote_core_or_team": False,
            "human_approval_required": True,
        },
    }

    out_path = mod._write_scheduled_artifact(synthetic_plan, tmp_path)
    return json.loads(out_path.read_text()), out_path


def test_scheduled_artifact_has_required_proposal_fields(tmp_path: Path) -> None:
    """Each proposal in the scheduled artifact must have the four required fields."""
    artifact, _ = _make_minimal_plan_and_write(tmp_path)
    proposals = artifact.get("proposals", [])
    assert len(proposals) >= 1, "Expected at least one proposal in the artifact"
    for prop in proposals:
        missing = REQUIRED_PROPOSAL_FIELDS - set(prop.keys())
        assert not missing, f"Proposal missing required fields: {missing}"


def test_scheduled_artifact_adr201_guarantee(tmp_path: Path) -> None:
    """Artifact must embed adr_201_guarantee with propose_only=True."""
    artifact, _ = _make_minimal_plan_and_write(tmp_path)
    guarantee = artifact.get("adr_201_guarantee", {})
    assert guarantee.get("propose_only") is True
    assert guarantee.get("auto_merge_blocked") is True
    assert guarantee.get("auto_promote_blocked") is True
    assert guarantee.get("human_approval_required") is True


def test_scheduled_artifact_runner_field(tmp_path: Path) -> None:
    """Artifact must identify runner as cos-self-improvement-runner."""
    artifact, _ = _make_minimal_plan_and_write(tmp_path)
    assert artifact.get("runner") == "cos-self-improvement-runner"


def test_scheduled_artifact_mode_is_propose_only(tmp_path: Path) -> None:
    """Artifact mode field must be propose-only."""
    artifact, _ = _make_minimal_plan_and_write(tmp_path)
    assert artifact.get("mode") == "propose-only"


def test_scheduled_artifact_filename_prefix(tmp_path: Path) -> None:
    """Output file name must start with 'scheduled-'."""
    _, out_path = _make_minimal_plan_and_write(tmp_path)
    assert out_path.name.startswith("scheduled-"), (
        f"Expected filename starting with 'scheduled-', got {out_path.name}"
    )


def test_scheduled_artifact_proposal_timestamp_field(tmp_path: Path) -> None:
    """Each proposal timestamp must be a non-empty string."""
    artifact, _ = _make_minimal_plan_and_write(tmp_path)
    for prop in artifact.get("proposals", []):
        ts = prop.get("timestamp", "")
        assert isinstance(ts, str) and len(ts) > 0, (
            f"Expected non-empty timestamp string, got {ts!r}"
        )


# ---------------------------------------------------------------------------
# Profile flag is accepted
# ---------------------------------------------------------------------------

def test_dry_run_accepts_profile_flag() -> None:
    """--profile flag is accepted without errors."""
    result = _run(["--propose-only", "--dry-run", "--profile", "team"])
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data.get("profile") == "team"
