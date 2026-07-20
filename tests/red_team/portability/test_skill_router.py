# SCOPE: os-only
"""Portability proof for cos_lib/skill_router.py.

``skill_router`` backs three consumer-facing hooks —
``hooks/orchestrator-skill-invocation-gate.sh``, ``hooks/skill-router-bash-gate.sh``,
and ``hooks/skill-router-prompt-suggest.sh`` (all SCOPE: both) — making it the
highest-blast-radius module in this batch. This proof pins that ``SkillRouter``
imports and its primary entry point (``best_match`` / ``match``) works from an
arbitrary working directory against a throwaway consumer project layout with
no ``skills/CATALOG.md`` and no ``SKILL.md`` files at all — the hand-coded
routing table is self-contained and does not require the OS repo tree.

It also pins the documented graceful-degradation contract (see
``tests/unit/test_skill_router_retrieval_audit.py``): the core router never
imports the optional semantic-retrieval stack directly, and — per
``COS_SKILL_ROUTER_DISABLE_SEMANTIC`` — produces correct regex-only matches
even when that stack is unavailable, which is the normal state for a
consumer project that has not installed the optional ML extras.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "cos_lib/skill_router.py"


def test_skill_router_imports_from_arbitrary_project_root(tmp_path: Path, monkeypatch) -> None:
    """Falsification probe: library import must not depend on process cwd."""
    monkeypatch.chdir(tmp_path)
    sys.path.insert(0, str(REPO_ROOT))
    spec = importlib.util.spec_from_file_location("portability_skill_router", ARTIFACT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)


def test_best_match_works_in_arbitrary_consumer_project_without_catalog(tmp_path: Path) -> None:
    """Falsification probe: instantiate ``SkillRouter`` against a bare
    consumer project (no ``skills/`` dir, no ``CATALOG.md``, no
    ``.cognitive-os/``) in a subprocess run from an arbitrary cwd, and
    confirm the hand-coded routing table still matches a real prompt.

    Also asserts the documented negative-context guard (a prompt that only
    critiques a route, e.g. "the router suggested /auto-rollback", must not
    match) — the same false-positive fixture pinned by the retrieval-audit
    manifest's benchmark.
    """
    project_dir = tmp_path / "consumer-project"
    project_dir.mkdir()

    unrelated_cwd = tmp_path / "not-the-project"
    unrelated_cwd.mkdir()

    script = (
        "import os, sys; sys.path.insert(0, %r)\n"
        "os.environ['COS_SKILL_ROUTER_DISABLE_SEMANTIC'] = '1'\n"
        "from cos_lib.skill_router import SkillRouter\n"
        "router = SkillRouter(project_root=%r)\n"
        "assert router.routing_entry_count > 0\n"
        "match = router.best_match('run the tests')\n"
        "assert match is not None, 'expected a match for run-tests prompt'\n"
        "assert match.skill_name == 'run-tests', match.skill_name\n"
        "assert match.invoke_command == '/run-tests'\n"
        "negative = router.best_match('the router suggested /auto-rollback and it was wrong')\n"
        "assert negative is None, negative\n"
        "print('SKILL_ROUTER_OK')\n"
    ) % (str(REPO_ROOT), str(project_dir))

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=unrelated_cwd,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "SKILL_ROUTER_OK" in result.stdout, result.stdout + result.stderr


def test_core_router_has_no_hard_optional_retrieval_import() -> None:
    """Falsification probe: the core router source must not hard-import the
    optional semantic/LLM retrieval stack — those are lazily imported inside
    ``try/except`` in ``SkillRouter._semantic_match`` /
    ``SkillRouter._llm_fallback_match`` so a consumer project without the
    optional ML extras installed still gets correct regex-only routing.
    """
    text = ARTIFACT.read_text(encoding="utf-8")
    assert "import cos_lib.semantic_skill_matcher" not in text
    assert "from cos_lib.semantic_skill_matcher import" not in text.split("_semantic_match")[0]
