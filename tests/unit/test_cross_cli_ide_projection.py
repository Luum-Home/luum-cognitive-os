"""Cross CLI/IDE projection guard for recently adapted portable primitives."""

from __future__ import annotations

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
RECENT_PORTABLE_PRIMITIVES = (
    "packages/quality-gates/skills/dod-check/SKILL.md",
    "packages/sdd-compound/skills/plan-chore/SKILL.md",
    "packages/sdd-compound/skills/plan-feature/SKILL.md",
    "skills/skill-creator/SKILL.md",
    "skills/graphify-query/SKILL.md",
    "scripts/cos-conflict-marker-guard",
    "scripts/cos-graphify-build",
    "scripts/cos-graphify-context-replay-benchmark",
    "scripts/cos-graphify-hotspot-report",
    "scripts/cos-graphify-phase-d-semantic",
    "scripts/cos-graphify-preload-matrix",
    "scripts/cos-graphify-run-telemetry",
    "scripts/cos-graphify-token-footprint",
    "scripts/cos-graphify-token-reduction-smoke",
)
RECENT_SKILLS = (
    "packages/quality-gates/skills/dod-check/SKILL.md",
    "packages/sdd-compound/skills/plan-chore/SKILL.md",
    "packages/sdd-compound/skills/plan-feature/SKILL.md",
    "skills/skill-creator/SKILL.md",
    "skills/graphify-query/SKILL.md",
)


def _harness_ids() -> set[str]:
    payload = yaml.safe_load((ROOT / "manifests" / "harness-projection.yaml").read_text(encoding="utf-8"))
    return {row["id"] for row in payload["harnesses"] if isinstance(row, dict) and row.get("id")}


def _lifecycle_rows() -> dict[str, dict[str, object]]:
    payload = yaml.safe_load((ROOT / "manifests" / "primitive-lifecycle.yaml").read_text(encoding="utf-8"))
    return {row["id"]: row for row in payload["primitives"] if isinstance(row, dict) and row.get("id")}


def _adapter_path_for_harness(harness: str) -> Path:
    mapping = {
        "claude": "claude-code",
        "vscode-copilot": "copilot",
    }
    return ROOT / ".ai" / "adapters" / mapping.get(harness, harness) / "adapter.json"


def test_recent_portable_primitives_declare_every_projected_harness() -> None:
    harnesses = _harness_ids()
    rows = _lifecycle_rows()

    assert "opencode" in harnesses
    assert "shell-ci" in harnesses
    assert "codex" in harnesses
    assert "claude" in harnesses
    for primitive_id in RECENT_PORTABLE_PRIMITIVES:
        row = rows[primitive_id]
        assert set(row["supported_harnesses"]) == harnesses, primitive_id
        assert row["runtime_projection"] is False, primitive_id


def test_recent_portable_primitives_are_visible_in_every_ai_adapter_manifest() -> None:
    for harness in _harness_ids():
        adapter_path = _adapter_path_for_harness(harness)
        payload = json.loads(adapter_path.read_text(encoding="utf-8"))
        projected = {item["portable_id"] for item in payload["projected_primitives"]}

        missing = set(RECENT_PORTABLE_PRIMITIVES) - projected
        assert missing == set(), f"{harness} missing {sorted(missing)}"


def test_recent_skill_frontmatter_uses_canonical_projection_not_one_harness_allowlist() -> None:
    for skill in RECENT_SKILLS:
        frontmatter = (ROOT / skill).read_text(encoding="utf-8").split("---", 2)[1]
        assert "cos-projected-cli-ide" in frontmatter, skill
        assert "claude-code" not in frontmatter, skill
        assert "platforms:\n- claude-code" not in frontmatter, skill
        assert "platforms:\n  - claude-code" not in frontmatter, skill
