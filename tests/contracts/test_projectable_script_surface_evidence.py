from __future__ import annotations

import py_compile
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

REPO = Path(__file__).resolve().parents[2]
PROJECTABLE_SCRIPT_SURFACES = [
    "scripts/cos-postgres-local.sh",
    "scripts/cos-valkey-local.sh",
    "scripts/document_feature_append.py",
    "scripts/install-aguara.sh",
    "scripts/install-garak.sh",
    "scripts/install-mcp-scan.sh",
    "scripts/install-promptfoo.sh",
    "scripts/install-tob-skills.sh",
    "scripts/sprint-test-summary.sh",
]


@pytest.mark.parametrize("relpath", PROJECTABLE_SCRIPT_SURFACES)
def test_projectable_script_surface_has_parseable_entrypoint(relpath: str) -> None:
    path = REPO / relpath
    assert path.is_file()
    if path.suffix == ".py":
        py_compile.compile(str(path), doraise=True)
    else:
        result = subprocess.run(["bash", "-n", str(path)], cwd=REPO, text=True, capture_output=True, check=False)
        assert result.returncode == 0, result.stderr
