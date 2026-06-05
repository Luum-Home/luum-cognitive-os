# SCOPE: os-only
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HOOK = ROOT / "hooks" / "quality-duplicates.sh"
WRAPPER = ROOT / "scripts" / "cos-quality-duplicates"
ENGINE = ROOT / "scripts" / "cos_quality_duplicates.py"


def test_quality_duplicates_hook_runs_from_consumer_project(tmp_path: Path) -> None:
    project = tmp_path / "consumer"
    project.mkdir()
    (project / "README.md").write_text("consumer\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=project, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=project, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=project, check=True)
    subprocess.run(["git", "add", "README.md"], cwd=project, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=project, check=True, capture_output=True, text=True)

    bin_dir = project / ".cognitive-os" / "bin"
    bin_dir.mkdir(parents=True)
    (bin_dir / "cos-quality-duplicates").write_bytes(WRAPPER.read_bytes())
    (bin_dir / "cos-quality-duplicates").chmod(0o755)
    (bin_dir / "cos_quality_duplicates.py").write_bytes(ENGINE.read_bytes())
    hooks_dir = project / ".cognitive-os" / "hooks" / "cos"
    hooks_dir.mkdir(parents=True)
    hook = hooks_dir / "quality-duplicates.sh"
    hook.write_bytes(HOOK.read_bytes())
    hook.chmod(0o755)

    (project / "README.md").write_text("consumer changed\n", encoding="utf-8")
    result = subprocess.run([str(hook)], cwd=project, text=True, capture_output=True, check=False, timeout=20)

    assert result.returncode == 0, result.stderr + result.stdout
    assert (project / ".cognitive-os" / "reports" / "quality-duplicates" / "latest.json").exists()
