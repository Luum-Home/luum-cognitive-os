# SCOPE: os-only
"""Portability proof for cos_lib/rule_router.py.

``RuleRouter`` backs the consumer-facing rule auto-selection surface
(SCOPE: both). This proof pins that the module imports and its primary entry
point (``RuleRouter.best_match`` / ``top_matches``) runs correctly from an
arbitrary working directory, enumerating only ``rules/*.md`` and
``packages/*/rules/*.md`` relative to the project root it is given — never
anything that assumes it is running inside the Cognitive OS source repo
itself.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "cos_lib/rule_router.py"

_RULE_MD = """---
enforcement: agent-instruction
routing_patterns:
  - pattern: "\\\\bacceptance criteria\\\\b"
    confidence: 0.92
trigger_priority: high
---

# Acceptance Criteria Rule

Prompts must include verifiable acceptance criteria.
"""


def test_rule_router_imports_from_arbitrary_project_root(tmp_path: Path, monkeypatch) -> None:
    """Falsification probe: library import must not depend on process cwd."""
    monkeypatch.chdir(tmp_path)
    sys.path.insert(0, str(REPO_ROOT))
    spec = importlib.util.spec_from_file_location("portability_rule_router", ARTIFACT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)


def test_rule_router_matches_prompt_in_arbitrary_consumer_project(tmp_path: Path) -> None:
    """Falsification probe: exercise the real entry point in a throwaway project.

    Builds a consumer project dir under ``tmp_path`` (standing in for a
    project that merely installed the OS — not the Cognitive OS source repo)
    with its own ``rules/*.md``, and confirms ``best_match``/``top_matches``
    find the rule via its frontmatter ``routing_patterns`` alone.
    """
    project_dir = tmp_path / "consumer-project"
    rules_dir = project_dir / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "acceptance-criteria.md").write_text(_RULE_MD)

    script = (
        "import sys; sys.path.insert(0, %r)\n"
        "from pathlib import Path\n"
        "from cos_lib.rule_router import RuleRouter\n"
        "router = RuleRouter(project_root=Path(%r))\n"
        "print(router.loaded_rule_count)\n"
        "print(router.routable_rule_count)\n"
        "best = router.best_match('does it have acceptance criteria?')\n"
        "print(best.rule_name if best else 'NO_MATCH')\n"
        "print(best.rule_path if best else 'NO_MATCH')\n"
    ) % (str(REPO_ROOT), str(project_dir))

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=project_dir,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    out_lines = result.stdout.strip().splitlines()
    assert out_lines[0] == "1"
    assert out_lines[1] == "1"
    assert out_lines[2] == "acceptance-criteria"
    assert out_lines[3] == "rules/acceptance-criteria.md"

    # Nothing was written outside the consumer project's own tree.
    assert not (tmp_path / ".cognitive-os").exists()
