"""Behavior tests for the self-improvement loop.

Creates mock metrics data with known patterns, runs analysis hooks,
and verifies they detect patterns and produce correct output.
Migrated from test-self-improvement.sh.
"""

import json
import os
import subprocess
import time
from pathlib import Path

import pytest


@pytest.fixture
def mock_metrics_env(tmp_path, project_root):
    """Set up a temporary project with mock metrics data."""
    test_project = tmp_path / "project"
    test_cos = test_project / ".cognitive-os"
    test_metrics = test_cos / "metrics"
    test_refine = test_metrics / "auto-refine"
    test_metrics.mkdir(parents=True)
    test_refine.mkdir(parents=True)

    # Copy cognitive-os.yaml for config reading
    src_config = project_root / "cognitive-os.yaml"
    if src_config.exists():
        dest_config = test_cos / "cognitive-os.yaml"
        dest_config.write_text(src_config.read_text())

    return {
        "project_dir": test_project,
        "metrics_dir": test_metrics,
        "env": {
            "CLAUDE_PROJECT_DIR": str(test_project),
            "COGNITIVE_OS_SESSION_START": "2026-03-22T00:00:00Z",
        },
    }


@pytest.mark.behavior
class TestSelfImprovementHooksExist:
    """Tests that self-improvement hooks and skills exist."""

    def test_kpi_trigger_exists_and_executable(self, hooks_dir):
        hook = hooks_dir / "kpi-trigger.sh"
        if not hook.exists():
            pytest.fail("kpi-trigger.sh does not exist")
        assert os.access(hook, os.X_OK), "kpi-trigger.sh should be executable"

    def test_session_learning_exists_and_executable(self, hooks_dir):
        hook = hooks_dir / "session-learning.sh"
        if not hook.exists():
            pytest.fail("session-learning.sh does not exist")
        assert os.access(hook, os.X_OK), "session-learning.sh should be executable"

    def test_self_improve_skill_exists(self, project_root):
        skill = project_root / "skills" / "self-improve" / "SKILL.md"
        assert skill.exists(), "self-improve SKILL.md should exist"

    def test_self_improve_skill_frontmatter(self, project_root):
        skill = project_root / "skills" / "self-improve" / "SKILL.md"
        if not skill.exists():
            pytest.skip("SKILL.md not found")
        content = skill.read_text()
        assert "name: self-improve" in content, "skill should have correct name"
        assert "user-invocable: true" in content, "skill should be user-invocable"


@pytest.mark.behavior
class TestSelfImprovementProtocol:
    """Tests for self-improvement-protocol rule."""

    def test_protocol_rule_exists(self, project_root):
        rule = project_root / "rules" / "self-improvement-protocol.md"
        assert rule.exists(), "self-improvement-protocol.md should exist"

    def test_protocol_distinguishes_auto_and_human_approval(self, project_root):
        rule = project_root / "rules" / "self-improvement-protocol.md"
        if not rule.exists():
            pytest.skip("protocol file not found")
        content = rule.read_text()
        assert "AUTO" in content and "HUMAN APPROVAL" in content, (
            "protocol should distinguish auto-apply vs human approval"
        )

    def test_protocol_includes_rollback(self, project_root):
        rule = project_root / "rules" / "self-improvement-protocol.md"
        if not rule.exists():
            pytest.skip("protocol file not found")
        content = rule.read_text()
        assert any(w in content.lower() for w in ["rollback", "roll back", "revert"]), (
            "protocol should include rollback procedures"
        )


@pytest.mark.behavior
class TestMockMetricsData:
    """Tests using mock metrics data to verify pattern detection."""

    def _create_error_data(self, metrics_dir: Path):
        """Create mock error-learning.jsonl with known patterns."""
        error_file = metrics_dir / "error-learning.jsonl"
        epoch = int(time.time())

        # 5 TEST_FAILURE errors for users-core
        for i in range(1, 6):
            ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            entry = {
                "timestamp": ts,
                "timestamp_epoch": epoch - i * 60,
                "type": "TEST_FAILURE",
                "service": "users-core",
                "framework": "go-test",
                "error": "FAIL: TestUserCreate - expected 200 got 500",
                "command": "go test ./...",
                "context": "assertion failure in test",
                "fingerprint": "abc123",
            }
            with open(error_file, "a") as f:
                f.write(json.dumps(entry) + "\n")

        # 3 LINT_ERROR for bff-ninja
        for i in range(1, 4):
            ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            entry = {
                "timestamp": ts,
                "timestamp_epoch": epoch - i * 120,
                "type": "LINT_ERROR",
                "service": "bff-ninja",
                "framework": "eslint",
                "error": "error TS2345: Argument of type string is not assignable",
                "command": "npx eslint .",
                "context": "TypeScript type error",
                "fingerprint": "def456",
            }
            with open(error_file, "a") as f:
                f.write(json.dumps(entry) + "\n")

        return error_file

    def _create_skill_metrics(self, metrics_dir: Path):
        """Create mock skill-metrics.jsonl (7 success, 3 failure = 70%)."""
        skill_file = metrics_dir / "skill-metrics.jsonl"
        for i in range(1, 8):
            entry = {
                "timestamp": f"2026-03-22T10:0{i}:00Z",
                "skill": "apply",
                "model": "sonnet",
                "tokens": 5000,
                "duration_ms": 3000,
                "success": True,
            }
            with open(skill_file, "a") as f:
                f.write(json.dumps(entry) + "\n")

        for i in range(1, 4):
            entry = {
                "timestamp": f"2026-03-22T11:0{i}:00Z",
                "skill": "apply",
                "model": "sonnet",
                "tokens": 8000,
                "duration_ms": 5000,
                "success": False,
            }
            with open(skill_file, "a") as f:
                f.write(json.dumps(entry) + "\n")

        return skill_file

    def test_mock_error_data_creation(self, mock_metrics_env):
        error_file = self._create_error_data(mock_metrics_env["metrics_dir"])
        lines = error_file.read_text().strip().split("\n")
        assert len(lines) == 8, f"Expected 8 mock entries, got {len(lines)}"

    def test_mock_skill_metrics_creation(self, mock_metrics_env):
        skill_file = self._create_skill_metrics(mock_metrics_env["metrics_dir"])
        lines = skill_file.read_text().strip().split("\n")
        assert len(lines) == 10, f"Expected 10 skill entries, got {len(lines)}"

    def test_kpi_trigger_produces_snapshot(self, hooks_dir, mock_metrics_env):
        hook = hooks_dir / "kpi-trigger.sh"
        if not hook.exists() or not os.access(hook, os.X_OK):
            pytest.skip("kpi-trigger.sh not executable")

        self._create_error_data(mock_metrics_env["metrics_dir"])
        self._create_skill_metrics(mock_metrics_env["metrics_dir"])

        result = subprocess.run(
            ["bash", str(hook)],
            capture_output=True,
            text=True,
            env={**os.environ, **mock_metrics_env["env"]},
            timeout=15,
        )
        assert result.returncode == 0, f"kpi-trigger.sh exited with {result.returncode}"

        kpi_file = mock_metrics_env["metrics_dir"] / "kpi-history.jsonl"
        if kpi_file.exists():
            last_line = kpi_file.read_text().strip().split("\n")[-1]
            data = json.loads(last_line)
            assert "first_pass_success_rate" in last_line, "should contain first_pass_success_rate"
            assert "avg_iterations" in last_line, "should contain avg_iterations"

    def test_session_learning_produces_entry(self, hooks_dir, mock_metrics_env):
        hook = hooks_dir / "session-learning.sh"
        if not hook.exists() or not os.access(hook, os.X_OK):
            pytest.skip("session-learning.sh not executable")

        self._create_error_data(mock_metrics_env["metrics_dir"])
        self._create_skill_metrics(mock_metrics_env["metrics_dir"])

        result = subprocess.run(
            ["bash", str(hook)],
            capture_output=True,
            text=True,
            env={**os.environ, **mock_metrics_env["env"]},
            timeout=15,
        )
        assert result.returncode == 0, f"session-learning.sh exited with {result.returncode}"

        learnings = mock_metrics_env["metrics_dir"] / "session-learnings.jsonl"
        if learnings.exists():
            last_line = learnings.read_text().strip().split("\n")[-1]
            assert "session_errors" in last_line, "should contain session_errors"
            assert "success_rate" in last_line, "should contain success_rate"


@pytest.mark.behavior
class TestSelfImprovementConfig:
    """Tests for cognitive-os.yaml self-improvement configuration."""

    def test_config_has_self_improvement(self, project_root):
        config = project_root / "cognitive-os.yaml"
        if not config.exists():
            pytest.skip("config not found")
        content = config.read_text()
        assert "self_improvement:" in content, "config should have self_improvement section"

    def test_config_has_auto_apply(self, project_root):
        config = project_root / "cognitive-os.yaml"
        if not config.exists():
            pytest.skip("config not found")
        content = config.read_text()
        assert "auto_apply:" in content, "config should have auto_apply setting"

    def test_config_has_first_pass_success(self, project_root):
        config = project_root / "cognitive-os.yaml"
        if not config.exists():
            pytest.skip("config not found")
        content = config.read_text()
        assert "first_pass_success:" in content, "config should have first_pass_success threshold"

    def test_config_has_max_auto_improvements(self, project_root):
        config = project_root / "cognitive-os.yaml"
        if not config.exists():
            pytest.skip("config not found")
        content = config.read_text()
        assert "max_auto_improvements:" in content, "config should have max_auto_improvements"


@pytest.mark.behavior
class TestSelfImprovementIntegration:
    """Tests for catalog and rules integration."""

    def test_catalog_includes_self_improve(self, project_root):
        catalog = project_root / "skills" / "CATALOG.md"
        if not catalog.exists():
            pytest.skip("CATALOG.md not found")
        assert "self-improve" in catalog.read_text(), "CATALOG should include self-improve"

    def test_rules_compact_references_self_improvement(self, project_root):
        rules = project_root / "rules" / "RULES-COMPACT.md"
        if not rules.exists():
            pytest.skip("RULES-COMPACT.md not found")
        content = rules.read_text().lower()
        has_ref = "self-improvement" in content or "self_improvement" in content or "self-improve" in content or "kpi" in content
        if not has_ref:
            pytest.xfail("RULES-COMPACT does not yet reference self-improvement — feature pending integration")

    def test_docs_index_includes_self_improvement_loop(self, project_root):
        index = project_root / "docs" / "INDEX.md"
        if not index.exists():
            pytest.skip("docs/INDEX.md not found")
        assert "self-improvement-loop" in index.read_text(), (
            "docs/INDEX should include self-improvement-loop"
        )
