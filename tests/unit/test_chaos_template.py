"""Unit tests for scripts/cos_chaos_template.py (ADR-041).

Tests: skeleton syntactically valid, placeholders present, writes to correct path.
"""
from __future__ import annotations

import ast
from pathlib import Path

import importlib.util

import pytest

# Load module directly (filename has hyphens, not importable as package name)
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
_MOD_PATH = _SCRIPTS_DIR / "cos_chaos_template.py"

_spec = importlib.util.spec_from_file_location("cos_chaos_template", _MOD_PATH)
_mod = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]

generate_skeleton = _mod.generate_skeleton
_infer_tier = _mod._infer_tier
_safe_name = _mod._safe_name
_is_script = _mod._is_script


# ── Tier inference ─────────────────────────────────────────────────────────────

def test_infer_tier_a_secret():
    assert _infer_tier("hooks/secret-detector.sh") == "A"


def test_infer_tier_a_destructive():
    assert _infer_tier("hooks/destructive-rm-blocker.sh") == "A"


def test_infer_tier_b_monitor():
    assert _infer_tier("hooks/agent-bus-monitor.sh") == "B"


def test_infer_tier_c_mlflow():
    assert _infer_tier("hooks/mlflow-sync.sh") == "C"


def test_infer_tier_d_skill_md():
    assert _infer_tier("skills/auto-refine/SKILL.md") == "D"


# ── Safe name conversion ───────────────────────────────────────────────────────

def test_safe_name_hyphenated():
    assert _safe_name("hooks/secret-detector.sh") == "secret_detector"


def test_safe_name_complex():
    assert _safe_name("hooks/auto-rollback-trigger.sh") == "auto_rollback_trigger"


def test_safe_name_no_extension():
    result = _safe_name("hooks/some_hook")
    assert result == "some_hook"


# ── Skeleton generation ────────────────────────────────────────────────────────

def test_skeleton_creates_file(tmp_path: Path):
    """generate_skeleton must create the test file at the expected path."""
    fake_project = tmp_path / "project"
    fake_project.mkdir()
    output_dir = tmp_path / "chaos"

    out_path = generate_skeleton(
        "hooks/secret-detector.sh",
        trigger="PreToolUse with literal API key",
        project_dir=fake_project,
        output_dir=output_dir,
    )

    assert out_path.exists(), f"Expected file at {out_path}"
    assert out_path.name == "test_secret_detector_exercised.py"
    assert out_path.parent == output_dir


def test_skeleton_is_syntactically_valid_python(tmp_path: Path):
    """Generated skeleton must be valid Python (parseable by ast)."""
    fake_project = tmp_path / "project"
    fake_project.mkdir()
    output_dir = tmp_path / "chaos"

    out_path = generate_skeleton(
        "hooks/auto-rollback-trigger.sh",
        trigger=None,
        project_dir=fake_project,
        output_dir=output_dir,
    )

    source = out_path.read_text()
    try:
        ast.parse(source)
    except SyntaxError as exc:
        pytest.fail(f"Generated skeleton is not valid Python: {exc}\n\nSource:\n{source[:500]}")


def test_skeleton_contains_placeholders(tmp_path: Path):
    """Generated skeleton must contain PLACEHOLDER markers for customization."""
    fake_project = tmp_path / "project"
    fake_project.mkdir()
    output_dir = tmp_path / "chaos"

    out_path = generate_skeleton(
        "hooks/content-policy.sh",
        trigger="PostToolUse Write with prohibited term",
        project_dir=fake_project,
        output_dir=output_dir,
    )

    source = out_path.read_text()
    assert "PLACEHOLDER" in source, "Generated skeleton must contain PLACEHOLDER markers"


def test_skeleton_contains_component_path(tmp_path: Path):
    """Generated skeleton must reference the component path."""
    fake_project = tmp_path / "project"
    fake_project.mkdir()
    output_dir = tmp_path / "chaos"
    component = "hooks/release-guard.sh"

    out_path = generate_skeleton(component, trigger=None, project_dir=fake_project, output_dir=output_dir)
    source = out_path.read_text()
    assert component in source, f"Component path '{component}' not found in skeleton"


def test_skeleton_contains_tier_label(tmp_path: Path):
    """Generated skeleton docstring must include the inferred tier."""
    fake_project = tmp_path / "project"
    fake_project.mkdir()
    output_dir = tmp_path / "chaos"

    out_path = generate_skeleton(
        "hooks/secret-detector.sh",
        trigger=None,
        project_dir=fake_project,
        output_dir=output_dir,
    )
    source = out_path.read_text()
    assert "Tier: A" in source, "Tier A label must appear in docstring"


def test_skeleton_writes_to_correct_output_dir(tmp_path: Path):
    """Output file must be created inside the specified output_dir."""
    fake_project = tmp_path / "project"
    fake_project.mkdir()
    custom_dir = tmp_path / "my_chaos_tests"

    out_path = generate_skeleton(
        "hooks/error-learning.sh",
        trigger=None,
        project_dir=fake_project,
        output_dir=custom_dir,
    )

    assert out_path.parent == custom_dir
    assert custom_dir.exists(), "output_dir must be created if it doesn't exist"


def test_script_template_used_for_python_scripts(tmp_path: Path):
    """Python scripts (lib/*.py) must use script template (no hook-style JSON payload)."""
    fake_project = tmp_path / "project"
    fake_project.mkdir()
    output_dir = tmp_path / "chaos"

    out_path = generate_skeleton(
        "lib/license_guard.py",
        trigger=None,
        project_dir=fake_project,
        output_dir=output_dir,
    )

    source = out_path.read_text()
    # Script template uses subprocess with --summary, not stdin JSON payload
    assert "subprocess" in source
    # Must be valid Python
    ast.parse(source)


def test_hook_template_used_for_shell_hooks(tmp_path: Path):
    """Shell hooks (hooks/*.sh) must use hook template with stdin payload pattern."""
    fake_project = tmp_path / "project"
    fake_project.mkdir()
    output_dir = tmp_path / "chaos"

    out_path = generate_skeleton(
        "hooks/auto-verify.sh",
        trigger=None,
        project_dir=fake_project,
        output_dir=output_dir,
    )

    source = out_path.read_text()
    # Hook template uses bash subprocess with stdin payload
    assert "bash" in source
    assert "stdin_payload" in source
