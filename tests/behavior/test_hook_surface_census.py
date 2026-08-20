"""Behavior proof for scripts/hook_surface_census.py.

The census exists to settle a contradiction between two other audits, so its
own two load-bearing behaviors are the ones a mistake would hide:

  1. The driver is read COMMENT-STRIPPED. The header of
     settings-driver-claude-code.sh names hooks while documenting their
     ABSENCE; a raw substring test turns that documentation into evidence of
     registration. That is not hypothetical -- it is why
     hook_surface_classifier.py reports publication-safety.sh as
     `profile_gated` today.
  2. `COS_ALLOW_PROTECTED_CONFIG_WRITE` is popped from the child audits' env.
     It is inherited, and a measurement taken with a write permission the
     normal caller lacks is not reproducible by the normal caller.

Each test carries a falsification probe: it first asserts the naive behavior
WOULD produce the wrong answer, then that the implementation does not.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CENSUS = REPO / "scripts/hook_surface_census.py"


def _load():
    spec = importlib.util.spec_from_file_location("hook_surface_census", CENSUS)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_driver_comment_naming_a_hook_is_not_read_as_registration():
    census = _load()
    driver_text = (
        "#!/usr/bin/env bash\n"
        "# WHAT THIS COSTS. hooks/publication-safety.sh is declared and absent.\n"
        '  local pre_bash\n'
        '  pre_bash=$(_cc_hook_group "PreToolUse" "Bash" \\\n'
        '    "hooks/destructive-rm-blocker.sh" "false" \\\n'
        "  )\n"
    )

    # Falsification probe: the naive test the census must not perform.
    assert "hooks/publication-safety.sh" in driver_text

    stripped = census.strip_comments(driver_text)
    assert "publication-safety" not in stripped
    assert "destructive-rm-blocker.sh" in stripped


def test_ledger_parsing_takes_the_basename_and_drops_comments(tmp_path: Path):
    ledger = tmp_path / "EXCLUDED_HOOKS.txt"
    ledger.write_text(
        "# header line naming hooks/never-registered.sh in prose\n"
        "\n"
        "aci-observation-capture.sh | CONDITIONAL: only under PROFILE=full\n"
        "_lib/common.sh | LIBRARY: sourced fragment\n"
    )

    names = census_names(ledger)
    assert "aci-observation-capture.sh" in names
    assert "common.sh" in names, "path prefixes must be reduced to the basename"
    # Falsification probe: a hook named only inside a comment must not count.
    assert "never-registered.sh" not in names


def census_names(path: Path) -> set[str]:
    return _load().ledger_names(path)


def test_child_audits_do_not_inherit_the_protected_write_permission(monkeypatch):
    census = _load()
    captured: dict[str, dict] = {}

    class _Proc:
        returncode = 0
        stdout = "{}"
        stderr = ""

    def fake_run(cmd, **kwargs):  # noqa: ANN001, ANN003
        captured["env"] = kwargs["env"]
        return _Proc()

    monkeypatch.setenv("COS_ALLOW_PROTECTED_CONFIG_WRITE", "1")
    monkeypatch.setattr(census.subprocess, "run", fake_run)

    # Falsification probe: the variable IS set in this process, so a census that
    # forwarded os.environ untouched would leak it.
    assert os.environ.get("COS_ALLOW_PROTECTED_CONFIG_WRITE") == "1"

    census.run_audit(Path("scripts/hook_projection_drift_audit.py"))
    assert "COS_ALLOW_PROTECTED_CONFIG_WRITE" not in captured["env"]
    # The rest of the environment still travels: PATH is what finds python.
    assert captured["env"].get("PATH") == os.environ.get("PATH")


def test_module_declares_its_scope_in_the_first_three_lines():
    head = CENSUS.read_text().splitlines()[:3]
    assert any(l.strip().startswith("# SCOPE:") for l in head), head


if __name__ == "__main__":  # pragma: no cover
    sys.exit(os.system(f"{sys.executable} -m pytest {__file__} -q"))
