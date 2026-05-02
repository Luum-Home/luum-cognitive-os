"""Behavior tests for Safety Mesh features 4-7.

Tests:
- Feature 4: Dry-Run Preview (dry-run-preview.sh hook)
- Feature 5: Auto-Rollback (auto-rollback-trigger.sh hook)
- Feature 6: Change Impact Analysis (lib/impact_analysis.py)
- Feature 7: Confidence Gate (confidence-gate.sh hook)
"""

import json
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

# ---------------------------------------------------------------------------
# Setup for lib imports
# ---------------------------------------------------------------------------

_LIB_DIR = str(Path(__file__).resolve().parent.parent.parent / "lib")
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from impact_analysis import (
    ImpactReport,
    RiskLevel,
    analyze_impact,
    classify_risk,
    find_affected_tests,
    find_config_dependencies,
    find_direct_importers,
    find_docker_services,
    find_sdd_artifacts,
    format_impact_report,
)


# ===========================================================================
# Feature 4: Dry-Run Preview
# ===========================================================================


class TestDryRunPreview:
    """Tests for hooks/dry-run-preview.sh."""

    def test_blocks_when_dry_run_true(self, run_hook, cognitive_os_env):
        """DRY_RUN=true should block Agent tool calls with exit 2."""
        env = {**cognitive_os_env["env"], "DRY_RUN": "true"}
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {
                "prompt": "Implement the user authentication module",
            },
        })
        result = run_hook("dry-run-preview.sh", env=env, stdin=input_json)
        assert result.returncode == 2
        assert "DRY-RUN" in result.stdout
        assert "Would execute" in result.stdout
        assert "authentication" in result.stdout

    def test_passes_when_dry_run_false(self, run_hook, cognitive_os_env):
        """DRY_RUN=false should not block."""
        env = {**cognitive_os_env["env"], "DRY_RUN": "false"}
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {
                "prompt": "Do something",
            },
        })
        result = run_hook("dry-run-preview.sh", env=env, stdin=input_json)
        assert result.returncode == 0

    def test_passes_when_dry_run_unset(self, run_hook, cognitive_os_env):
        """When DRY_RUN is not set, should not block."""
        env = {k: v for k, v in cognitive_os_env["env"].items()}
        # Ensure DRY_RUN is not set
        env.pop("DRY_RUN", None)
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {"prompt": "Do something"},
        })
        result = run_hook("dry-run-preview.sh", env=env, stdin=input_json)
        assert result.returncode == 0

    def test_ignores_non_agent_tools(self, run_hook, cognitive_os_env):
        """DRY_RUN should not affect non-Agent tools like Bash."""
        env = {**cognitive_os_env["env"], "DRY_RUN": "true"}
        input_json = json.dumps({
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
        })
        result = run_hook("dry-run-preview.sh", env=env, stdin=input_json)
        assert result.returncode == 0

    def test_blocks_delegate_tool(self, run_hook, cognitive_os_env):
        """DRY_RUN should also block delegate tool calls."""
        env = {**cognitive_os_env["env"], "DRY_RUN": "true"}
        input_json = json.dumps({
            "tool_name": "delegate",
            "tool_input": {
                "prompt": "Run tests on the payment service",
            },
        })
        result = run_hook("dry-run-preview.sh", env=env, stdin=input_json)
        assert result.returncode == 2
        assert "DRY-RUN" in result.stdout

    def test_logs_to_metrics(self, run_hook, cognitive_os_env):
        """DRY_RUN interceptions should be logged to dry-run.jsonl."""
        env = {**cognitive_os_env["env"], "DRY_RUN": "true"}
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_input": {"prompt": "Build the feature"},
        })
        run_hook("dry-run-preview.sh", env=env, stdin=input_json)

        # Log goes to session-scoped metrics dir
        session_metrics = (
            Path(cognitive_os_env["cos_dir"])
            / "sessions"
            / cognitive_os_env["session_id"]
            / "metrics"
        )
        global_metrics = Path(cognitive_os_env["cos_dir"]) / "metrics"
        log_file = session_metrics / "dry-run.jsonl"
        if not log_file.exists():
            log_file = global_metrics / "dry-run.jsonl"
        assert log_file.exists()
        entries = [json.loads(line) for line in log_file.read_text().strip().split("\n")]
        assert len(entries) >= 1
        assert entries[0]["action"] == "blocked"
        assert entries[0]["tool"] == "Agent"


# ===========================================================================
# Feature 5: Auto-Rollback Trigger
# ===========================================================================


class TestAutoRollbackTrigger:
    """Tests for hooks/auto-rollback-trigger.sh."""

    def test_detects_verify_apply_exhaustion(self, run_hook, cognitive_os_env):
        """Should detect 'Verify-apply loop exceeded 3 retries' pattern."""
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_result": (
                "Verify-apply loop exceeded 3 retries. "
                "CRITICAL issues remain: REQ-01 scenario untested. "
                "Change: auth-refactor. Human intervention required."
            ),
        })
        result = run_hook(
            "auto-rollback-trigger.sh",
            env=cognitive_os_env["env"],
            stdin=input_json,
        )
        assert result.returncode == 0
        assert "ROLLBACK PLAN REQUIRED" in result.stdout
        assert "Human approval is required" in result.stdout

    def test_detects_max_retries_reached(self, run_hook, cognitive_os_env):
        """Should detect 'max retries reached/exceeded' in verify context."""
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_result": (
                "The max retries have been exceeded during verify. "
                "Change: payment-flow"
            ),
        })
        result = run_hook(
            "auto-rollback-trigger.sh",
            env=cognitive_os_env["env"],
            stdin=input_json,
        )
        assert result.returncode == 0
        assert "ROLLBACK PLAN REQUIRED" in result.stdout
        assert "Human approval is required" in result.stdout

    def test_detects_retry_count_with_fail(self, run_hook, cognitive_os_env):
        """Should detect retry_count: 3 combined with verdict: FAIL."""
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_result": (
                "DAG state:\n"
                "  retry_count: 3\n"
                "  verdict: FAIL\n"
                "  change: db-migration"
            ),
        })
        result = run_hook(
            "auto-rollback-trigger.sh",
            env=cognitive_os_env["env"],
            stdin=input_json,
        )
        assert result.returncode == 0
        assert "ROLLBACK PLAN REQUIRED" in result.stdout
        assert "Human approval is required" in result.stdout

    def test_ignores_normal_agent_output(self, run_hook, cognitive_os_env):
        """Should not trigger on normal agent completion."""
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_result": "Task completed successfully. All tests pass.",
        })
        result = run_hook(
            "auto-rollback-trigger.sh",
            env=cognitive_os_env["env"],
            stdin=input_json,
        )
        assert result.returncode == 0
        assert "AUTO-ROLLBACK" not in result.stdout

    def test_ignores_non_agent_tools(self, run_hook, cognitive_os_env):
        """Should not trigger on non-Agent tools."""
        input_json = json.dumps({
            "tool_name": "Bash",
            "tool_result": "Verify-apply loop exceeded 3 retries",
        })
        result = run_hook(
            "auto-rollback-trigger.sh",
            env=cognitive_os_env["env"],
            stdin=input_json,
        )
        assert result.returncode == 0
        assert "AUTO-ROLLBACK" not in result.stdout

    def test_production_phase_requires_plan(self, run_hook, cognitive_os_env):
        """In production phase, should require a rollback plan and human approval."""
        # Create cognitive-os.yaml with production phase
        project_dir = cognitive_os_env["project_dir"]
        config_file = project_dir / "cognitive-os.yaml"
        config_file.write_text("project:\n  phase: production\n")

        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_result": "Verify-apply loop exceeded 3 retries. Change: my-feature",
        })
        result = run_hook(
            "auto-rollback-trigger.sh",
            env=cognitive_os_env["env"],
            stdin=input_json,
        )
        assert result.returncode == 0
        assert "ROLLBACK PLAN REQUIRED" in result.stdout
        assert "human approval" in result.stdout.lower()

    @pytest.mark.parametrize("phase", ["reconstruction", "stabilization", "production", "maintenance"])
    def test_all_phases_require_human_approval(self, run_hook, cognitive_os_env, phase):
        """Every phase should request a rollback plan, never automatic execution."""
        project_dir = cognitive_os_env["project_dir"]
        config_file = project_dir / "cognitive-os.yaml"
        config_file.write_text(f"project:\n  phase: {phase}\n")
        input_json = json.dumps({"tool_name": "Agent", "tool_result": "Verify-apply loop exceeded 3 retries. Change: my-feature"})
        result = run_hook("auto-rollback-trigger.sh", env=cognitive_os_env["env"], stdin=input_json)
        assert result.returncode == 0
        assert "ROLLBACK PLAN REQUIRED" in result.stdout
        assert "Human approval is required" in result.stdout
        assert "No git revert" in result.stdout
        assert "execute automatically" not in result.stdout.lower()

    def test_logs_to_metrics(self, run_hook, cognitive_os_env):
        """Should log the trigger event to auto-rollback.jsonl."""
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_result": "Verify-apply loop exceeded 3 retries. Change: test-change",
        })
        run_hook(
            "auto-rollback-trigger.sh",
            env=cognitive_os_env["env"],
            stdin=input_json,
        )

        session_metrics = (
            Path(cognitive_os_env["cos_dir"])
            / "sessions"
            / cognitive_os_env["session_id"]
            / "metrics"
        )
        global_metrics = Path(cognitive_os_env["cos_dir"]) / "metrics"
        log_file = session_metrics / "auto-rollback.jsonl"
        if not log_file.exists():
            log_file = global_metrics / "auto-rollback.jsonl"
        assert log_file.exists()
        entries = [json.loads(line) for line in log_file.read_text().strip().split("\n")]
        assert len(entries) >= 1
        assert entries[0]["trigger"] == "verify-apply-exhaustion"
        assert entries[0]["mode"] == "plan_required"
        assert entries[0]["approval_required"] is True
        assert entries[0]["destructive_commands_executed"] is False


# ===========================================================================
# Feature 6: Change Impact Analysis
# ===========================================================================


class TestImpactAnalysisImports:
    """Tests for import detection in lib/impact_analysis.py."""

    def test_go_imports(self, tmp_path):
        """Should detect Go import relationships."""
        # Create a Go source file
        src_dir = tmp_path / "internal" / "auth"
        src_dir.mkdir(parents=True)
        (src_dir / "handler.go").write_text(
            'package auth\n\nimport "myapp/internal/auth/service"\n'
        )
        (src_dir / "service.go").write_text("package auth\n\nfunc Authenticate() {}\n")

        result = find_direct_importers(
            [str(src_dir / "service.go")], str(tmp_path)
        )
        # handler.go imports service
        assert any("handler.go" in imp for imps in result.values() for imp in imps)

    def test_typescript_imports(self, tmp_path):
        """Should detect TypeScript import relationships."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "utils.ts").write_text("export function helper() {}\n")
        (src_dir / "main.ts").write_text(
            'import { helper } from "./utils";\n\nhelper();\n'
        )

        result = find_direct_importers([str(src_dir / "utils.ts")], str(tmp_path))
        assert any("main.ts" in imp for imps in result.values() for imp in imps)

    def test_python_imports(self, tmp_path):
        """Should detect Python import relationships."""
        pkg_dir = tmp_path / "mypackage"
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text("")
        (pkg_dir / "core.py").write_text("def process(): pass\n")
        (pkg_dir / "app.py").write_text("from core import process\n")

        result = find_direct_importers([str(pkg_dir / "core.py")], str(tmp_path))
        assert any("app.py" in imp for imps in result.values() for imp in imps)

    def test_no_importers(self, tmp_path):
        """Should return empty when no files import the changed file."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "isolated.ts").write_text("export const x = 1;\n")
        (src_dir / "other.ts").write_text("export const y = 2;\n")

        result = find_direct_importers([str(src_dir / "isolated.ts")], str(tmp_path))
        assert not result


class TestImpactAnalysisTests:
    """Tests for test coverage mapping."""

    def test_go_test_mapping(self, tmp_path):
        """Should find Go test files matching changed files."""
        pkg_dir = tmp_path / "internal" / "users"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "service.go").write_text("package users\n")
        (pkg_dir / "service_test.go").write_text("package users\n")

        result = find_affected_tests(
            [str(pkg_dir / "service.go")], str(tmp_path)
        )
        assert any("service_test.go" in t for tests in result.values() for t in tests)

    def test_typescript_test_mapping(self, tmp_path):
        """Should find TypeScript spec files matching changed files."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "auth.service.ts").write_text("export class AuthService {}\n")
        (src_dir / "auth.service.spec.ts").write_text("describe('AuthService', () => {})\n")

        result = find_affected_tests(
            [str(src_dir / "auth.service.ts")], str(tmp_path)
        )
        assert any("spec.ts" in t for tests in result.values() for t in tests)

    def test_no_tests_found(self, tmp_path):
        """Should return empty when no tests cover the changed file."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "untested.go").write_text("package main\n")

        result = find_affected_tests([str(src_dir / "untested.go")], str(tmp_path))
        assert not result


class TestImpactAnalysisServices:
    """Tests for Docker service mapping."""

    def test_docker_service_detection(self, tmp_path):
        """Should map changed files to Docker services via build context."""
        # Create docker-compose
        (tmp_path / "docker-compose.yml").write_text(
            "services:\n"
            "  api:\n"
            "    build:\n"
            "      context: ./backend\n"
            "  web:\n"
            "    build:\n"
            "      context: ./frontend\n"
        )
        # Create source files
        backend_dir = tmp_path / "backend"
        backend_dir.mkdir()
        (backend_dir / "main.go").write_text("package main\n")

        result = find_docker_services(
            [str(backend_dir / "main.go")], str(tmp_path)
        )
        assert any("api" in svc for svcs in result.values() for svc in svcs)

    def test_no_compose_file(self, tmp_path):
        """Should return empty when no docker-compose exists."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "main.go").write_text("package main\n")

        result = find_docker_services([str(src_dir / "main.go")], str(tmp_path))
        assert not result


class TestImpactAnalysisRisk:
    """Tests for risk classification."""

    def test_critical_risk_payment_path(self):
        """Payment paths should be classified as CRITICAL."""
        risk, reasons = classify_risk(
            ["/app/internal/payment/handler.go"],
            importers={},
            tests={},
            services={},
        )
        assert risk == RiskLevel.CRITICAL
        assert any("Critical path" in r for r in reasons)

    def test_high_risk_auth_path(self):
        """Auth paths should be classified as HIGH."""
        risk, reasons = classify_risk(
            ["/app/internal/auth/middleware.go"],
            importers={},
            tests={},
            services={},
        )
        assert risk == RiskLevel.HIGH
        assert any("High-risk path" in r for r in reasons)

    def test_high_risk_many_importers(self):
        """Many importers should increase risk to HIGH."""
        importers = {"/app/core.go": [f"file{i}.go" for i in range(12)]}
        risk, reasons = classify_risk(
            ["/app/core.go"],
            importers=importers,
            tests={"/app/core.go": ["core_test.go"]},
            services={},
        )
        assert risk == RiskLevel.HIGH
        assert any("blast radius" in r.lower() for r in reasons)

    def test_medium_risk_no_tests(self):
        """Files without test coverage should be at least MEDIUM risk."""
        risk, reasons = classify_risk(
            ["/app/utils.go"],
            importers={},
            tests={},
            services={},
        )
        assert risk >= RiskLevel.MEDIUM
        assert any("test coverage" in r.lower() for r in reasons)

    def test_low_risk_simple_change(self):
        """Simple change with tests should be LOW risk."""
        risk, reasons = classify_risk(
            ["/app/helper.go"],
            importers={"/app/helper.go": ["user.go"]},
            tests={"/app/helper.go": ["helper_test.go"]},
            services={},
        )
        assert risk == RiskLevel.LOW

    def test_multi_service_risk(self):
        """Changes affecting multiple services should increase risk."""
        risk, reasons = classify_risk(
            ["/app/shared.go"],
            importers={},
            tests={"/app/shared.go": ["shared_test.go"]},
            services={"/app/shared.go": ["api", "worker", "scheduler"]},
        )
        assert risk >= RiskLevel.HIGH
        assert any("service" in r.lower() for r in reasons)


class TestImpactAnalysisIntegration:
    """Integration tests for the full analyze_impact function."""

    def test_full_analysis(self, tmp_path):
        """Full analysis should return a complete ImpactReport."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "core.ts").write_text("export function process() {}\n")
        (src_dir / "handler.ts").write_text(
            'import { process } from "./core";\n'
        )
        (src_dir / "core.spec.ts").write_text(
            "describe('core', () => { it('works', () => {}) })\n"
        )

        report = analyze_impact(["src/core.ts"], str(tmp_path))

        assert isinstance(report, ImpactReport)
        assert report.changed_files == ["src/core.ts"]
        assert report.risk_level is not None

    def test_format_report(self):
        """format_impact_report should produce readable output."""
        report = ImpactReport(
            changed_files=["src/auth.go"],
            direct_importers={"src/auth.go": ["src/handler.go", "src/middleware.go"]},
            affected_tests={"src/auth.go": ["src/auth_test.go"]},
            config_dependencies={},
            docker_services={"src/auth.go": ["api"]},
            sdd_artifacts={},
            risk_level=RiskLevel.HIGH,
            risk_reasons=["High blast radius: 2 files import changed files"],
        )
        output = format_impact_report(report)
        assert "CHANGE IMPACT ANALYSIS REPORT" in output
        assert "HIGH" in output
        assert "auth.go" in output
        assert "handler.go" in output
        assert "api" in output

    def test_config_dependencies(self, tmp_path):
        """Should detect config files referencing changed files."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "database.go").write_text("package db\n")
        (tmp_path / "config.yaml").write_text(
            "database:\n  driver: database\n  module: database.go\n"
        )

        result = find_config_dependencies(
            [str(src_dir / "database.go")], str(tmp_path)
        )
        assert any("config.yaml" in c for configs in result.values() for c in configs)

    def test_sdd_artifact_detection(self, tmp_path):
        """Should find SDD artifacts referencing changed files."""
        # Create SDD artifact directory
        sdd_dir = tmp_path / "openspec" / "changes" / "auth-refactor"
        sdd_dir.mkdir(parents=True)
        (sdd_dir / "spec.md").write_text(
            "# Auth Refactor Spec\n\nAffects: src/auth/handler.go\n"
        )

        src_dir = tmp_path / "src" / "auth"
        src_dir.mkdir(parents=True)
        (src_dir / "handler.go").write_text("package auth\n")

        result = find_sdd_artifacts(
            [str(src_dir / "handler.go")], str(tmp_path)
        )
        assert any("spec.md" in a for artifacts in result.values() for a in artifacts)


# ===========================================================================
# Feature 7: Confidence Gate
# ===========================================================================


class TestConfidenceGate:
    """Tests for hooks/confidence-gate.sh."""

    def test_low_score_warns_in_reconstruction(self, run_hook, cognitive_os_env):
        """Score < 50 in reconstruction should warn but not block."""
        project_dir = cognitive_os_env["project_dir"]
        config_file = project_dir / "cognitive-os.yaml"
        config_file.write_text("project:\n  phase: reconstruction\n")

        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_result": (
                "TRUST REPORT:\n  Score: 40/100\n\n"
                "WHAT I'M UNSURE ABOUT:\n- Edge cases not tested"
            ),
        })
        result = run_hook(
            "confidence-gate.sh",
            env=cognitive_os_env["env"],
            stdin=input_json,
        )
        assert result.returncode == 0  # Warn only, no block
        assert "CONFIDENCE GATE" in result.stdout

    def test_low_score_blocks_in_production(self, run_hook, cognitive_os_env):
        """Score < 50 in production should block (exit 2)."""
        project_dir = cognitive_os_env["project_dir"]
        config_file = project_dir / "cognitive-os.yaml"
        config_file.write_text("project:\n  phase: production\n")

        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_result": (
                "TRUST REPORT:\n  Score: 40/100\n\n"
                "WHAT I'M UNSURE ABOUT:\n- Not confident about edge cases"
            ),
        })
        result = run_hook(
            "confidence-gate.sh",
            env=cognitive_os_env["env"],
            stdin=input_json,
        )
        assert result.returncode == 2  # BLOCK
        assert "BLOCKED" in result.stdout

    def test_very_low_score_critical_warning(self, run_hook, cognitive_os_env):
        """Score < 30 should trigger CRITICAL warning."""
        project_dir = cognitive_os_env["project_dir"]
        config_file = project_dir / "cognitive-os.yaml"
        config_file.write_text("project:\n  phase: reconstruction\n")

        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_result": (
                "TRUST REPORT:\n  Score: 20/100\n\n"
                "WHAT I'M UNSURE ABOUT:\n- Everything"
            ),
        })
        result = run_hook(
            "confidence-gate.sh",
            env=cognitive_os_env["env"],
            stdin=input_json,
        )
        assert result.returncode == 0  # Warn only in reconstruction
        assert "CRITICAL" in result.stdout

    def test_very_low_score_blocks_in_maintenance(self, run_hook, cognitive_os_env):
        """Score < 30 in maintenance should block."""
        project_dir = cognitive_os_env["project_dir"]
        config_file = project_dir / "cognitive-os.yaml"
        config_file.write_text("project:\n  phase: maintenance\n")

        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_result": (
                "TRUST REPORT:\n  Score: 15/100\n\n"
                "WHAT I'M UNSURE ABOUT:\n- Most things"
            ),
        })
        result = run_hook(
            "confidence-gate.sh",
            env=cognitive_os_env["env"],
            stdin=input_json,
        )
        assert result.returncode == 2  # BLOCK
        assert "CRITICAL" in result.stdout

    def test_normal_score_passes(self, run_hook, cognitive_os_env):
        """Score >= 50 should pass through without any gate message."""
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_result": (
                "TRUST REPORT:\n  Score: 75/100\n\n"
                "WHAT I'M UNSURE ABOUT:\n- Minor edge case"
            ),
        })
        result = run_hook(
            "confidence-gate.sh",
            env=cognitive_os_env["env"],
            stdin=input_json,
        )
        assert result.returncode == 0
        assert "CONFIDENCE GATE" not in result.stdout

    def test_ignores_non_agent_tools(self, run_hook, cognitive_os_env):
        """Should not process non-Agent tools."""
        input_json = json.dumps({
            "tool_name": "Bash",
            "tool_result": "Score: 10/100",
        })
        result = run_hook(
            "confidence-gate.sh",
            env=cognitive_os_env["env"],
            stdin=input_json,
        )
        assert result.returncode == 0
        assert "CONFIDENCE GATE" not in result.stdout

    def test_no_trust_report_passes(self, run_hook, cognitive_os_env):
        """When there is no Trust Report, confidence gate should not activate."""
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_result": "Task completed. All tests pass.",
        })
        result = run_hook(
            "confidence-gate.sh",
            env=cognitive_os_env["env"],
            stdin=input_json,
        )
        assert result.returncode == 0
        assert "CONFIDENCE GATE" not in result.stdout

    def test_logs_to_metrics(self, run_hook, cognitive_os_env):
        """Low-score gate activations should be logged."""
        project_dir = cognitive_os_env["project_dir"]
        config_file = project_dir / "cognitive-os.yaml"
        config_file.write_text("project:\n  phase: reconstruction\n")

        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_result": (
                "TRUST REPORT:\n  Score: 25/100\n\n"
                "WHAT I'M UNSURE ABOUT:\n- Everything"
            ),
        })
        run_hook(
            "confidence-gate.sh",
            env=cognitive_os_env["env"],
            stdin=input_json,
        )

        session_metrics = (
            Path(cognitive_os_env["cos_dir"])
            / "sessions"
            / cognitive_os_env["session_id"]
            / "metrics"
        )
        global_metrics = Path(cognitive_os_env["cos_dir"]) / "metrics"
        log_file = session_metrics / "confidence-gates.jsonl"
        if not log_file.exists():
            log_file = global_metrics / "confidence-gates.jsonl"
        assert log_file.exists()
        entries = [json.loads(line) for line in log_file.read_text().strip().split("\n")]
        assert len(entries) >= 1
        assert entries[0]["score"] == 25
        assert entries[0]["severity"] == "critical"

    def test_stabilization_warns_only(self, run_hook, cognitive_os_env):
        """Score < 50 in stabilization should warn but not block."""
        project_dir = cognitive_os_env["project_dir"]
        config_file = project_dir / "cognitive-os.yaml"
        config_file.write_text("project:\n  phase: stabilization\n")

        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_result": (
                "TRUST REPORT:\n  Score: 35/100\n\n"
                "WHAT I'M UNSURE ABOUT:\n- Uncertain"
            ),
        })
        result = run_hook(
            "confidence-gate.sh",
            env=cognitive_os_env["env"],
            stdin=input_json,
        )
        assert result.returncode == 0  # Warn only
        assert "CONFIDENCE GATE" in result.stdout
