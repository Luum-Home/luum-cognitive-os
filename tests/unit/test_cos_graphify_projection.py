"""Projection coverage for the ADR-331 Graphify primitive family."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
GRAPHIFY_SCRIPTS = (
    "scripts/cos-graphify-build",
    "scripts/cos-graphify-context-replay-benchmark",
    "scripts/cos-graphify-hotspot-report",
    "scripts/cos-graphify-phase-d-semantic",
    "scripts/cos-graphify-preload-matrix",
    "scripts/cos-graphify-run-telemetry",
    "scripts/cos-graphify-token-footprint",
    "scripts/cos-graphify-token-reduction-smoke",
)
GRAPHIFY_SKILL = "skills/graphify-query/SKILL.md"


def _lifecycle_rows() -> dict[str, dict[str, object]]:
    payload = yaml.safe_load((ROOT / "manifests" / "primitive-lifecycle.yaml").read_text(encoding="utf-8"))
    return {row["id"]: row for row in payload["primitives"] if isinstance(row, dict) and row.get("id")}


def _overlay_tool_rows() -> dict[str, dict[str, object]]:
    rows: dict[str, dict[str, object]] = {}
    for path in (ROOT / ".ai" / "primitives" / "tools").glob("scripts-cos-graphify-*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows[str(payload["source_id"])] = payload
    return rows


def test_all_graphify_scripts_are_lifecycle_declared() -> None:
    rows = _lifecycle_rows()

    for script in GRAPHIFY_SCRIPTS:
        row = rows[script]
        assert row["owner_adr"] == "ADR-331"
        assert row["kind"] == "script"
        assert row["runtime_projection"] is False
        assert "codex" in row["supported_harnesses"]
        assert "claude" in row["supported_harnesses"]
        assert script in row["projection_targets"]


def test_all_graphify_scripts_are_projected_as_ai_tool_primitives() -> None:
    rows = _overlay_tool_rows()

    assert set(GRAPHIFY_SCRIPTS).issubset(rows)
    for script in GRAPHIFY_SCRIPTS:
        payload = rows[script]
        assert payload["family"] == "script"
        assert payload["lifecycle"]["owner_adr"] == "ADR-331"
        assert payload["portable_contract"]["trigger"]["runtime_projection"] is False
        assert script in payload["projection_targets"]


def test_graphify_query_skill_is_materialized_for_kernel_and_driver_surfaces() -> None:
    rows = _lifecycle_rows()
    skill_row = rows[GRAPHIFY_SKILL]
    assert skill_row["kind"] == "skill"
    assert skill_row["runtime_projection"] is False

    source = ROOT / GRAPHIFY_SKILL
    kernel = ROOT / ".cognitive-os" / "skills" / "cos" / "graphify-query" / "SKILL.md"
    driver = ROOT / ".claude" / "skills" / "graphify-query" / "SKILL.md"

    assert source.exists()
    assert kernel.resolve() == source.resolve()
    assert driver.resolve() == source.resolve()


def test_graphify_wrappers_execute_directly_for_help() -> None:
    for script in GRAPHIFY_SCRIPTS:
        completed = subprocess.run(
            [str(ROOT / script), "--help"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
        assert completed.returncode == 0, f"{script} failed: {completed.stderr}"
        assert "usage:" in completed.stdout


def test_graphify_skill_preserves_navigation_not_truth_boundary() -> None:
    text = (ROOT / GRAPHIFY_SKILL).read_text(encoding="utf-8")

    assert "not a correctness proof" in text
    assert "Do not install upstream Graphify hooks" in text
    assert "Do not say the graph proves behavior" in text


def test_graphify_default_boundary_excludes_visual_and_server_surfaces() -> None:
    skill_text = (ROOT / GRAPHIFY_SKILL).read_text(encoding="utf-8")
    adr_text = (
        ROOT
        / "docs"
        / "02-Decisions"
        / "adrs"
        / "ADR-331-graphify-portable-context-optimization-primitive.md"
    ).read_text(encoding="utf-8")
    plan_text = (
        ROOT
        / "docs"
        / "04-Concepts"
        / "architecture"
        / "graphify-portable-optimization-plan-2026-05-22.md"
    ).read_text(encoding="utf-8")

    combined = "\n".join([skill_text, adr_text, plan_text])
    assert "Graphify is only the current backend" in skill_text
    assert "web graph viewer" in skill_text
    assert "visual exports" in combined
    assert "Graphify-managed MCP" in combined
    assert "Neo4j" in combined
    assert "watch mode" in combined
    assert "separate approved" in combined
