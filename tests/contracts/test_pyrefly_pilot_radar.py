"""Pyrefly pilot stays documented as an advisory tech-radar gate."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


ROOT = Path(__file__).resolve().parents[2]
ADDENDUM = ROOT / "docs" / "06-Daily" / "reports" / "external-tools-radar-pyrefly-addendum-2026-05-15.md"
INDEX = ROOT / "docs" / "06-Daily" / "reports" / "external-tools-radar-INDEX.md"
ECOSYSTEM = ROOT / "docs" / "04-Concepts" / "patterns" / "ecosystem-tools.md"
MANIFEST = ROOT / "manifests" / "external-tools-adoption.yaml"
FEATURE_DD = ROOT / "manifests" / "feature-tool-due-diligence.yaml"
DEPENDENCY_EVIDENCE = ROOT / "manifests" / "dependency-adoption-evidence.yaml"
SCRIPT = ROOT / "scripts" / "cos-pyrefly-pilot"
HOOK = ROOT / "hooks" / "pyrefly-typecheck-advisory.sh"
SKILL = ROOT / "skills" / "pyrefly-typecheck" / "SKILL.md"
CODEX_HOOKS = ROOT / ".codex" / "hooks.json"
COGNITIVE_OS = ROOT / "cognitive-os.yaml"


def _yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_pyrefly_optional_typecheck_extra_and_config_are_advisory() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    extras = pyproject["project"]["optional-dependencies"]
    assert "pyrefly>=1.0,<1.1" in extras["typecheck"]

    config = pyproject["tool"]["pyrefly"]
    assert "lib/**/*.py" in config["project-includes"]
    assert "packages/agent-service/src/**/*.py" in config["project-includes"]
    assert config["errors"]["missing-import"] is False


def test_pyrefly_radar_and_manifests_are_connected() -> None:
    addendum = ADDENDUM.read_text(encoding="utf-8")
    index = INDEX.read_text(encoding="utf-8")
    ecosystem = ECOSYSTEM.read_text(encoding="utf-8")
    assert "TRIAL / advisory CLI gate" in addendum
    assert "make typecheck-pyrefly" in addendum
    assert ADDENDUM.name in index
    assert "Pyrefly — Python Type Checker for Agentic Loops" in ecosystem

    adoption_tools = {row["id"]: row for row in _yaml(MANIFEST)["tools"]}
    pyrefly = adoption_tools["pyrefly"]
    assert pyrefly["verdict"] == "TRIAL"
    assert pyrefly["adoption_kind"] == "advisory-cli-gate"
    assert pyrefly["allowed_surfaces"]["consumer_projects"] is False
    assert pyrefly["source_of_truth"]["radar_report"] == str(ADDENDUM.relative_to(ROOT))

    features = {row["capability_id"]: row for row in _yaml(FEATURE_DD)["features"]}
    assert features["python-typecheck-agentic-loop"]["decision"] == "TRIAL"

    evidence = DEPENDENCY_EVIDENCE.read_text(encoding="utf-8")
    assert "package: pyrefly" in evidence
    assert "consumer: pyproject.toml ([typecheck] extra)" in evidence


def test_pyrefly_runner_defaults_to_advisory_receipts() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "ENFORCE=\"${COS_PYREFLY_ENFORCE:-0}\"" in text
    assert "COS_PYREFLY_STRICT_IMPORTS" in text
    assert ".cognitive-os/reports/pyrefly" in text
    assert "if [ \"$ENFORCE\" = \"1\" ]" in text


def test_pyrefly_skill_and_stop_hook_are_advisory_and_registered() -> None:
    skill = SKILL.read_text(encoding="utf-8")
    assert "name: pyrefly-typecheck" in skill
    assert "make typecheck-pyrefly" in skill
    assert "COS_PYREFLY_ENFORCE=1" in skill

    hook = HOOK.read_text(encoding="utf-8")
    assert "Stop hook" in hook
    assert "scripts/cos-pyrefly-pilot" in hook
    assert "--summary-only" in hook
    assert "exit 0" in hook
    assert "^(lib|scripts|packages/agent-service/src)/.*\\.py$" in hook

    config = _yaml(COGNITIVE_OS)
    entry = config["harness"]["hooks"]["pyrefly-typecheck-advisory"]
    assert entry["event"] == "Stop"
    assert entry["script"] == "hooks/pyrefly-typecheck-advisory.sh"
    assert entry["async"] is True

    codex = CODEX_HOOKS.read_text(encoding="utf-8")
    assert "hooks/pyrefly-typecheck-advisory.sh" in codex
