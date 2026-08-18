# SCOPE: os-only
"""Paired portability proof for rules/encargo-refutable.md.

A rule is not an executable, so "runs from an arbitrary root" is the wrong probe
(the scaffold's default template would try to exec the Markdown). The portable
claim a rule makes is: its text carries no absolute path into this checkout, it
parses the same when read from a foreign project root, and the delivery
mechanism it declares actually references it.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "rules/encargo-refutable.md"
DELIVERY = REPO_ROOT / "templates/agent-mandatory-rules.md"


def _load_health():
    path = REPO_ROOT / "scripts" / "primitive_scope_health.py"
    spec = importlib.util.spec_from_file_location("scope_health_encargo_refutable", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_carries_no_absolute_source_path() -> None:
    """Falsification probe: a rule naming this checkout cannot travel."""
    health = _load_health()
    text = ARTIFACT.read_text(encoding="utf-8")
    assert not health.SOURCE_PATH_RE.search(text)


def test_parses_identically_from_arbitrary_project_root(tmp_path: Path) -> None:
    """The rule's frontmatter must survive relocation to a foreign project root."""
    import yaml

    relocated = tmp_path / "rules" / ARTIFACT.name
    relocated.parent.mkdir(parents=True)
    relocated.write_text(ARTIFACT.read_text(encoding="utf-8"), encoding="utf-8")

    body = relocated.read_text(encoding="utf-8")
    _, _, after = body.partition("---\n")
    front, sep, _ = after.partition("\n---")
    assert sep, "rule lost its frontmatter block after relocation"

    meta = yaml.safe_load(front)
    assert meta["rule"] == "encargo-refutable"
    assert meta["scope"] == "os-only"
    assert meta["status"] == "active"


def test_declared_delivery_path_actually_carries_the_rule() -> None:
    """The rule declares delivery via the mandatory-rules template; verify it."""
    delivered = DELIVERY.read_text(encoding="utf-8")
    assert "refutable" in delivered.lower(), "declared delivery template does not carry the rule"
