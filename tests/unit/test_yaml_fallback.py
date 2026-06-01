from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_repo_yaml_module():
    spec = importlib.util.spec_from_file_location("cos_yaml_fallback_under_test", ROOT / "yaml.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_safe_load_supports_anchor_declared_list() -> None:
    yaml = load_repo_yaml_module()

    data = yaml.safe_load(
        """
primitives:
  - id: scripts/example.py
    supported_harnesses: &id001
      - shell
    runtime_projection: false
  - id: scripts/other.py
    supported_harnesses: *id001
"""
    )

    assert data["primitives"][0]["supported_harnesses"] == ["shell"]
    assert data["primitives"][0]["runtime_projection"] is False
