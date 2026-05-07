from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.behavior
def test_package_mcp_server_imports_and_read_tools_return_json(project_root: Path) -> None:
    script = """
import importlib.util, json, pathlib, sys
path = pathlib.Path(sys.argv[1])
spec = importlib.util.spec_from_file_location('cos_mcp_pkg', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
for name, args in {
    'cos_status': (),
    'cos_get_tasks': (),
    'cos_get_rules': ('security credential',),
    'cos_check_quality': ('def ok():\\n    return 1\\n',),
}.items():
    payload = getattr(module, name)(*args)
    json.loads(payload)
print('ok')
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(project_root / "packages" / "mcp-server" / "cos_mcp.py")],
        cwd=project_root,
        text=True,
        capture_output=True,
        timeout=10,
        check=True,
    )
    assert result.stdout.strip() == "ok"
