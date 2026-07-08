# SCOPE: os-only
"""Portability proof for the OpenCode plugin cos-primitive-guard.js.

Both copies (.opencode/plugins/ and packages/opencode-adapter/plugins/) share
one contract: OpenCode's plugin loader iterates ``Object.values(module)`` and
throws ``Plugin export is not a function`` if ANY export is not a plugin
factory, discarding the whole plugin. So the module must export exactly one
value and it must be a function. A non-function export (e.g. an array) silently
disables all COS governance in OpenCode — the falsification probe below guards
against that regression across harnesses.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
PLUGIN_COPIES = [
    REPO_ROOT / ".opencode/plugins/cos-primitive-guard.js",
    REPO_ROOT / "packages/opencode-adapter/plugins/cos-primitive-guard.js",
]

_INTROSPECT = """
import * as mod from %s
const entries = Object.entries(mod).map(([k, v]) => [k, typeof v])
console.log(JSON.stringify(entries))
"""


def _module_exports(plugin_path: Path) -> list[list[str]]:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node runtime unavailable")
    script = _INTROSPECT % json.dumps(str(plugin_path))
    result = subprocess.run(
        [node, "--input-type=module", "-e", script],
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )
    # The last stdout line is the JSON payload (ignore any runtime noise above).
    lines = [ln for ln in result.stdout.splitlines() if ln.strip().startswith("[")]
    assert lines, f"no export payload from {plugin_path}: {result.stdout}{result.stderr}"
    return json.loads(lines[-1])


@pytest.mark.parametrize("plugin_path", PLUGIN_COPIES, ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_plugin_module_only_exports_functions(plugin_path: Path) -> None:
    """Falsification probe: every module export must be a function.

    Reproduces OpenCode's loader contract (gk(): throws TypeError on the first
    non-function export). A single non-function export disables the whole plugin.
    """
    assert plugin_path.is_file(), f"missing plugin copy: {plugin_path}"
    exports = _module_exports(plugin_path)
    assert exports, f"plugin exports nothing: {plugin_path}"
    non_functions = [name for name, kind in exports if kind != "function"]
    assert not non_functions, (
        f"{plugin_path.relative_to(REPO_ROOT)} has non-function export(s) "
        f"{non_functions}; OpenCode would reject the whole plugin with "
        f"'Plugin export is not a function'"
    )


def test_plugin_copies_are_identical() -> None:
    """The two harness copies must not drift — they share one contract."""
    bodies = {p.read_text(encoding="utf-8") for p in PLUGIN_COPIES if p.is_file()}
    assert len(bodies) == 1, "cos-primitive-guard.js copies have drifted apart"
