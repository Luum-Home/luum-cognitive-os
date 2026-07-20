# SCOPE: os-only
"""Portability proof for cos_lib/semantic_skill_matcher.py.

``SemanticSkillMatcher`` backs the consumer-facing skill router's semantic
fallback layer (SCOPE: both). This proof pins that the module imports and
its primary entry point (``SemanticSkillMatcher.from_routing_table`` ->
``match``) runs correctly from an arbitrary working directory, using only a
cache dir relative to the project it is given — never anything that assumes
it is running inside the Cognitive OS source repo itself.

The optional ``fastembed``/``numpy`` embedding stack is normally absent in a
consumer install (it's an opt-in extra). This proof therefore asserts the
documented graceful-degradation contract — ``match()`` returns ``[]`` rather
than raising — instead of requiring the optional stack to be present.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "cos_lib/semantic_skill_matcher.py"


def test_semantic_skill_matcher_imports_from_arbitrary_project_root(tmp_path: Path, monkeypatch) -> None:
    """Falsification probe: library import must not depend on process cwd."""
    monkeypatch.chdir(tmp_path)
    sys.path.insert(0, str(REPO_ROOT))
    spec = importlib.util.spec_from_file_location("portability_semantic_skill_matcher", ARTIFACT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)


def test_matcher_degrades_gracefully_without_optional_stack_in_arbitrary_project(tmp_path: Path) -> None:
    """Falsification probe: exercise the real entry point in a throwaway project.

    Builds a consumer project dir under ``tmp_path`` (standing in for a
    project that merely installed the OS — not the Cognitive OS source repo,
    and without the optional ``[semantic]``/``fastembed`` extra), builds a
    matcher from a routing table, and confirms ``match()`` returns ``[]``
    rather than raising — the documented consumer-default behaviour — while
    writing nothing outside the project's own cache dir.
    """
    project_dir = tmp_path / "consumer-project"
    project_dir.mkdir()

    script = (
        "import sys; sys.path.insert(0, %r)\n"
        "from types import SimpleNamespace\n"
        "from cos_lib.semantic_skill_matcher import SemanticSkillMatcher, load_skill_metadata\n"
        "entries = [SimpleNamespace(skill_name='rate-limiting', invoke_command='/rate-limiting')]\n"
        "metadata = {'rate-limiting': {'description': 'Throttle agent tool calls per minute', "
        "'summary_line': '', 'routing_intents': []}}\n"
        "matcher = SemanticSkillMatcher.from_routing_table(entries, metadata, cache_dir=%r)\n"
        "matches = matcher.match('please throttle the tool calls')\n"
        "print(type(matches).__name__)\n"
        "print(len(matches))\n"
    ) % (str(REPO_ROOT), str(project_dir / ".cognitive-os" / "cache" / "semantic-router"))

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=project_dir,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    out_lines = result.stdout.strip().splitlines()
    assert out_lines[0] == "list"
    # fastembed is not installed in this environment (the normal consumer
    # case) -> graceful degradation to an empty match list, never a raise.
    assert out_lines[1] == "0"

    # Nothing was written outside the consumer project's own tree.
    assert not (tmp_path / ".cognitive-os").exists()
