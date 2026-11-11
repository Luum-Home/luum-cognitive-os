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


ALIASED = """\
evidence:
- primitive: scripts/first
  tests: &shared_tests
  - tests/unit/test_shared.py
  - tests/red_team/portability/test_shared_primitives.py
  rationale: Defines the anchor.
- primitive: templates/second.example.yaml
  tests: *shared_tests
  rationale: Reuses the anchor.
"""

# The shims delegate to PyYAML when it is importable, so the fallback parser is
# only reached in an interpreter without site-packages. `-I -S` gives one.
_PROBE = """
import importlib.util, json, sys
spec = importlib.util.spec_from_file_location("shim_under_test", sys.argv[1])
shim = importlib.util.module_from_spec(spec); spec.loader.exec_module(shim)
assert not shim._COS_YAML_DELEGATED, "PyYAML was importable: the fallback was not exercised"
try:
    print(json.dumps(shim.safe_load(sys.stdin.read())))
except shim.YAMLError as exc:
    print(json.dumps({"yaml_error": str(exc)}))
"""


def _fallback_load(shim: Path, text: str):
    import json
    import subprocess
    import sys

    proc = subprocess.run(
        [sys.executable, "-I", "-S", "-c", _PROBE, str(shim)],
        input=text, capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


import pytest  # noqa: E402


@pytest.mark.parametrize("shim", ["yaml.py", "scripts/yaml.py"])
def test_fallback_resolves_an_alias_to_the_anchored_list(shim: str) -> None:
    """`tests: *name` reads as the list declared with `tests: &name`, as PyYAML reads it."""
    import yaml as pyyaml

    data = _fallback_load(ROOT / shim, ALIASED)

    assert data == pyyaml.safe_load(ALIASED)
    assert data["evidence"][1]["tests"] == [
        "tests/unit/test_shared.py",
        "tests/red_team/portability/test_shared_primitives.py",
    ]
    assert data["evidence"][1]["rationale"] == "Reuses the anchor."


@pytest.mark.parametrize("shim", ["yaml.py", "scripts/yaml.py"])
def test_fallback_rejects_an_undefined_alias(shim: str) -> None:
    """An alias with no anchor is an error, not the literal string `*name`."""
    data = _fallback_load(ROOT / shim, "a:\n  tests: *missing\n")

    assert "yaml_error" in data and "missing" in data["yaml_error"]


@pytest.mark.parametrize("shim", ["yaml.py", "scripts/yaml.py"])
def test_fallback_reads_the_behavior_evidence_manifest_like_pyyaml(shim: str) -> None:
    """Each primitive's test list in the shipped manifest is the same with or without PyYAML."""
    import yaml as pyyaml

    text = (ROOT / "manifests" / "primitive-behavior-evidence.yaml").read_text(encoding="utf-8")
    expected = {row["primitive"]: row.get("tests") for row in pyyaml.safe_load(text)["evidence"]}
    got = {row["primitive"]: row.get("tests") for row in _fallback_load(ROOT / shim, text)["evidence"]}

    assert got == expected


@pytest.mark.parametrize("shim", ["yaml.py", "scripts/yaml.py"])
def test_fallback_keeps_a_hash_inside_a_plain_scalar(shim: str) -> None:
    """`#` opens a comment only after whitespace; `path#fragment` is one value."""
    data = _fallback_load(ROOT / shim, "primitive: lib/agent_bus.py#interrupt  # trailing comment\n")

    assert data == {"primitive": "lib/agent_bus.py#interrupt"}
