# SCOPE: os-only
"""Unit tests for the session-start-stack-recommend.sh hook.

Tests execute the actual StackSkillRecommender code against a fixture project
and verify the output state file — not just file existence.
"""

from __future__ import annotations

import json
import os
import subprocess
import textwrap
from pathlib import Path

import pytest

from lib.stack_skill_recommender import SkillRecommendation, StackSkillRecommender


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_project(tmp_path: Path, files: dict[str, str | bytes]) -> Path:
    """Create a fixture project directory with the given files."""
    for rel_path, content in files.items():
        p = tmp_path / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            p.write_bytes(content)
        else:
            p.write_text(content, encoding="utf-8")
    return tmp_path


def _write_output(project_path: Path, recs: list[SkillRecommendation]) -> Path:
    """Replicate hook logic: write stack-recommendations.json to the state dir."""
    from datetime import datetime, timezone

    output = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "project_path": str(project_path.resolve()),
        "recommendations": [
            {
                "skill_name": r.skill_name,
                "reason": r.reason,
                "source": r.source,
                "install_command": r.install_command,
                "priority": r.priority,
            }
            for r in recs
        ],
    }
    state_dir = project_path / ".cognitive-os" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    out_path = state_dir / "stack-recommendations.json"
    tmp_path_file = out_path.with_suffix(".json.tmp")
    tmp_path_file.write_text(json.dumps(output, indent=2), encoding="utf-8")
    tmp_path_file.replace(out_path)
    return out_path


# ---------------------------------------------------------------------------
# Test A: Python package project produces python recommendation
# ---------------------------------------------------------------------------


def test_python_project_produces_recommendations(tmp_path: Path) -> None:
    """A project with pyproject.toml triggers a Python skill recommendation."""
    _make_project(
        tmp_path,
        {
            "pyproject.toml": textwrap.dedent("""\
                [project]
                name = "my-service"
                requires-python = ">=3.11"
            """),
        },
    )

    recommender = StackSkillRecommender()
    recs = recommender.recommend(str(tmp_path))

    skill_names = [r.skill_name for r in recs]
    assert "test-driven-development" in skill_names, (
        f"Expected 'test-driven-development' in recommendations for Python project, got: {skill_names}"
    )

    # Verify output file can be produced
    out_path = _write_output(tmp_path, recs)
    assert out_path.exists()
    data = json.loads(out_path.read_text())
    assert data["project_path"] == str(tmp_path.resolve())
    assert isinstance(data["recommendations"], list)
    assert len(data["recommendations"]) >= 1


# ---------------------------------------------------------------------------
# Test B: Go project produces go-testing recommendation
# ---------------------------------------------------------------------------


def test_go_project_produces_recommendations(tmp_path: Path) -> None:
    """A project with go.mod triggers a Go skill recommendation."""
    _make_project(
        tmp_path,
        {
            "go.mod": "module example.com/myapp\n\ngo 1.21\n",
        },
    )

    recommender = StackSkillRecommender()
    recs = recommender.recommend(str(tmp_path))

    skill_names = [r.skill_name for r in recs]
    assert "go-testing" in skill_names, (
        f"Expected 'go-testing' in recommendations for Go project, got: {skill_names}"
    )


# ---------------------------------------------------------------------------
# Test C: React + TypeScript combo produces the react-typescript combo skill
# ---------------------------------------------------------------------------


def test_react_typescript_combo_recommendation(tmp_path: Path) -> None:
    """A project with React + TypeScript triggers the combo recommendation."""
    _make_project(
        tmp_path,
        {
            "tsconfig.json": '{"compilerOptions": {"target": "ES2022"}}',
            "package.json": json.dumps(
                {
                    "name": "my-app",
                    "dependencies": {"react": "^18.0.0", "react-dom": "^18.0.0"},
                    "devDependencies": {"typescript": "^5.0.0"},
                }
            ),
        },
    )

    recommender = StackSkillRecommender()
    recs = recommender.recommend(str(tmp_path))

    skill_names = [r.skill_name for r in recs]
    assert "react-typescript" in skill_names, (
        f"Expected 'react-typescript' combo skill, got: {skill_names}"
    )


# ---------------------------------------------------------------------------
# Test D: Empty project produces no recommendations and valid output file
# ---------------------------------------------------------------------------


def test_empty_project_produces_empty_recommendations(tmp_path: Path) -> None:
    """An empty project directory produces an empty recommendations list."""
    recommender = StackSkillRecommender()
    recs = recommender.recommend(str(tmp_path))

    assert recs == [], f"Expected no recommendations for empty project, got: {recs}"

    out_path = _write_output(tmp_path, recs)
    data = json.loads(out_path.read_text())
    assert data["recommendations"] == []
    assert "generated_at" in data
    assert "project_path" in data


# ---------------------------------------------------------------------------
# Test E: Output file schema is valid (required fields present)
# ---------------------------------------------------------------------------


def test_output_file_schema(tmp_path: Path) -> None:
    """The output JSON file contains required top-level keys and valid recommendation shape."""
    _make_project(
        tmp_path,
        {
            "go.mod": "module example.com/test\n\ngo 1.22\n",
            "Dockerfile": "FROM golang:1.22-alpine\n",
        },
    )

    recommender = StackSkillRecommender()
    recs = recommender.recommend(str(tmp_path))
    out_path = _write_output(tmp_path, recs)

    data = json.loads(out_path.read_text())
    assert "generated_at" in data, "Output must contain 'generated_at'"
    assert "project_path" in data, "Output must contain 'project_path'"
    assert "recommendations" in data, "Output must contain 'recommendations'"

    for rec in data["recommendations"]:
        for field in ("skill_name", "reason", "source", "install_command", "priority"):
            assert field in rec, f"Recommendation missing field '{field}': {rec}"
        assert rec["priority"] in ("recommended", "optional", "suggested"), (
            f"Unexpected priority value: {rec['priority']}"
        )


# ---------------------------------------------------------------------------
# Test F: Hook script executes without error in subprocess (smoke test)
# ---------------------------------------------------------------------------


def test_hook_script_exits_zero(tmp_path: Path) -> None:
    """The hook script exits 0 even when no stack is detected."""
    hook_path = Path(__file__).parent.parent.parent / "hooks" / "session-start-stack-recommend.sh"
    if not hook_path.exists():
        pytest.skip(f"Hook not found at {hook_path}")

    result = subprocess.run(
        ["bash", str(hook_path)],
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "CLAUDE_PROJECT_DIR": str(tmp_path),
            "COS_DISABLE_STACK_RECOMMEND": "",
        },
        timeout=30,
    )
    assert result.returncode == 0, (
        f"Hook exited {result.returncode}\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
