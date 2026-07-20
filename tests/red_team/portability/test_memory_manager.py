# SCOPE: os-only
"""Portability proof for cos_lib/memory_manager.py.

Pins that MemoryManager, MemoryProvider, and EngramMemoryProvider work from
an arbitrary working directory with no dependency on the OS repo tree — the
Engram provider only shells out to a binary resolved via PATH/ENGRAM_BIN, and
degrades to empty results when that binary is unavailable.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "cos_lib/memory_manager.py"


def test_memory_manager_imports_from_arbitrary_project_root(tmp_path: Path, monkeypatch) -> None:
    """Falsification probe: library import must not depend on process cwd."""
    monkeypatch.chdir(tmp_path)
    sys.path.insert(0, str(REPO_ROOT))
    spec = importlib.util.spec_from_file_location("portability_memory_manager", ARTIFACT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)


def test_memory_manager_prefetch_works_from_arbitrary_cwd_without_engram_binary(
    tmp_path: Path,
) -> None:
    """Falsification probe: exercise real behavior — register the built-in
    Engram provider and run prefetch_all() in a subprocess launched from an
    arbitrary cwd with a PATH that has no ``engram`` binary on it.

    Proves the manager degrades gracefully (empty context, no crash) rather
    than assuming an OS-repo-local engram install, and that registration /
    routing logic works outside the source repo.
    """
    consumer_cwd = tmp_path / "consumer_project"
    consumer_cwd.mkdir()

    script = (
        "import sys; sys.path.insert(0, %r)\n"
        "from cos_lib.memory_manager import MemoryManager, EngramMemoryProvider\n"
        "mm = MemoryManager()\n"
        "provider = EngramMemoryProvider(engram_bin='definitely-not-a-real-binary')\n"
        "mm.add_provider(provider)\n"
        "assert provider.is_available() is False\n"
        "ctx = mm.prefetch_all('anything')\n"
        "assert ctx == ''\n"
        "schemas = mm.get_all_tool_schemas()\n"
        "assert any(s['name'] == 'engram_query' for s in schemas)\n"
        "print('MANAGER_OK')\n"
    ) % (str(REPO_ROOT),)

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=consumer_cwd,
        env={"PATH": "/usr/bin:/bin"},
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "MANAGER_OK" in result.stdout
