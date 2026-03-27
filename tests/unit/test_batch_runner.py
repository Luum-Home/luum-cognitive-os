"""Unit tests for lib/batch_runner.py

Validates ChangeResult/PhaseResult dataclasses, YAML batch file parsing,
phase list resolution, timing summary formatting, JSON report generation,
dry-run mode, continue-on-failure, and exit codes.
"""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_LIB_DIR = str(Path(__file__).resolve().parent.parent.parent / "lib")
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from batch_runner import (
    ChangeResult,
    ChangeSpec,
    PhaseResult,
    SDD_PHASES,
    _build_phase_prompt,
    _format_duration,
    _validate_phase,
    generate_json_report,
    load_batch_yaml,
    main,
    resolve_phases,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Dataclass creation
# ---------------------------------------------------------------------------


class TestPhaseResult:
    def test_defaults(self):
        pr = PhaseResult(phase="apply", success=True, elapsed_seconds=12.5)
        assert pr.phase == "apply"
        assert pr.success is True
        assert pr.elapsed_seconds == 12.5
        assert pr.error_message == ""
        assert pr.tokens_in == 0
        assert pr.cost_usd == 0.0

    def test_with_error(self):
        pr = PhaseResult(
            phase="verify", success=False, elapsed_seconds=5.0,
            error_message="Build failed",
        )
        assert pr.success is False
        assert pr.error_message == "Build failed"


class TestChangeResult:
    def test_defaults(self):
        cr = ChangeResult(name="add-auth", success=True, elapsed_seconds=60.0)
        assert cr.name == "add-auth"
        assert cr.phase_results == []
        assert cr.failed_phase is None
        assert cr.total_cost_usd == 0.0

    def test_to_dict(self):
        pr = PhaseResult(
            phase="apply", success=True, elapsed_seconds=10.0,
            tokens_in=100, tokens_out=50, cost_usd=0.01,
        )
        cr = ChangeResult(
            name="add-auth", success=True, elapsed_seconds=10.0,
            phase_results=[pr], total_cost_usd=0.01,
            total_tokens_in=100, total_tokens_out=50,
        )
        d = cr.to_dict()
        assert d["name"] == "add-auth"
        assert d["success"] is True
        assert len(d["phases"]) == 1
        assert d["phases"][0]["phase"] == "apply"
        assert d["total_cost_usd"] == 0.01

    def test_to_dict_with_failure(self):
        cr = ChangeResult(
            name="fix-bug", success=False, elapsed_seconds=5.0,
            failed_phase="verify",
        )
        d = cr.to_dict()
        assert d["failed_phase"] == "verify"


# ---------------------------------------------------------------------------
# Phase validation
# ---------------------------------------------------------------------------


class TestValidatePhase:
    def test_valid_phases(self):
        for phase in SDD_PHASES:
            assert _validate_phase(phase) is True

    def test_invalid_phase(self):
        assert _validate_phase("deploy") is False
        assert _validate_phase("") is False


class TestBuildPhasePrompt:
    def test_known_phases(self):
        for phase in SDD_PHASES:
            prompt = _build_phase_prompt(phase, "my-change")
            assert "my-change" in prompt

    def test_unknown_phase_raises(self):
        with pytest.raises(ValueError, match="Unknown SDD phase"):
            _build_phase_prompt("deploy", "my-change")


# ---------------------------------------------------------------------------
# Phase resolution
# ---------------------------------------------------------------------------


class TestResolvePhases:
    def test_change_level_phases(self):
        change = ChangeSpec(name="add-auth", phases=["propose", "spec"])
        result = resolve_phases(change, None, False)
        assert result == ["propose", "spec"]

    def test_global_phase(self):
        change = ChangeSpec(name="add-auth")
        result = resolve_phases(change, "propose", False)
        assert result == ["propose"]

    def test_fast_forward(self):
        change = ChangeSpec(name="add-auth")
        result = resolve_phases(change, None, True)
        assert result == list(SDD_PHASES)

    def test_default_all_phases(self):
        change = ChangeSpec(name="add-auth")
        result = resolve_phases(change, None, False)
        assert result == list(SDD_PHASES)

    def test_change_phases_override_global(self):
        change = ChangeSpec(name="add-auth", phases=["apply"])
        result = resolve_phases(change, "propose", True)
        assert result == ["apply"]


# ---------------------------------------------------------------------------
# Duration formatting
# ---------------------------------------------------------------------------


class TestFormatDuration:
    def test_seconds(self):
        assert _format_duration(30.5) == "30.5s"

    def test_minutes(self):
        result = _format_duration(125.0)
        assert "2m" in result

    def test_hours(self):
        result = _format_duration(7200.0)
        assert "2h" in result


# ---------------------------------------------------------------------------
# YAML batch file parsing
# ---------------------------------------------------------------------------


class TestLoadBatchYaml:
    def test_basic_yaml(self, tmp_path):
        yaml_content = """
changes:
  - name: add-auth
    phases: [propose, spec]
  - name: fix-bug
"""
        f = tmp_path / "batch.yaml"
        f.write_text(yaml_content)

        changes = load_batch_yaml(str(f))
        assert len(changes) == 2
        assert changes[0].name == "add-auth"
        assert changes[0].phases == ["propose", "spec"]
        assert changes[1].name == "fix-bug"
        assert changes[1].phases is None

    def test_string_entries(self, tmp_path):
        yaml_content = """
changes:
  - add-auth
  - fix-bug
"""
        f = tmp_path / "batch.yaml"
        f.write_text(yaml_content)

        changes = load_batch_yaml(str(f))
        assert len(changes) == 2
        assert changes[0].name == "add-auth"

    def test_missing_file_exits(self, tmp_path):
        with pytest.raises(SystemExit):
            load_batch_yaml(str(tmp_path / "nonexistent.yaml"))

    def test_invalid_format_exits(self, tmp_path):
        f = tmp_path / "bad.yaml"
        f.write_text("just a string")
        with pytest.raises(SystemExit):
            load_batch_yaml(str(f))

    def test_invalid_phase_exits(self, tmp_path):
        yaml_content = """
changes:
  - name: add-auth
    phases: [propose, deploy]
"""
        f = tmp_path / "batch.yaml"
        f.write_text(yaml_content)
        with pytest.raises(SystemExit):
            load_batch_yaml(str(f))

    def test_empty_changes_exits(self, tmp_path):
        yaml_content = """
changes: []
"""
        f = tmp_path / "batch.yaml"
        f.write_text(yaml_content)
        with pytest.raises(SystemExit):
            load_batch_yaml(str(f))


# ---------------------------------------------------------------------------
# JSON report generation
# ---------------------------------------------------------------------------


class TestGenerateJsonReport:
    def test_report_structure(self, tmp_path):
        pr = PhaseResult(
            phase="apply", success=True, elapsed_seconds=10.0,
            tokens_in=100, tokens_out=50, cost_usd=0.01,
        )
        results = [
            ChangeResult(
                name="add-auth", success=True, elapsed_seconds=10.0,
                phase_results=[pr], total_cost_usd=0.01,
            ),
            ChangeResult(
                name="fix-bug", success=False, elapsed_seconds=5.0,
                failed_phase="verify", total_cost_usd=0.005,
            ),
        ]

        report_path = str(tmp_path / "report.json")
        generate_json_report(results, 15.0, "fast-forward", report_path)

        with open(report_path) as f:
            report = json.load(f)

        assert report["summary"]["total_changes"] == 2
        assert report["summary"]["succeeded"] == 1
        assert report["summary"]["failed"] == 1
        assert len(report["changes"]) == 2
        assert len(report["failed_changes"]) == 1
        assert report["failed_changes"][0]["name"] == "fix-bug"

    def test_report_creates_parent_dirs(self, tmp_path):
        results = [
            ChangeResult(name="x", success=True, elapsed_seconds=1.0),
        ]
        report_path = str(tmp_path / "sub" / "dir" / "report.json")
        generate_json_report(results, 1.0, "single", report_path)
        assert Path(report_path).exists()


# ---------------------------------------------------------------------------
# CLI main() — dry-run and exit codes
# ---------------------------------------------------------------------------


class TestMain:
    def test_dry_run(self):
        exit_code = main(["add-auth", "--fast-forward", "--dry-run"])
        assert exit_code == 0

    def test_no_args_returns_1(self):
        exit_code = main([])
        assert exit_code == 1

    def test_invalid_phase_returns_1(self):
        exit_code = main(["add-auth", "--phase", "deploy"])
        assert exit_code == 1

    @patch("batch_runner.ClaudeExecutor")
    def test_all_pass_returns_0(self, mock_executor_cls):
        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor

        # Simulate successful runs for all phases
        from claude_executor import ClaudeResult
        mock_executor.run.return_value = ClaudeResult(
            success=True, result_text="ok", duration_secs=1.0,
        )

        exit_code = main(["add-auth", "--phase", "propose"])
        assert exit_code == 0

    @patch("batch_runner.ClaudeExecutor")
    def test_failure_returns_1(self, mock_executor_cls):
        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor

        from claude_executor import ClaudeResult
        mock_executor.run.return_value = ClaudeResult(
            success=False, result_text="fail", duration_secs=1.0,
            error_message="Phase failed",
        )

        exit_code = main(["add-auth", "--phase", "propose"])
        assert exit_code == 1

    @patch("batch_runner.ClaudeExecutor")
    def test_continue_on_failure(self, mock_executor_cls):
        mock_executor = MagicMock()
        mock_executor_cls.return_value = mock_executor

        from claude_executor import ClaudeResult
        # First change fails, second succeeds
        fail_result = ClaudeResult(
            success=False, result_text="fail", duration_secs=1.0,
            error_message="Phase failed",
        )
        ok_result = ClaudeResult(
            success=True, result_text="ok", duration_secs=1.0,
        )
        mock_executor.run.side_effect = [fail_result, ok_result]

        exit_code = main([
            "change1", "change2",
            "--phase", "propose",
            "--continue-on-failure",
        ])
        # Should still return 1 because one failed
        assert exit_code == 1
        # But should have run both changes
        assert mock_executor.run.call_count == 2
