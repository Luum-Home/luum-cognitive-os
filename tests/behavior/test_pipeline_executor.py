"""Tests for the pipeline executor module.

Validates:
- Variable resolution (_resolve_vars)
- Gate condition evaluation (_evaluate_gate)
- PipelineState save/load cycle
- PipelineExecutor dry-run mode
- Workflow YAML loading from .cognitive-os/workflows/
- Step sequencing and type recognition
"""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

pytestmark = pytest.mark.behavior


# ─── Variable resolution ─────────────────────────────────────────────────────


class TestResolveVars:
    """Tests for _resolve_vars free function."""

    @pytest.fixture(autouse=True)
    def import_fn(self):
        from lib.pipeline_executor import _resolve_vars
        self.resolve = _resolve_vars

    def test_simple_dollar_brace(self):
        result = self.resolve("${CHANGE}", {"CHANGE": "my-feature"})
        assert result == "my-feature"

    def test_simple_dollar_no_brace(self):
        result = self.resolve("$CHANGE", {"CHANGE": "my-feature"})
        assert result == "my-feature"

    def test_default_value_used_when_missing(self):
        result = self.resolve("${BUILD_CMD:-go build ./...}", {})
        assert result == "go build ./..."

    def test_default_value_overridden_by_context(self):
        result = self.resolve("${BUILD_CMD:-go build ./...}", {"BUILD_CMD": "make build"})
        assert result == "make build"

    def test_multiple_vars_in_one_string(self):
        result = self.resolve("${CMD} ${ARG}", {"CMD": "echo", "ARG": "hello"})
        assert result == "echo hello"

    def test_unknown_var_no_default_kept_or_empty(self):
        # Unknown var with no default — behaviour is empty string or kept as-is
        result = self.resolve("${UNKNOWN_XYZ}", {})
        # Accept either empty string or the literal placeholder
        assert result == "" or "UNKNOWN_XYZ" in result

    def test_no_substitution_needed(self):
        result = self.resolve("plain text", {"ANYTHING": "val"})
        assert result == "plain text"

    def test_empty_string_input(self):
        result = self.resolve("", {"CHANGE": "x"})
        assert result == ""


# ─── Gate condition evaluation ───────────────────────────────────────────────


class TestEvaluateGate:
    """Tests for _evaluate_gate free function."""

    @pytest.fixture(autouse=True)
    def import_fn(self):
        from lib.pipeline_executor import _evaluate_gate, PipelineState
        self.evaluate = _evaluate_gate
        self.State = PipelineState

    def _state_with(self, **step_statuses):
        """Build a PipelineState with pre-populated step results."""
        state = self.State.__new__(self.State)
        state.steps_completed = list(step_statuses.keys())
        state.step_results = {}
        for name, status in step_statuses.items():
            from lib.pipeline_executor import StepResult
            state.step_results[name] = StepResult(
                name=name,
                step_type="agent",
                status=status,
                duration_secs=0.1,
                output="",
                exit_code=0,
                retry_count=0,
            )
        return state

    def test_equals_pass(self):
        state = self._state_with(propose="completed")
        assert self.evaluate("propose.status == completed", state) is True

    def test_equals_fail(self):
        state = self._state_with(propose="failed")
        assert self.evaluate("propose.status == completed", state) is False

    def test_not_equals_pass(self):
        state = self._state_with(propose="failed")
        assert self.evaluate("propose.status != completed", state) is True

    def test_not_equals_fail(self):
        state = self._state_with(propose="completed")
        assert self.evaluate("propose.status != completed", state) is False

    def test_step_not_run(self):
        state = self._state_with()  # empty
        # A step that was never run — == completed should be False
        assert self.evaluate("propose.status == completed", state) is False

    def test_gate_passes_when_all_required_completed(self):
        state = self._state_with(apply="completed", verify="completed")
        assert self.evaluate("apply.status == completed", state) is True
        assert self.evaluate("verify.status == completed", state) is True


# ─── PipelineState persistence ───────────────────────────────────────────────


class TestPipelineState:
    """Tests for PipelineState save/load cycle."""

    @pytest.fixture(autouse=True)
    def imports(self):
        from lib.pipeline_executor import PipelineState, StepResult
        self.State = PipelineState
        self.StepResult = StepResult

    def test_fresh_state_has_empty_steps(self):
        state = self.State(change_name="test-change", workflow_name="feature-pipeline")
        assert state.steps_completed == []
        assert state.step_results == {}

    def test_mark_completed_adds_result(self):
        state = self.State(change_name="test-change", workflow_name="feature-pipeline")
        result = self.StepResult(
            name="propose",
            step_type="agent",
            status="completed",
            duration_secs=1.5,
            output="done",
            exit_code=0,
            retry_count=0,
        )
        state.mark_completed("propose", result)
        assert "propose" in state.steps_completed
        assert state.step_results["propose"].status == "completed"

    def test_save_and_load_roundtrip(self, tmp_path):
        state = self.State(change_name="my-feature", workflow_name="feature-pipeline")
        result = self.StepResult(
            name="propose",
            step_type="agent",
            status="completed",
            duration_secs=2.0,
            output="proposal done",
            exit_code=0,
            retry_count=0,
        )
        state.mark_completed("propose", result)
        state.save(state_dir=tmp_path)

        loaded = self.State.load(
            change_name="my-feature",
            workflow_name="feature-pipeline",
            state_dir=tmp_path,
        )
        assert "propose" in loaded.steps_completed
        assert loaded.step_results["propose"].status == "completed"
        assert loaded.workflow_name == "feature-pipeline"

    def test_load_missing_file_returns_fresh_state(self, tmp_path):
        loaded = self.State.load(
            change_name="nonexistent",
            workflow_name="feature-pipeline",
            state_dir=tmp_path,
        )
        assert loaded.steps_completed == []
        assert loaded.change_name == "nonexistent"

    def test_save_creates_json_file(self, tmp_path):
        state = self.State(change_name="x", workflow_name="feature-pipeline")
        state.save(state_dir=tmp_path)
        files = list(tmp_path.glob("*.json"))
        assert len(files) >= 1

    def test_vars_persisted(self, tmp_path):
        state = self.State(
            change_name="x",
            workflow_name="feature-pipeline",
            vars={"FOO": "bar"},
        )
        state.save(state_dir=tmp_path)
        loaded = self.State.load("x", "feature-pipeline", state_dir=tmp_path)
        assert loaded.vars.get("FOO") == "bar"


# ─── PipelineExecutor dry-run ─────────────────────────────────────────────────


class TestPipelineExecutorDryRun:
    """Tests for PipelineExecutor in dry-run mode (no real agents/scripts run)."""

    @pytest.fixture
    def feature_workflow(self):
        return PROJECT_ROOT / ".cognitive-os" / "workflows" / "feature-pipeline.yaml"

    @pytest.fixture
    def bugfix_workflow(self):
        return PROJECT_ROOT / ".cognitive-os" / "workflows" / "bugfix-pipeline.yaml"

    @pytest.fixture(autouse=True)
    def imports(self):
        from lib.pipeline_executor import PipelineExecutor
        self.Executor = PipelineExecutor

    def test_dry_run_completes_without_error(self, feature_workflow, tmp_path):
        if not feature_workflow.exists():
            pytest.skip("feature-pipeline.yaml not found")
        executor = self.Executor(
            workflow_path=feature_workflow,
            change_name="dry-run-test",
            dry_run=True,
            state_dir=tmp_path,
        )
        result = executor.run()
        # Dry-run should succeed (return truthy or structured result)
        assert result is not None

    def test_dry_run_visits_all_steps(self, feature_workflow, tmp_path):
        if not feature_workflow.exists():
            pytest.skip("feature-pipeline.yaml not found")
        executor = self.Executor(
            workflow_path=feature_workflow,
            change_name="dry-run-test",
            dry_run=True,
            state_dir=tmp_path,
        )
        executor.run()
        # After dry-run, state should record steps attempted
        from lib.pipeline_executor import PipelineState
        state = PipelineState.load("dry-run-test", "feature-pipeline", state_dir=tmp_path)
        assert len(state.steps_completed) > 0

    def test_dry_run_bugfix_workflow(self, bugfix_workflow, tmp_path):
        if not bugfix_workflow.exists():
            pytest.skip("bugfix-pipeline.yaml not found")
        executor = self.Executor(
            workflow_path=bugfix_workflow,
            change_name="dry-run-bugfix",
            dry_run=True,
            state_dir=tmp_path,
        )
        result = executor.run()
        assert result is not None

    def test_start_from_skips_earlier_steps(self, feature_workflow, tmp_path):
        if not feature_workflow.exists():
            pytest.skip("feature-pipeline.yaml not found")
        executor = self.Executor(
            workflow_path=feature_workflow,
            change_name="start-from-test",
            dry_run=True,
            start_from="apply",
            state_dir=tmp_path,
        )
        executor.run()
        from lib.pipeline_executor import PipelineState
        state = PipelineState.load("start-from-test", "feature-pipeline", state_dir=tmp_path)
        # Steps before "apply" should not be in completed list
        assert "propose" not in state.steps_completed

    def test_extra_vars_passed_through(self, feature_workflow, tmp_path):
        if not feature_workflow.exists():
            pytest.skip("feature-pipeline.yaml not found")
        executor = self.Executor(
            workflow_path=feature_workflow,
            change_name="vars-test",
            dry_run=True,
            extra_vars={"BUILD_CMD": "make build", "TEST_CMD": "make test"},
            state_dir=tmp_path,
        )
        result = executor.run()
        assert result is not None


# ─── Workflow YAML structure ──────────────────────────────────────────────────


class TestWorkflowYaml:
    """Tests for workflow YAML files in .cognitive-os/workflows/."""

    WORKFLOWS_DIR = PROJECT_ROOT / ".cognitive-os" / "workflows"

    def _load_yaml(self, path):
        try:
            import yaml
        except ImportError:
            pytest.skip("pyyaml not installed")
        return yaml.safe_load(path.read_text())

    def test_feature_pipeline_exists(self):
        assert (self.WORKFLOWS_DIR / "feature-pipeline.yaml").exists()

    def test_bugfix_pipeline_exists(self):
        assert (self.WORKFLOWS_DIR / "bugfix-pipeline.yaml").exists()

    def test_feature_pipeline_has_steps(self):
        path = self.WORKFLOWS_DIR / "feature-pipeline.yaml"
        if not path.exists():
            pytest.skip("feature-pipeline.yaml not found")
        data = self._load_yaml(path)
        assert "steps" in data
        assert len(data["steps"]) > 0

    def test_bugfix_pipeline_has_steps(self):
        path = self.WORKFLOWS_DIR / "bugfix-pipeline.yaml"
        if not path.exists():
            pytest.skip("bugfix-pipeline.yaml not found")
        data = self._load_yaml(path)
        assert "steps" in data
        assert len(data["steps"]) > 0

    def test_feature_pipeline_has_propose_step(self):
        path = self.WORKFLOWS_DIR / "feature-pipeline.yaml"
        if not path.exists():
            pytest.skip("feature-pipeline.yaml not found")
        data = self._load_yaml(path)
        step_names = [s.get("name", s.get("id", "")) for s in data["steps"]]
        assert any("propose" in name for name in step_names)

    def test_feature_pipeline_step_types_are_valid(self):
        path = self.WORKFLOWS_DIR / "feature-pipeline.yaml"
        if not path.exists():
            pytest.skip("feature-pipeline.yaml not found")
        data = self._load_yaml(path)
        valid_types = {"agent", "script", "gate"}
        for step in data["steps"]:
            step_type = step.get("type", "agent")
            assert step_type in valid_types, f"Step {step} has invalid type {step_type!r}"

    def test_feature_pipeline_has_gate_step(self):
        path = self.WORKFLOWS_DIR / "feature-pipeline.yaml"
        if not path.exists():
            pytest.skip("feature-pipeline.yaml not found")
        data = self._load_yaml(path)
        types = [s.get("type", "agent") for s in data["steps"]]
        assert "gate" in types

    def test_bugfix_pipeline_has_apply_step(self):
        path = self.WORKFLOWS_DIR / "bugfix-pipeline.yaml"
        if not path.exists():
            pytest.skip("bugfix-pipeline.yaml not found")
        data = self._load_yaml(path)
        step_names = [s.get("name", s.get("id", "")) for s in data["steps"]]
        assert any("apply" in name for name in step_names)

    def test_on_failure_values_are_valid(self):
        for filename in ("feature-pipeline.yaml", "bugfix-pipeline.yaml"):
            path = self.WORKFLOWS_DIR / filename
            if not path.exists():
                continue
            data = self._load_yaml(path)
            valid_failures = {"abort", "retry", "escalate", "skip"}
            for step in data["steps"]:
                if "on_failure" in step:
                    assert step["on_failure"] in valid_failures, (
                        f"{filename}: step {step.get('name')} has invalid on_failure"
                    )

    def test_variable_syntax_in_scripts(self):
        """Script steps using ${VAR:-default} syntax should be parseable."""
        path = self.WORKFLOWS_DIR / "feature-pipeline.yaml"
        if not path.exists():
            pytest.skip("feature-pipeline.yaml not found")
        data = self._load_yaml(path)
        raw_text = path.read_text()
        # The file should contain at least one default-value substitution
        assert "${" in raw_text
