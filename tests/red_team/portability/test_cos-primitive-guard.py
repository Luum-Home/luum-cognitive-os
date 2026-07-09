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


# The real hook keys OpenCode's `interface Hooks` accepts (from
# @opencode-ai/plugin/dist/index.d.ts on v1.16.2). A handler keyed by anything
# outside this set is a phantom — OpenCode never invokes it.
REAL_OPENCODE_HOOKS = frozenset({
    "dispose", "event", "config", "tool", "auth", "provider",
    "chat.message", "chat.params", "chat.headers", "permission.ask",
    "command.execute.before", "shell.env", "tool.execute.before",
    "tool.execute.after", "tool.definition", "experimental.session.compacting",
    "experimental.chat.messages.transform", "experimental.chat.system.transform",
    "experimental.compaction.autocontinue", "experimental.text.complete",
})
# Keys the plugin used to register that OpenCode NEVER delivers (regression guard).
PHANTOM_KEYS = frozenset({
    "session.created", "session.idle", "session.compacted", "tui.prompt.append",
})

_HANDLER_KEYS = """
import { CosPrimitiveGuard } from %s
const handlers = await CosPrimitiveGuard({ directory: %s, worktree: %s })
console.log(JSON.stringify(Object.keys(handlers)))
"""


def _factory_handler_keys(plugin_path: Path, tmp: Path) -> list[str]:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node runtime unavailable")
    script = _HANDLER_KEYS % (json.dumps(str(plugin_path)), json.dumps(str(tmp)), json.dumps(str(tmp)))
    result = subprocess.run(
        [node, "--input-type=module", "-e", script],
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.strip().startswith("[")]
    assert lines, f"no handler payload from {plugin_path}: {result.stdout}{result.stderr}"
    return json.loads(lines[-1])


@pytest.mark.parametrize("plugin_path", PLUGIN_COPIES, ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_factory_registers_only_real_opencode_hooks(plugin_path: Path, tmp_path: Path) -> None:
    """Behavioral contract-drift probe: invoke the real factory and check its keys.

    Every handler the plugin returns must be a hook OpenCode's `interface Hooks`
    actually delivers; none may be a phantom key. A phantom handler silently
    disables that slice of COS governance in OpenCode (the exact defect this
    change fixes for session lifecycle).
    """
    keys = _factory_handler_keys(plugin_path, tmp_path)
    assert keys, f"factory returned no handlers: {plugin_path}"
    phantom = sorted(set(keys) & PHANTOM_KEYS)
    assert not phantom, f"{plugin_path.relative_to(REPO_ROOT)} still registers phantom hook(s): {phantom}"
    unknown = sorted(k for k in keys if k not in REAL_OPENCODE_HOOKS)
    assert not unknown, (
        f"{plugin_path.relative_to(REPO_ROOT)} registers handler(s) absent from "
        f"OpenCode interface Hooks: {unknown}"
    )
    # Lifecycle governance must be reachable via the generic `event` Hook.
    assert "event" in keys, "plugin no longer registers the `event` lifecycle Hook"
