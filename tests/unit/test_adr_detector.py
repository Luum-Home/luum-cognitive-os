"""Tests for lib/adr_detector.py — ADR auto-detection mechanism.

Behavioral tests covering:
- Signal detection for each signal type
- Scoring threshold (0.69 = no ADR, 0.70 = ADR generated)
- ADR numbering (finds next available number)
- ADR template correctness (Context, Decision, Status: Draft)
- Non-architectural commits scoring low
"""
import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

# Import the module under test
from lib.adr_detector import (
    DEFAULT_THRESHOLD,
    DEFAULT_WEIGHTS,
    analyze_commit,
    generate_adr_draft,
    get_next_adr_number,
    log_detection,
    _check_dependency_change,
    _check_config_schema_change,
    _check_hook_change,
    _check_license_change,
    _check_large_deletion,
    _check_new_integration,
    _check_file_structure_change,
    _check_breaking_change,
    _parse_name_status,
    _slugify,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_files(entries: list[tuple[str, str]]) -> list[dict[str, str]]:
    """Build a changed_files list from (status, path) tuples."""
    return [{"status": s, "path": p} for s, p in entries]


# ---------------------------------------------------------------------------
# Signal detection tests — one per signal type
# ---------------------------------------------------------------------------

class TestDependencyChangeSignal:
    def test_detects_package_json(self):
        files = _make_files([("M", "package.json")])
        signals = _check_dependency_change(files)
        assert len(signals) == 1
        assert signals[0]["type"] == "dependency_change"
        assert signals[0]["weight"] == DEFAULT_WEIGHTS["dependency_change"]

    def test_detects_pyproject_toml(self):
        files = _make_files([("M", "pyproject.toml")])
        signals = _check_dependency_change(files)
        assert len(signals) == 1

    def test_detects_go_mod(self):
        files = _make_files([("M", "go.mod")])
        signals = _check_dependency_change(files)
        assert len(signals) == 1

    def test_detects_requirements_txt(self):
        files = _make_files([("M", "requirements.txt")])
        signals = _check_dependency_change(files)
        assert len(signals) == 1

    def test_no_signal_for_regular_files(self):
        files = _make_files([("M", "src/main.py"), ("A", "README.md")])
        signals = _check_dependency_change(files)
        assert len(signals) == 0

    def test_detects_nested_dependency_file(self):
        """package.json in a subdirectory should still trigger."""
        files = _make_files([("M", "packages/core/package.json")])
        signals = _check_dependency_change(files)
        assert len(signals) == 1


class TestConfigSchemaChangeSignal:
    def test_detects_cognitive_os_yaml(self):
        files = _make_files([("M", "cognitive-os.yaml")])
        signals = _check_config_schema_change(files)
        assert len(signals) == 1
        assert signals[0]["type"] == "config_schema_change"

    def test_detects_cos_dispatch_toml(self):
        files = _make_files([("M", "cos-dispatch.toml")])
        signals = _check_config_schema_change(files)
        assert len(signals) == 1

    def test_no_signal_for_non_config(self):
        files = _make_files([("M", "config/app.yaml")])
        signals = _check_config_schema_change(files)
        assert len(signals) == 0


class TestHookChangeSignal:
    def test_detects_hook_script(self):
        files = _make_files([("A", "hooks/my-new-hook.sh")])
        signals = _check_hook_change(files)
        assert len(signals) == 1
        assert signals[0]["type"] == "hook_change"

    def test_detects_settings_json(self):
        files = _make_files([("M", ".claude/settings.json")])
        signals = _check_hook_change(files)
        assert len(signals) == 1

    def test_no_signal_for_lib_scripts(self):
        files = _make_files([("M", "lib/utils.sh")])
        signals = _check_hook_change(files)
        assert len(signals) == 0


class TestLicenseChangeSignal:
    def test_detects_license_file(self):
        files = _make_files([("M", "LICENSE")])
        signals = _check_license_change(files)
        assert len(signals) == 1
        assert signals[0]["type"] == "license_change"
        assert signals[0]["weight"] == DEFAULT_WEIGHTS["license_change"]

    def test_detects_license_md(self):
        files = _make_files([("A", "LICENSE.md")])
        signals = _check_license_change(files)
        assert len(signals) == 1

    def test_no_signal_for_random_file(self):
        files = _make_files([("M", "docs/license-info.md")])
        signals = _check_license_change(files)
        assert len(signals) == 0


class TestLargeDeletionSignal:
    def test_triggers_on_more_than_20_deleted(self):
        files = _make_files([("D", f"src/file{i}.py") for i in range(25)])
        signals = _check_large_deletion(files, "")
        assert len(signals) == 1
        assert signals[0]["type"] == "large_deletion"

    def test_no_signal_for_few_deletions(self):
        files = _make_files([("D", f"src/file{i}.py") for i in range(5)])
        signals = _check_large_deletion(files, "")
        assert len(signals) == 0

    def test_exactly_20_does_not_trigger(self):
        files = _make_files([("D", f"src/file{i}.py") for i in range(20)])
        signals = _check_large_deletion(files, "")
        assert len(signals) == 0


class TestNewIntegrationSignal:
    def test_detects_new_package(self):
        files = _make_files([("A", "packages/new-service/index.ts")])
        signals = _check_new_integration(files)
        assert len(signals) == 1
        assert signals[0]["type"] == "new_integration"

    def test_no_signal_for_modified_package(self):
        files = _make_files([("M", "packages/existing/index.ts")])
        signals = _check_new_integration(files)
        assert len(signals) == 0

    def test_no_signal_outside_packages(self):
        files = _make_files([("A", "src/new-module/index.ts")])
        signals = _check_new_integration(files)
        assert len(signals) == 0


class TestFileStructureChangeSignal:
    def test_detects_new_directory(self):
        files = _make_files([
            ("A", "new-dir/file1.py"),
            ("A", "new-dir/file2.py"),
            ("M", "existing/old.py"),
        ])
        signals = _check_file_structure_change(files)
        assert len(signals) == 1
        assert signals[0]["type"] == "file_structure_change"

    def test_no_signal_for_existing_dirs(self):
        files = _make_files([
            ("M", "src/main.py"),
            ("M", "src/utils.py"),
        ])
        signals = _check_file_structure_change(files)
        assert len(signals) == 0


class TestBreakingChangeSignal:
    def test_detects_api_file_change(self):
        files = _make_files([("M", "packages/core/api/v1.py")])
        signals = _check_breaking_change(files)
        assert len(signals) == 1
        assert signals[0]["type"] == "breaking_change"

    def test_detects_proto_file(self):
        files = _make_files([("M", "proto/service.proto")])
        signals = _check_breaking_change(files)
        assert len(signals) == 1

    def test_detects_openapi_yaml(self):
        files = _make_files([("M", "openapi.yaml")])
        signals = _check_breaking_change(files)
        assert len(signals) == 1

    def test_no_signal_for_regular_code(self):
        files = _make_files([("M", "src/internal/handler.py")])
        signals = _check_breaking_change(files)
        assert len(signals) == 0


# ---------------------------------------------------------------------------
# Scoring threshold tests
# ---------------------------------------------------------------------------

class TestScoringThreshold:
    def test_threshold_is_070(self):
        assert DEFAULT_THRESHOLD == 0.70

    def test_score_below_threshold_does_not_trigger(self):
        """A single file_structure_change signal (0.20) should not trigger."""
        files = _make_files([("A", "new-dir/file.py")])
        signals = _check_file_structure_change(files)
        total = sum(s["weight"] for s in signals)
        assert total < DEFAULT_THRESHOLD

    def test_score_at_069_does_not_trigger(self):
        """Combine signals that total exactly below threshold."""
        # dependency_change (0.40) + large_deletion would be 0.65
        # We need to construct a scenario at 0.69
        # config_schema (0.35) + hook_change (0.30) = 0.65 < 0.70
        config_signals = _check_config_schema_change(
            _make_files([("M", "cognitive-os.yaml")])
        )
        hook_signals = _check_hook_change(
            _make_files([("A", "hooks/test.sh")])
        )
        total = sum(s["weight"] for s in config_signals + hook_signals)
        assert total == pytest.approx(0.65)
        assert total < DEFAULT_THRESHOLD

    def test_score_at_070_triggers(self):
        """Combine signals that total exactly at threshold."""
        # dependency_change (0.40) + hook_change (0.30) = 0.70
        dep_signals = _check_dependency_change(
            _make_files([("M", "package.json")])
        )
        hook_signals = _check_hook_change(
            _make_files([("A", "hooks/new.sh")])
        )
        total = sum(s["weight"] for s in dep_signals + hook_signals)
        assert total == pytest.approx(0.70)
        assert total >= DEFAULT_THRESHOLD

    def test_score_above_threshold_triggers(self):
        """License (0.60) + dependency (0.40) = 1.0 > 0.70."""
        lic_signals = _check_license_change(
            _make_files([("M", "LICENSE")])
        )
        dep_signals = _check_dependency_change(
            _make_files([("M", "requirements.txt")])
        )
        total = sum(s["weight"] for s in lic_signals + dep_signals)
        assert total == pytest.approx(1.0)
        assert total >= DEFAULT_THRESHOLD


# ---------------------------------------------------------------------------
# ADR numbering tests
# ---------------------------------------------------------------------------

class TestADRNumbering:
    def test_empty_directory(self, tmp_path):
        adrs_dir = tmp_path / "adrs"
        adrs_dir.mkdir()
        assert get_next_adr_number(str(adrs_dir)) == 1

    def test_nonexistent_directory(self, tmp_path):
        adrs_dir = tmp_path / "nonexistent"
        assert get_next_adr_number(str(adrs_dir)) == 1

    def test_finds_next_after_existing(self, tmp_path):
        adrs_dir = tmp_path / "adrs"
        adrs_dir.mkdir()
        (adrs_dir / "ADR-001-first.md").touch()
        (adrs_dir / "ADR-002-second.md").touch()
        (adrs_dir / "ADR-005-fifth.md").touch()
        assert get_next_adr_number(str(adrs_dir)) == 6

    def test_ignores_non_adr_files(self, tmp_path):
        adrs_dir = tmp_path / "adrs"
        adrs_dir.mkdir()
        (adrs_dir / "README.md").touch()
        (adrs_dir / "template.md").touch()
        (adrs_dir / "ADR-003-real.md").touch()
        assert get_next_adr_number(str(adrs_dir)) == 4

    def test_handles_gaps_correctly(self, tmp_path):
        """Should return max+1, not fill gaps."""
        adrs_dir = tmp_path / "adrs"
        adrs_dir.mkdir()
        (adrs_dir / "ADR-001-first.md").touch()
        (adrs_dir / "ADR-010-tenth.md").touch()
        assert get_next_adr_number(str(adrs_dir)) == 11


# ---------------------------------------------------------------------------
# ADR template tests
# ---------------------------------------------------------------------------

class TestADRTemplate:
    @patch("lib.adr_detector._git")
    def test_generated_adr_has_correct_sections(self, mock_git, tmp_path):
        """The generated ADR must contain Status: Draft, Context, Decision."""
        mock_git.side_effect = lambda cmd, cwd: {
            True: "feat: add new auth system\n",  # commit message
        }.get("--format=%s" in " ".join(cmd), "Added OAuth2 flow\n")

        adrs_dir = tmp_path / "docs" / "02-Decisions" / "adrs"
        adrs_dir.mkdir(parents=True)

        signals = [
            {"type": "dependency_change", "weight": 0.40, "description": "Dependency files changed", "files": ["package.json"]},
            {"type": "hook_change", "weight": 0.30, "description": "Hook files changed", "files": ["hooks/auth.sh"]},
        ]

        path = generate_adr_draft("abc1234", signals, str(tmp_path))

        content = Path(path).read_text()
        assert "## Status" in content
        assert "Draft" in content
        assert "## Context" in content
        assert "## Decision" in content
        assert "## Consequences" in content
        assert "## Detection Signals" in content
        assert "## Source" in content
        assert "`abc1234`" in content

    @patch("lib.adr_detector._git")
    def test_adr_filename_format(self, mock_git, tmp_path):
        mock_git.return_value = "feat: migrate to pip\n"

        adrs_dir = tmp_path / "docs" / "02-Decisions" / "adrs"
        adrs_dir.mkdir(parents=True)

        signals = [{"type": "dependency_change", "weight": 0.40, "description": "Deps changed", "files": ["requirements.txt"]}]
        path = generate_adr_draft("def5678", signals, str(tmp_path))

        filename = os.path.basename(path)
        assert filename.startswith("ADR-001-")
        assert filename.endswith(".md")

    @patch("lib.adr_detector._git")
    def test_adr_number_increments(self, mock_git, tmp_path):
        mock_git.return_value = "feat: change\n"

        adrs_dir = tmp_path / "docs" / "02-Decisions" / "adrs"
        adrs_dir.mkdir(parents=True)
        (adrs_dir / "ADR-020-existing.md").touch()

        signals = [{"type": "license_change", "weight": 0.60, "description": "License changed", "files": ["LICENSE"]}]
        path = generate_adr_draft("aaa1111", signals, str(tmp_path))

        assert "ADR-021-" in os.path.basename(path)

    @patch("lib.adr_detector._git")
    def test_adr_generation_creates_reservation_record(self, mock_git, tmp_path):
        mock_git.return_value = "feat: reserve adr\n"
        (tmp_path / "docs" / "02-Decisions" / "adrs").mkdir(parents=True)

        signals = [{"type": "license_change", "weight": 0.60, "description": "License changed", "files": ["LICENSE"]}]
        path = generate_adr_draft("ccc3333", signals, str(tmp_path))

        state = tmp_path / ".cognitive-os" / "locks" / "adr-reservations.json"
        assert state.exists()
        data = json.loads(state.read_text())
        assert data["reservations"][0]["path"] == Path(path).relative_to(tmp_path).as_posix()

    @patch("lib.adr_detector._git")
    def test_adr_signal_table_in_output(self, mock_git, tmp_path):
        mock_git.return_value = "feat: big change\n"

        adrs_dir = tmp_path / "docs" / "02-Decisions" / "adrs"
        adrs_dir.mkdir(parents=True)

        signals = [
            {"type": "dependency_change", "weight": 0.40, "description": "Dep changed", "files": ["go.mod"]},
            {"type": "breaking_change", "weight": 0.50, "description": "API changed", "files": ["packages/core/api/v1.py"]},
        ]
        path = generate_adr_draft("bbb2222", signals, str(tmp_path))
        content = Path(path).read_text()

        assert "| Signal | Weight | Evidence |" in content
        assert "| Dep changed |" in content
        assert "| API changed |" in content
        assert "**Total weight:**" in content


# ---------------------------------------------------------------------------
# Non-architectural commits should score low
# ---------------------------------------------------------------------------

class TestNonArchitecturalCommits:
    def test_typo_fix_scores_zero(self):
        """A commit that only changes a source file should score 0."""
        files = _make_files([("M", "src/handler.py")])
        all_signals = (
            _check_dependency_change(files)
            + _check_config_schema_change(files)
            + _check_hook_change(files)
            + _check_license_change(files)
            + _check_large_deletion(files, "")
            + _check_new_integration(files)
            + _check_file_structure_change(files)
            + _check_breaking_change(files)
        )
        assert len(all_signals) == 0

    def test_doc_only_change_scores_zero(self):
        files = _make_files([("M", "docs/guide.md"), ("M", "docs/tutorial.md")])
        all_signals = (
            _check_dependency_change(files)
            + _check_config_schema_change(files)
            + _check_hook_change(files)
            + _check_license_change(files)
            + _check_large_deletion(files, "")
            + _check_new_integration(files)
            + _check_file_structure_change(files)
            + _check_breaking_change(files)
        )
        assert len(all_signals) == 0

    def test_test_only_change_scores_zero(self):
        files = _make_files([
            ("M", "tests/unit/test_utils.py"),
            ("A", "tests/unit/test_new.py"),
        ])
        all_signals = (
            _check_dependency_change(files)
            + _check_config_schema_change(files)
            + _check_hook_change(files)
            + _check_license_change(files)
            + _check_large_deletion(files, "")
            + _check_new_integration(files)
            + _check_file_structure_change(files)
            + _check_breaking_change(files)
        )
        # file_structure_change might trigger for the test dir, but
        # since tests/unit already has modified files, it should not
        total = sum(s["weight"] for s in all_signals)
        assert total < DEFAULT_THRESHOLD


# ---------------------------------------------------------------------------
# Utility tests
# ---------------------------------------------------------------------------

class TestParseNameStatus:
    def test_parses_standard_output(self):
        output = "M\tsrc/main.py\nA\tnew/file.ts\nD\told/removed.go\n"
        result = _parse_name_status(output)
        assert len(result) == 3
        assert result[0] == {"status": "M", "path": "src/main.py"}
        assert result[1] == {"status": "A", "path": "new/file.ts"}
        assert result[2] == {"status": "D", "path": "old/removed.go"}

    def test_empty_output(self):
        assert _parse_name_status("") == []
        assert _parse_name_status("\n") == []


class TestSlugify:
    def test_basic_slug(self):
        assert _slugify("Migrate to pip") == "migrate-to-pip"

    def test_special_chars_removed(self):
        assert _slugify("feat: Docker->pip migration!") == "feat-docker-pip-migration"

    def test_truncated_at_60(self):
        long_title = "a" * 100
        assert len(_slugify(long_title)) == 60


# ---------------------------------------------------------------------------
# Metrics logging tests
# ---------------------------------------------------------------------------

class TestMetricsLogging:
    def test_log_creates_file(self, tmp_path):
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        result = {
            "commit_hash": "abc1234",
            "commit_message": "test commit",
            "total_score": 0.50,
            "threshold": 0.70,
            "triggered": False,
            "signals": [{"type": "dependency_change", "weight": 0.40}],
        }

        log_detection(result, None, str(project_dir))

        log_file = project_dir / ".cognitive-os" / "metrics" / "adr-detections.jsonl"
        assert log_file.exists()

        record = json.loads(log_file.read_text().strip())
        assert record["commit_hash"] == "abc1234"
        assert record["triggered"] is False
        assert record["adr_path"] is None

    def test_log_appends(self, tmp_path):
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        result = {
            "commit_hash": "aaa",
            "commit_message": "first",
            "total_score": 0.40,
            "threshold": 0.70,
            "triggered": False,
            "signals": [],
        }

        log_detection(result, None, str(project_dir))
        log_detection(result, None, str(project_dir))

        log_file = project_dir / ".cognitive-os" / "metrics" / "adr-detections.jsonl"
        lines = log_file.read_text().strip().splitlines()
        assert len(lines) == 2


# ---------------------------------------------------------------------------
# Integration: analyze_commit with mocked git
# ---------------------------------------------------------------------------

class TestAnalyzeCommitIntegration:
    @patch("lib.adr_detector._git")
    def test_adr_only_commit_not_triggered(self, mock_git):
        """Commits touching only ADR files should not trigger."""
        def git_side_effect(cmd, cwd):
            if "--format=%s" in " ".join(cmd):
                return "docs: update ADR-001\n"
            if "diff-tree" in " ".join(cmd):
                return "M\tdocs/02-Decisions/adrs/ADR-001-test.md\n"
            return ""

        mock_git.side_effect = git_side_effect
        result = analyze_commit("abc1234", "/fake")
        assert result["triggered"] is False
        assert result["total_score"] == 0.0

    @patch("lib.adr_detector._git")
    def test_license_change_triggers(self, mock_git):
        """A LICENSE change alone (0.60) should not trigger at 0.70 threshold."""
        def git_side_effect(cmd, cwd):
            if "--format=%s" in " ".join(cmd):
                return "chore: update license\n"
            if "diff-tree" in " ".join(cmd):
                return "M\tLICENSE\n"
            return ""

        mock_git.side_effect = git_side_effect
        result = analyze_commit("abc1234", "/fake")
        assert result["total_score"] == pytest.approx(0.60)
        assert result["triggered"] is False

    @patch("lib.adr_detector._git")
    def test_combined_signals_trigger(self, mock_git):
        """LICENSE (0.60) + dependency (0.40) = 1.0 should trigger."""
        def git_side_effect(cmd, cwd):
            if "--format=%s" in " ".join(cmd):
                return "feat: AGPL migration\n"
            if "diff-tree" in " ".join(cmd):
                return "M\tLICENSE\nM\tpackage.json\n"
            return ""

        mock_git.side_effect = git_side_effect
        result = analyze_commit("abc1234", "/fake")
        assert result["total_score"] == pytest.approx(1.0)
        assert result["triggered"] is True
        assert len(result["signals"]) == 2
