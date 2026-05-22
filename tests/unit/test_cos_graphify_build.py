"""Tests for the Graphify build wrapper."""
from __future__ import annotations

import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "cos-graphify-build"


def _load_module():
    loader = SourceFileLoader("cos_graphify_build", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def test_graphify_invocation_uses_operator_binary_when_available(monkeypatch) -> None:
    module = _load_module()

    def fake_which(name: str) -> str | None:
        return "/usr/local/bin/graphify" if name == "graphify" else None

    monkeypatch.setattr(module.shutil, "which", fake_which)

    assert module._graphify_invocation(None) == ["/usr/local/bin/graphify"]


def test_graphify_invocation_uses_uvx_from_package(monkeypatch) -> None:
    module = _load_module()

    def fake_which(name: str) -> str | None:
        return "/opt/homebrew/bin/uvx" if name == "uvx" else None

    monkeypatch.setattr(module.shutil, "which", fake_which)

    assert module._graphify_invocation(None) == ["/opt/homebrew/bin/uvx", "--from", "graphifyy", "graphify"]
