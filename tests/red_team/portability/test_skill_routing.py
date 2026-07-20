# SCOPE: os-only
"""Portability proof for cos_lib/skill_routing.py.

Pins that the ADR-050 per-skill routing loader (``find_skill_md``,
``load_skill_requirements``, ``load_skill_requirements_by_name``) resolves a
real ``SKILL.md`` and parses its ``routing:`` frontmatter block from an
arbitrary working directory, in a subprocess, using only a project-relative
``skills/<name>/SKILL.md`` layout — never anything that assumes it is running
inside the Cognitive OS source repo.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "cos_lib/skill_routing.py"

SKILL_MD = """---
name: portability-probe
model: sonnet
routing:
  tier: balanced
  providers_preferred: [claude]
  providers_excluded: [minimax]
  budget_max_usd_per_call: 0.5
---

# Portability Probe

A throwaway skill used only to prove skill_routing.py works outside the OS repo.
"""


def test_skill_routing_imports_from_arbitrary_project_root(tmp_path: Path, monkeypatch) -> None:
    """Falsification probe: library import must not depend on process cwd."""
    monkeypatch.chdir(tmp_path)
    sys.path.insert(0, str(REPO_ROOT))
    spec = importlib.util.spec_from_file_location("portability_skill_routing", ARTIFACT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)


def test_load_skill_requirements_by_name_from_arbitrary_consumer_project(tmp_path: Path) -> None:
    """Falsification probe: resolve a skill by name and parse its routing
    block, in a subprocess run from an arbitrary cwd, against a throwaway
    consumer project layout (``<project>/skills/<name>/SKILL.md``).

    Proves the loader has no hidden dependency on running inside the
    Cognitive OS source repo (e.g. relative paths, sibling manifests).
    """
    project_dir = tmp_path / "consumer-project"
    skill_dir = project_dir / "skills" / "portability-probe"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(SKILL_MD, encoding="utf-8")

    unrelated_cwd = tmp_path / "not-the-project"
    unrelated_cwd.mkdir()

    script = (
        "import sys; sys.path.insert(0, %r)\n"
        "from cos_lib.skill_routing import load_skill_requirements_by_name, to_dispatch_dict\n"
        "req = load_skill_requirements_by_name('portability-probe', project_root=%r)\n"
        "assert req is not None, 'expected routing block to be found'\n"
        "assert req.tier == 'balanced', req.tier\n"
        "assert req.providers_preferred == ['claude'], req.providers_preferred\n"
        "assert req.providers_excluded == ['minimax'], req.providers_excluded\n"
        "assert req.budget_max_usd_per_call == 0.5, req.budget_max_usd_per_call\n"
        "d = to_dispatch_dict(req)\n"
        "assert d['tier'] == 'balanced'\n"
        "print('SKILL_ROUTING_OK')\n"
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
    assert "SKILL_ROUTING_OK" in result.stdout, result.stdout + result.stderr


def test_missing_skill_and_missing_routing_block_return_none(tmp_path: Path, monkeypatch) -> None:
    """Falsification probe: absent skill and absent routing block degrade to
    None gracefully rather than raising, from an arbitrary cwd.
    """
    monkeypatch.chdir(tmp_path)
    sys.path.insert(0, str(REPO_ROOT))
    from cos_lib.skill_routing import load_skill_requirements_by_name, load_skill_requirements

    project_dir = tmp_path / "empty-consumer-project"
    project_dir.mkdir()
    assert load_skill_requirements_by_name("does-not-exist", project_root=project_dir) is None

    no_routing_skill_dir = project_dir / "skills" / "no-routing"
    no_routing_skill_dir.mkdir(parents=True)
    (no_routing_skill_dir / "SKILL.md").write_text(
        "---\nname: no-routing\n---\n\n# No routing block here\n", encoding="utf-8"
    )
    assert load_skill_requirements(no_routing_skill_dir / "SKILL.md") is None
