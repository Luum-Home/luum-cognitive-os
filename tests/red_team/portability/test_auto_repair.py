# SCOPE: os-only
"""Portability proof for cos_lib/auto_repair.py.

``auto_repair`` backs ``hooks/auto-repair-dispatcher.sh`` (SCOPE: both), a
consumer-facing PostToolUse hook. This proof pins that the module imports
and its primary entry point (``AutoRepairEngine.attempt_repair``) runs
correctly from an arbitrary working directory, using only a git repo and
``.cognitive-os/`` paths relative to the project dir — never anything that
assumes it is running inside the Cognitive OS source repo itself.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "cos_lib/auto_repair.py"


def _fake_python3_bin(tmp_path: Path) -> Path:
    """Build a PATH dir whose 'python3' wraps the current interpreter.

    The module's verification step shells out to a bare 'python3' on PATH
    to run pytest --co. A raw symlink confuses some interpreters' argv[0]
    based site-packages resolution, so use a tiny exec wrapper instead —
    this is test-harness plumbing, not something the module itself needs.
    """
    bin_dir = tmp_path / "fakebin"
    bin_dir.mkdir()
    wrapper = bin_dir / "python3"
    wrapper.write_text(f'#!/bin/sh\nexec "{sys.executable}" "$@"\n')
    wrapper.chmod(0o755)
    return bin_dir


def test_auto_repair_imports_from_arbitrary_project_root(tmp_path: Path, monkeypatch) -> None:
    """Falsification probe: library import must not depend on process cwd."""
    monkeypatch.chdir(tmp_path)
    sys.path.insert(0, str(REPO_ROOT))
    spec = importlib.util.spec_from_file_location("portability_auto_repair", ARTIFACT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)


def test_attempt_repair_works_in_arbitrary_consumer_project(tmp_path: Path) -> None:
    """Falsification probe: exercise the real entry point in a throwaway project.

    Initializes a bare git repo under ``tmp_path`` (standing in for a
    consumer project that merely installed the OS — not the Cognitive OS
    source repo), commits a non-executable script, and confirms
    ``attempt_repair`` matches the built-in "permission denied" remediation,
    applies ``chmod +x`` inside an isolated worktree under
    ``.cognitive-os/worktrees``, and returns a successful diff — all rooted
    at the consumer project's own tree.
    """
    project_dir = tmp_path / "consumer-project"
    project_dir.mkdir()

    subprocess.run(["git", "init", "-q"], cwd=project_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=project_dir, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=project_dir, check=True)

    script_path = project_dir / "deploy.sh"
    script_path.write_text("#!/bin/sh\necho hi\n")
    script_path.chmod(0o644)  # not executable
    subprocess.run(["git", "add", "deploy.sh"], cwd=project_dir, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=project_dir, check=True)

    script = (
        "import sys; sys.path.insert(0, %r)\n"
        "from cos_lib.auto_repair import AutoRepairEngine\n"
        "engine = AutoRepairEngine(project_root=%r)\n"
        "result = engine.attempt_repair('SCRIPT_ERROR', 'consumer-svc', "
        "'permission denied: cannot execute deploy.sh')\n"
        "print(result.success)\n"
        "print(result.fix_applied)\n"
    ) % (str(REPO_ROOT), str(project_dir))

    fake_bin = _fake_python3_bin(tmp_path)
    env = dict(os.environ)
    env["PATH"] = f"{fake_bin}{os.pathsep}{env.get('PATH', '')}"

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=project_dir,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    out_lines = result.stdout.strip().splitlines()
    assert out_lines[0] == "True", result.stdout + result.stderr
    assert "executable" in out_lines[1].lower()

    # The worktree was created and cleaned up under the consumer project's
    # own .cognitive-os tree — nothing leaked outside tmp_path.
    assert not (project_dir / ".cognitive-os" / "worktrees").exists() or not any(
        (project_dir / ".cognitive-os" / "worktrees").iterdir()
    )

    # Metrics were logged relative to the consumer project, not the OS repo.
    metrics_path = project_dir / ".cognitive-os" / "metrics" / "repair-outcomes.jsonl"
    assert metrics_path.is_file()


def test_is_safe_to_repair_blocks_protected_paths() -> None:
    """Falsification probe: pure function safety boundary has no filesystem
    or cwd dependency at all.
    """
    sys.path.insert(0, str(REPO_ROOT))
    spec = importlib.util.spec_from_file_location("portability_auto_repair_safety", ARTIFACT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    assert module.is_safe_to_repair("src/app.py") is True
    assert module.is_safe_to_repair("config/.env") is False
    assert module.is_safe_to_repair("services/auth/login.py") is False
