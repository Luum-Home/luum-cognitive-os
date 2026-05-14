from __future__ import annotations

import importlib.machinery
import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "cos-portability-proof-scaffold"


def _load_module():
    loader = importlib.machinery.SourceFileLoader("cos_portability_proof_scaffold", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[loader.name] = module
    spec.loader.exec_module(module)
    return module


def test_scaffold_creates_gate_compatible_hook_proof(tmp_path: Path) -> None:
    mod = _load_module()
    artifact = tmp_path / "hooks" / "foo-bar.sh"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("#!/usr/bin/env bash\n# SCOPE: both\nexit 0\n", encoding="utf-8")

    target = mod.scaffold(tmp_path, "hooks/foo-bar.sh")

    assert target.relative_to(tmp_path).as_posix() == "tests/red_team/portability/test_foo-bar.py"
    text = target.read_text(encoding="utf-8")
    assert "Falsification probe" in text
    assert "hooks/foo-bar.sh" in text


def test_scaffold_uses_skill_specific_proof_name(tmp_path: Path) -> None:
    mod = _load_module()
    artifact = tmp_path / "skills" / "add-hook" / "SKILL.md"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("<!-- SCOPE: both -->\n---\nname: add-hook\n---\n", encoding="utf-8")

    target = mod.scaffold(tmp_path, "skills/add-hook/SKILL.md")

    assert target.relative_to(tmp_path).as_posix() == "tests/red_team/portability/test_skill_add_hook.py"
    assert "skill_add_hook" in target.read_text(encoding="utf-8")


def test_scaffold_refuses_overwrite_without_force(tmp_path: Path) -> None:
    mod = _load_module()
    artifact = tmp_path / "hooks" / "foo.sh"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("#!/usr/bin/env bash\n# SCOPE: both\n", encoding="utf-8")
    first = mod.scaffold(tmp_path, "hooks/foo.sh")
    first.write_text("custom\n", encoding="utf-8")

    try:
        mod.scaffold(tmp_path, "hooks/foo.sh")
    except SystemExit as exc:
        assert "refusing to overwrite" in str(exc)
    else:
        raise AssertionError("expected overwrite refusal")

    second = mod.scaffold(tmp_path, "hooks/foo.sh", force=True)
    assert second == first
    assert "custom" not in second.read_text(encoding="utf-8")
