"""Unit tests for lib/tool_adoption_evaluator.py.

All tests are offline — no network requests are made.  GitHub API calls are
either monkey-patched or tested via the fallback path (gh CLI absent).

Run with: pytest tests/unit/test_tool_adoption_evaluator.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from lib.tool_adoption_evaluator import (
    ToolAdoptionEvaluator,
    _classify_deployment,
    _classify_ui,
    _compute_overlap,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def evaluator(tmp_path: Path) -> ToolAdoptionEvaluator:
    """Evaluator pointing at a temp dir with a minimal lib/ skeleton."""
    lib_dir = tmp_path / "lib"
    lib_dir.mkdir()
    (lib_dir / "rate_limiter.py").write_text("# rate limiter")
    (lib_dir / "cost_dashboard.py").write_text("# cost dashboard")
    (lib_dir / "agent_bus.py").write_text("# agent bus")
    (lib_dir / "__init__.py").write_text("")
    return ToolAdoptionEvaluator(project_root=str(tmp_path))


# ---------------------------------------------------------------------------
# License checks
# ---------------------------------------------------------------------------


def test_check_license_mit(evaluator: ToolAdoptionEvaluator) -> None:
    """MIT license → APPROVED, can_copy_code=True."""
    with patch("lib.tool_adoption_evaluator._run_gh", return_value='{"licenseInfo":{"spdxId":"MIT","name":"MIT License"}}'):
        result = evaluator.check_license("https://github.com/owner/repo")
    assert result["license"] == "MIT"
    assert result["verdict"] == "APPROVED"
    assert result["can_copy_code"] is True
    assert result["can_copy_patterns"] is True


def test_check_license_agpl(evaluator: ToolAdoptionEvaluator) -> None:
    """AGPL-3.0 → BLOCKED, can_copy_code=False."""
    with patch("lib.tool_adoption_evaluator._run_gh", return_value='{"licenseInfo":{"spdxId":"AGPL-3.0","name":"GNU Affero General Public License v3.0"}}'):
        result = evaluator.check_license("https://github.com/owner/repo")
    assert result["license"] == "AGPL-3.0"
    assert result["verdict"] == "BLOCKED"
    assert result["can_copy_code"] is False
    assert result["can_copy_patterns"] is True


def test_check_license_apache(evaluator: ToolAdoptionEvaluator) -> None:
    """Apache-2.0 → APPROVED."""
    with patch("lib.tool_adoption_evaluator._run_gh", return_value='{"licenseInfo":{"spdxId":"Apache-2.0","name":"Apache License 2.0"}}'):
        result = evaluator.check_license("https://github.com/owner/repo")
    assert result["license"] == "Apache-2.0"
    assert result["verdict"] == "APPROVED"
    assert result["can_copy_code"] is True


def test_check_license_unknown_is_blocked(evaluator: ToolAdoptionEvaluator) -> None:
    """Unknown license (gh CLI unavailable) → BLOCKED."""
    with patch("lib.tool_adoption_evaluator._run_gh", return_value=None):
        result = evaluator.check_license("https://github.com/owner/repo")
    assert result["verdict"] == "BLOCKED"
    assert result["can_copy_code"] is False


# ---------------------------------------------------------------------------
# Deployment weight
# ---------------------------------------------------------------------------


def test_deployment_pip(evaluator: ToolAdoptionEvaluator) -> None:
    """Repo with pyproject.toml → pip-install, score 1.0."""
    files = ["pyproject.toml", "src/foo/__init__.py", "README.md"]
    result = _classify_deployment(files)
    assert result["weight"] == "pip-install"
    assert result["pip_first_score"] == 1.0
    assert result["containers_needed"] == 0


def test_deployment_docker_heavy(evaluator: ToolAdoptionEvaluator) -> None:
    """Repo with two docker-compose files (≥5 implied containers) → docker-heavy, score 0.0."""
    files = [
        "docker-compose.yml",
        "docker-compose.override.yml",
        "Dockerfile",
        "README.md",
    ]
    result = _classify_deployment(files)
    assert result["weight"] == "docker-heavy"
    assert result["pip_first_score"] == 0.0


def test_deployment_binary_cargo(evaluator: ToolAdoptionEvaluator) -> None:
    """Repo with Cargo.toml → single-binary, score 0.8."""
    files = ["Cargo.toml", "src/main.rs"]
    result = _classify_deployment(files)
    assert result["weight"] == "single-binary"
    assert result["pip_first_score"] == 0.8
    assert result["containers_needed"] == 0


def test_deployment_binary_go(evaluator: ToolAdoptionEvaluator) -> None:
    """Repo with go.mod → single-binary, score 0.8."""
    files = ["go.mod", "main.go"]
    result = _classify_deployment(files)
    assert result["weight"] == "single-binary"
    assert result["pip_first_score"] == 0.8


def test_deployment_docker_light(evaluator: ToolAdoptionEvaluator) -> None:
    """Dockerfile only (no compose) → docker-light, score 0.2."""
    files = ["Dockerfile", "README.md"]
    result = _classify_deployment(files)
    assert result["weight"] == "docker-light"
    assert result["pip_first_score"] == 0.2


# ---------------------------------------------------------------------------
# Feature overlap
# ---------------------------------------------------------------------------


def test_overlap_exact(evaluator: ToolAdoptionEvaluator) -> None:
    """Feature name matching our lib stem → exact overlap."""
    our = {"rate_limiter": "rate_limiter.py", "cost_dashboard": "cost_dashboard.py"}
    results = _compute_overlap(["rate_limiter", "new_thing"], our)
    exact = [r for r in results if r["their_feature"] == "rate_limiter"]
    assert len(exact) == 1
    assert exact[0]["overlap_level"] == "exact"
    assert exact[0]["our_equivalent"] == "rate_limiter.py"


def test_overlap_none(evaluator: ToolAdoptionEvaluator) -> None:
    """Unique feature name → no overlap."""
    our = {"rate_limiter": "rate_limiter.py"}
    results = _compute_overlap(["totally_unique_feature"], our)
    assert results[0]["overlap_level"] == "none"
    assert results[0]["our_equivalent"] is None
    assert results[0]["recommendation"] == "adopt_theirs"


def test_overlap_partial(evaluator: ToolAdoptionEvaluator) -> None:
    """Substring match → partial overlap."""
    our = {"agent_bus": "agent_bus.py"}
    results = _compute_overlap(["agent_bus_v2"], our)
    partial = [r for r in results if r["their_feature"] == "agent_bus_v2"]
    assert partial[0]["overlap_level"] == "partial"


# ---------------------------------------------------------------------------
# UI detection
# ---------------------------------------------------------------------------


def test_ui_detection_web_react(evaluator: ToolAdoptionEvaluator) -> None:
    """React files → web UI, React tech."""
    files = ["frontend/App.tsx", "frontend/index.jsx", "package.json"]
    result = _classify_ui(files)
    assert result["has_ui"] is True
    assert result["ui_type"] == "web"
    assert result["ui_tech"] == "React"


def test_ui_detection_web_vue(evaluator: ToolAdoptionEvaluator) -> None:
    """Vue files → web UI, Vue tech."""
    files = ["src/App.vue", "package.json"]
    result = _classify_ui(files)
    assert result["has_ui"] is True
    assert result["ui_tech"] == "Vue"


def test_ui_detection_none(evaluator: ToolAdoptionEvaluator) -> None:
    """No UI files → has_ui=False."""
    files = ["main.py", "lib/core.py", "pyproject.toml"]
    result = _classify_ui(files)
    assert result["has_ui"] is False
    assert result["ui_type"] is None


# ---------------------------------------------------------------------------
# Recommendation generation
# ---------------------------------------------------------------------------


def _make_evaluation(
    license_verdict: str = "APPROVED",
    license_name: str = "MIT",
    weight: str = "pip-install",
    pip_score: float = 1.0,
    overlap: list | None = None,
) -> dict:
    return {
        "url": "https://github.com/x/y",
        "name": "y",
        "license": {
            "license": license_name,
            "verdict": license_verdict,
            "reason": "test",
            "can_copy_code": license_verdict == "APPROVED",
            "can_copy_patterns": True,
        },
        "deployment": {
            "weight": weight,
            "install_command": "pip install y",
            "containers_needed": 0,
            "estimated_ram_mb": 50,
            "pip_first_score": pip_score,
        },
        "overlap": overlap or [],
        "ui": {"has_ui": False},
        "recommendation": None,
    }


def test_recommendation_adopt(evaluator: ToolAdoptionEvaluator) -> None:
    """Good license + pip + no overlap → ADOPT."""
    ev = _make_evaluation()
    rec = evaluator.generate_recommendation(ev)
    assert rec["verdict"] == "ADOPT"
    assert rec["pip_first"] is True
    assert rec["confidence"] >= 0.8


def test_recommendation_skip_agpl(evaluator: ToolAdoptionEvaluator) -> None:
    """AGPL license → SKIP regardless of everything else."""
    ev = _make_evaluation(license_verdict="BLOCKED", license_name="AGPL-3.0",
                          weight="pip-install", pip_score=1.0)
    rec = evaluator.generate_recommendation(ev)
    assert rec["verdict"] == "SKIP"
    assert rec["confidence"] == 1.0


def test_recommendation_watch_docker_heavy(evaluator: ToolAdoptionEvaluator) -> None:
    """Docker-heavy + no overlap → WATCH."""
    ev = _make_evaluation(weight="docker-heavy", pip_score=0.0)
    rec = evaluator.generate_recommendation(ev)
    assert rec["verdict"] == "WATCH"
    assert rec["pip_first"] is False


def test_recommendation_adapt_exact_overlap(evaluator: ToolAdoptionEvaluator) -> None:
    """Exact overlap → ADAPT."""
    overlap = [{"their_feature": "rate_limiter", "our_equivalent": "rate_limiter.py",
                "overlap_level": "exact", "recommendation": "keep_ours"}]
    ev = _make_evaluation(overlap=overlap)
    rec = evaluator.generate_recommendation(ev)
    assert rec["verdict"] == "ADAPT"


# ---------------------------------------------------------------------------
# Format report
# ---------------------------------------------------------------------------


def test_format_report_readable(evaluator: ToolAdoptionEvaluator) -> None:
    """Formatted report contains key sections."""
    ev = _make_evaluation()
    ev["recommendation"] = evaluator.generate_recommendation(ev)
    report = evaluator.format_evaluation_report(ev)
    assert "TOOL EVALUATION" in report
    assert "License" in report
    assert "Deployment" in report
    assert "RECOMMENDATION" in report
    assert "pip-first score" in report


# ---------------------------------------------------------------------------
# Batch evaluate
# ---------------------------------------------------------------------------


def test_batch_evaluate(evaluator: ToolAdoptionEvaluator) -> None:
    """batch_evaluate processes a list of URLs and returns sorted results."""
    urls = [
        "https://github.com/owner/agpl-tool",
        "https://github.com/owner/nice-tool",
    ]

    def mock_check_license(url: str) -> dict:
        if "agpl" in url:
            return {"license": "AGPL-3.0", "verdict": "BLOCKED", "reason": "copyleft",
                    "can_copy_code": False, "can_copy_patterns": True, "source": "test"}
        return {"license": "MIT", "verdict": "APPROVED", "reason": "permissive",
                "can_copy_code": True, "can_copy_patterns": True, "source": "test"}

    def mock_deployment(url: str) -> dict:
        return {"weight": "pip-install", "install_command": "pip install x",
                "containers_needed": 0, "estimated_ram_mb": 50, "pip_first_score": 1.0}

    with (
        patch.object(evaluator, "check_license", side_effect=mock_check_license),
        patch.object(evaluator, "check_deployment_weight", side_effect=mock_deployment),
        patch.object(evaluator, "detect_feature_overlap", return_value=[]),
        patch.object(evaluator, "check_ui_components",
                     return_value={"has_ui": False, "ui_type": None, "ui_tech": None,
                                   "configurable": False, "integration_effort": "none"}),
    ):
        results = evaluator.batch_evaluate(urls)

    assert len(results) == 2
    # ADOPT must come before SKIP in ranked output
    verdicts = [r["recommendation"]["verdict"] for r in results]
    assert verdicts.index("ADOPT") < verdicts.index("SKIP")


# ---------------------------------------------------------------------------
# Graceful degradation — no gh CLI
# ---------------------------------------------------------------------------


def test_graceful_no_gh_cli(evaluator: ToolAdoptionEvaluator) -> None:
    """Works without gh CLI: returns a result (may have limited info)."""
    with patch("lib.tool_adoption_evaluator._run_gh", return_value=None):
        result = evaluator.evaluate_url("https://github.com/owner/some-repo")
    # Must not raise; recommendation must be present
    assert "recommendation" in result
    assert result["recommendation"] is not None
    assert result["recommendation"]["verdict"] in ("ADOPT", "ADAPT", "WATCH", "SKIP")
