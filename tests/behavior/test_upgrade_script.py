"""Behavior tests for scripts/upgrade.sh.

Focused on harness-awareness and upgrade plumbing. These tests use a fake
source directory so they can verify how upgrade.sh re-invokes cos-init without
touching the real repository checkout.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parents[2]
UPGRADE_SCRIPT = PROJECT_ROOT / "scripts" / "upgrade.sh"


def _write_executable(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    path.chmod(0o755)


def _make_fake_source(tmp_path: Path) -> Path:
    source = tmp_path / "fake-source"
    (source / ".cognitive-os").mkdir(parents=True)
    (source / ".cognitive-os" / "version").write_text("2.0.0\n")

    _write_executable(
        source / "scripts" / "cos-init.sh",
        """#!/usr/bin/env bash
set -euo pipefail
target="${COGNITIVE_OS_PROJECT_DIR:?}/.cognitive-os"
mkdir -p "$target"
python3 - "$target/upgrade-invocation.json" "$COGNITIVE_OS_HARNESS" "$@" <<'PYEOF'
import json
import sys

payload = {
    "harness": sys.argv[2],
    "argv": sys.argv[3:],
}
with open(sys.argv[1], "w") as fh:
    json.dump(payload, fh)
PYEOF
""",
    )

    _write_executable(
        source / "scripts" / "component-lint.sh",
        "#!/usr/bin/env bash\nexit 0\n",
    )

    (source / "scripts" / "cos-registry.sh").write_text(
        "cos_registry_register() { :; }\n"
    )

    return source


def _make_project(tmp_path: Path, source_dir: Path) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    (project / ".cognitive-os").mkdir()
    (project / ".cognitive-os" / "install-meta.json").write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "mode": "default",
                "source": str(source_dir),
                "installed_at": "2026-01-01T00:00:00Z",
                "project_name": "upgrade-test",
            }
        )
    )
    return project


def _run_upgrade(project: Path, env_overrides: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        ["bash", str(UPGRADE_SCRIPT), "--force"],
        capture_output=True,
        text=True,
        cwd=str(project),
        env=env,
        timeout=30,
    )


def test_upgrade_passes_active_codex_harness_to_cos_init(tmp_path):
    """upgrade.sh should re-run cos-init with the detected Codex harness."""
    source_dir = _make_fake_source(tmp_path)
    project = _make_project(tmp_path, source_dir)
    codex_dir = project / ".codex"
    codex_dir.mkdir()
    (codex_dir / "hooks.json").write_text('{"hooks": {}}\n')

    result = _run_upgrade(project)

    assert result.returncode == 0, result.stderr
    assert "Harness:  codex" in result.stdout

    invocation = json.loads((project / ".cognitive-os" / "upgrade-invocation.json").read_text())
    assert invocation["harness"] == "codex"
    assert invocation["argv"] == ["--default", "--harness=codex"]


def test_upgrade_honors_explicit_harness_override(tmp_path):
    """COGNITIVE_OS_HARNESS should override project-file autodetection during upgrade."""
    source_dir = _make_fake_source(tmp_path)
    project = _make_project(tmp_path, source_dir)
    codex_dir = project / ".codex"
    codex_dir.mkdir()
    (codex_dir / "hooks.json").write_text('{"hooks": {}}\n')

    result = _run_upgrade(project, env_overrides={"COGNITIVE_OS_HARNESS": "claude"})

    assert result.returncode == 0, result.stderr
    assert "Harness:  claude" in result.stdout

    invocation = json.loads((project / ".cognitive-os" / "upgrade-invocation.json").read_text())
    assert invocation["harness"] == "claude"
    assert invocation["argv"] == ["--default", "--harness=claude"]
