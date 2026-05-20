"""Behavioral contracts for the core-vs-extensions split evidence surface."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

import pytest


pytestmark = pytest.mark.contract

PROJECT_ROOT = Path(__file__).resolve().parents[2]

_SPEC = importlib.util.spec_from_file_location(
    "generate_compact_catalog",
    PROJECT_ROOT / "scripts" / "generate_compact_catalog.py",
)
assert _SPEC and _SPEC.loader
generate_compact_catalog = importlib.util.module_from_spec(_SPEC)
sys.modules["generate_compact_catalog"] = generate_compact_catalog
_SPEC.loader.exec_module(generate_compact_catalog)


def write_skill(path: Path, name: str, description: str) -> None:
    """Create a minimal user-facing SKILL.md fixture."""
    path.mkdir(parents=True, exist_ok=True)
    (path / "SKILL.md").write_text(
        "---\n"
        f"name: {name}\n"
        "audience: both\n"
        f"description: {description}\n"
        "---\n"
        f"# {name}\n",
        encoding="utf-8",
    )


def test_compact_catalog_renders_core_and_extension_scope_tags(tmp_path: Path) -> None:
    """The generator must classify top-level skills as core and packaged skills as extensions."""
    write_skill(tmp_path / "skills" / "core-demo", "core-demo", "Core demo skill.")
    write_skill(
        tmp_path / "packages" / "cos-demo" / "skills" / "ext-demo",
        "ext-demo",
        "Extension demo skill.",
    )

    skills = generate_compact_catalog.dedupe(generate_compact_catalog.collect_skills(tmp_path))
    rendered = generate_compact_catalog.render_compact(skills)

    assert "| core-demo | [core] | Core demo skill. |" in rendered
    assert "| ext-demo | [ext:cos-demo] | Extension demo skill. |" in rendered


def test_install_hook_dry_run_accepts_packaged_user_prompt_submit_hook() -> None:
    """A packaged hook registration can be resolved for a non-legacy Claude event."""
    result = subprocess.run(
        [
            str(PROJECT_ROOT / "scripts" / "cos-install-hook"),
            "prompt-quality-llm",
            "--event",
            "UserPromptSubmit",
            "--matcher",
            "*",
            "--dry-run",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "harness.hooks.UserPromptSubmit" in result.stdout
    assert "packages/cos-advisory-llm/hooks/prompt-quality-llm.sh" in result.stdout


@pytest.mark.timeout(180)
def test_aspirational_audit_reports_zero_active_dormant_debt() -> None:
    """The current classifier should prove Phase 3 starts from zero active dormant debt."""
    payload = None
    result = None
    for attempt in range(3):
        result = subprocess.run(
            [sys.executable, "scripts/aspirational_audit.py", "--json"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout)
        if payload["dormant_aspirational_ratio"] == 0.0:
            break
        if attempt < 2:
            time.sleep(1.0)

    assert payload is not None
    assert payload["dormant_aspirational_ratio"] == 0.0
    assert set(payload["counts"]) == {"REAL", "ON_DEMAND", "METADATA"}
